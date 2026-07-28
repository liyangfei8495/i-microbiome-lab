# -*- coding: utf-8 -*-
"""生成每条新闻的独立分享/阅读页 news/<id>.html。

特性：
- 与主站风格一致：支持日/夜主题切换（data-theme + CSS 变量）与中/英语言切换（lang-zh/lang-en + .zh/.en）
- 渲染完整双语正文（标题/日期/段落/图片），不仅预览卡片
- 顶部写入 Open Graph + Twitter Card 标签（微信/QQ 抓取直接出标题+封面卡片，用默认中文）
- 自动根治 base64 内嵌图：发现 news 图片块为 base64 时，解码上传到仓库
  images/news/<id>-<i>.jpg 并改写为绝对 URL（同时让 content.json 减重、OG 有图）
- 页面内「分享给朋友」(原生 Web Share) + 「返回实验室网站」

用法：
  GH_TOKEN=xxx python gen_news_share.py
"""
import os, re, json, base64, time, html, urllib.request, urllib.error
from datetime import datetime

SITE = "https://liang-lab.cn"
REPO = "liyangfei8495/i-microbiome-lab"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GH_PAT") or ""


def api(method, path, data=None):
    url = "https://api.github.com/repos/%s/contents/%s" % (REPO, path)
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data else None,
        method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_live_json():
    meta = api("GET", "content.json")
    raw = base64.b64decode(meta["content"]).decode("utf-8")
    return json.loads(raw), meta["sha"]


def put_content_json(data, sha):
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    body = {
        "message": "site: 生成器自动去除 news base64 内嵌图，改为 URL 引用",
        "content": base64.b64encode(raw.encode()).decode(),
        "sha": sha,
    }
    api("PUT", "content.json", body)
    # 同时写回本地，供后续渲染与离线兜底一致
    with open(os.path.join(HERE, "content.json"), "w", encoding="utf-8") as f:
        f.write(raw)
    return raw


def upload_image(b64src, path):
    hdr, enc = b64src.split(",", 1)
    ext = "jpg"
    mm = re.search(r"data:image/([a-zA-Z0-9.+-]+)", hdr)
    if mm:
        sub = mm.group(1)
        ext = "png" if sub == "png" else ("webp" if sub == "webp" else "jpg")
    img = base64.b64decode(enc)
    body = {
        "message": "site: 生成器上传 news 内嵌图(%s)" % path,
        "content": base64.b64encode(img).decode(),
    }
    try:
        api("PUT", path, body)
    except urllib.error.HTTPError:
        # 已存在则覆盖（取当前 sha）
        meta = api("GET", path)
        body["sha"] = meta["sha"]
        api("PUT", path, body)
    return "%s/%s" % (SITE, path)


def clean_base64(data):
    """把 news 图片块里的 base64 上传并改为 URL，返回清理数量。"""
    cleaned = 0
    for n in data.get("news", []) or []:
        nid = n.get("id", "news")
        for i, b in enumerate(n.get("blocks", []) or []):
            src = b.get("src")
            if isinstance(src, str) and src.startswith("data:image"):
                url = upload_image(src, "images/news/%s-%d.%s" % (nid, i, "jpg"))
                b["src"] = url
                cleaned += 1
    return cleaned


def esc_attr(s):
    return html.escape(s or "", quote=True)


def render_blocks(blocks):
    """渲染双语正文：text/heading 分 .zh/.en 两段，image 共用。"""
    out = []
    for b in blocks or []:
        t = b.get("type")
        if t == "image":
            src = b.get("src") or ""
            cap = b.get("caption") or ""
            fig = '<figure class="n-img"><img src="%s" alt="%s" loading="lazy">' % (
                esc_attr(src), esc_attr(cap))
            if cap:
                fig += '<figcaption><span class="zh">%s</span><span class="en">%s</span></figcaption>' % (
                    html.escape(cap), html.escape(cap))
            fig += "</figure>"
            out.append(fig)
        elif t == "heading":
            zh = b.get("zh") or b.get("text") or ""
            en = b.get("en") or b.get("text") or ""
            out.append('<h2><span class="zh">%s</span><span class="en">%s</span></h2>'
                       % (html.escape(zh), html.escape(en)))
        else:  # text / 默认
            zh = b.get("zh") or ""
            en = b.get("en") or ""
            if zh:
                for para in re.split(r"\n{2,}", zh.strip()):
                    para = para.strip().replace("\n", "<br>")
                    if para:
                        out.append('<p class="zh">%s</p>' % para)
            if en:
                for para in re.split(r"\n{2,}", en.strip()):
                    para = para.strip().replace("\n", "<br>")
                    if para:
                        out.append('<p class="en">%s</p>' % para)
    return "\n".join(out)


def first_image(n):
    for b in n.get("blocks", []) or []:
        if b.get("type") == "image" and isinstance(b.get("src"), str) \
                and b["src"].startswith("http"):
            return b["src"]
    return ""


def first_summary(n, limit=120):
    """OG 描述用中文摘要。"""
    for b in n.get("blocks", []) or []:
        if b.get("type") in (None, "text") and (b.get("zh") or b.get("en")):
            s = (b.get("zh") or b.get("en") or "").strip()
            s = re.sub(r"\s+", " ", s)
            return (s[:limit] + "…") if len(s) > limit else s
    return ""


TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLEZH__ | 智能微生态与生物制造实验室</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="智能微生态与生物制造实验室">
<meta property="og:title" content="__OGTITLE__">
<meta property="og:description" content="__OGDESC__">
<meta property="og:url" content="__OGURL__">
<meta property="og:image" content="__OGIMAGE__">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="__OGTITLE__">
<meta name="twitter:description" content="__OGDESC__">
<meta name="twitter:image" content="__OGIMAGE__">
<link rel="preload" as="style" href="../css/all.min.css" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="../css/all.min.css"></noscript>
<style>
  :root{--primary:#0066cc;--primary-hover:#0052a3;--bg:#fff;--section-bg:#f5f5f7;
        --border-color:#e5e5ea;--text-color:#1d1d1f;--light-text-color:#6e6e73;
        --hover-color:#f0f4f8;--accent:#0066cc;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       color:var(--text-color);background:var(--bg);line-height:1.7;
       -webkit-font-smoothing:antialiased;min-height:100vh;transition:background .3s,color .3s}
  [data-theme="dark"]{--primary:#4da3ff;--primary-hover:#79b8ff;--bg:#0d1117;--section-bg:#161b22;
        --border-color:#30363d;--text-color:#e6edf3;--light-text-color:#8b949e;--hover-color:#21262d;--accent:#4da3ff;}
  .lang-zh .en,.lang-en .zh{display:none !important}
  .topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;
          padding:10px 20px;border-bottom:1px solid var(--border-color);
          background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(16px);
          -webkit-backdrop-filter:blur(16px)}
  .back{color:var(--light-text-color);text-decoration:none;font-size:14px;display:inline-flex;align-items:center;gap:6px}
  .back:hover{color:var(--text-color)}
  .topbar-right{display:flex;align-items:center;gap:10px}
  .lang-toggle-btn{background:transparent;border:1px solid var(--border-color);border-radius:999px;
          padding:6px 14px;font-size:13px;cursor:pointer;color:var(--text-color);font-family:inherit;line-height:1}
  #theme-toggle{background:transparent;border:1px solid var(--border-color);border-radius:999px;
          padding:6px 12px;font-size:14px;cursor:pointer;color:var(--text-color);line-height:1}
  .wrap{max-width:760px;margin:0 auto;padding:32px 22px 72px}
  .kicker{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--primary);
          letter-spacing:.06em;border:1px solid color-mix(in srgb,var(--primary) 30%,transparent);
          padding:6px 14px;border-radius:999px;background:color-mix(in srgb,var(--primary) 8%,transparent)}
  h1{font-size:27px;line-height:1.4;margin:18px 0 8px;font-weight:700;letter-spacing:.01em}
  .date{color:var(--light-text-color);font-size:14px;margin-bottom:26px}
  .content{font-size:16px;color:var(--text-color)}
  .content p{margin:0 0 16px}
  .content h2{font-size:19px;margin:28px 0 12px;color:var(--text-color)}
  .content .n-img{margin:20px 0}
  .content .n-img img{width:100%;border-radius:14px;display:block;border:1px solid var(--border-color)}
  .content .n-img figcaption{font-size:13px;color:var(--light-text-color);text-align:center;margin-top:8px}
  .bar{display:flex;gap:12px;align-items:center;justify-content:center;margin-top:44px}
  .share{display:inline-flex;align-items:center;gap:8px;background:var(--primary);color:#fff;
         font-weight:600;border:none;border-radius:999px;padding:11px 22px;cursor:pointer;
         font-size:14px;transition:transform .2s,box-shadow .2s}
  .share:hover{transform:translateY(-2px);box-shadow:0 10px 26px color-mix(in srgb,var(--primary) 40%,transparent)}
  .foot{margin-top:40px;padding-top:22px;border-top:1px solid var(--border-color);
        text-align:center;color:var(--light-text-color);font-size:13px}
  .foot a{color:var(--primary);text-decoration:none}
  @media(max-width:600px){h1{font-size:22px}.wrap{padding:24px 16px 60px}}
</style>
</head>
<body class="lang-zh">
  <div class="topbar">
    <a class="back" href="__SITE__/">← <span class="zh">返回实验室网站</span><span class="en">Back to Lab</span></a>
    <div class="topbar-right">
      <button id="lang-toggle" class="lang-toggle-btn" type="button">EN</button>
      <button id="theme-toggle" class="lang-toggle-btn" type="button" title="切换主题" aria-label="切换明暗主题"><i class="fas fa-moon"></i></button>
    </div>
  </div>
  <div class="wrap">
    <span class="kicker"><span class="zh">团队动态</span><span class="en">News</span></span>
    <h1><span class="zh">__TITLEZH__</span><span class="en">__TITLEEN__</span></h1>
    <div class="date">__DATE__</div>
    <div class="content">
__BODY__
    </div>
    <div class="bar">
      <button class="share" id="shareBtn">🔗 <span class="zh">分享给朋友</span><span class="en">Share</span></button>
    </div>
    <div class="foot">
      <span class="zh">来自</span><span class="en">From</span> <a href="__SITE__/">智能微生态与生物制造实验室</a>
    </div>
  </div>
<script>
  var ZH_TITLE=__TITLEZH_ESC__, EN_TITLE=__TITLEEN_ESC__;
  /* ===== 语言切换 ===== */
  var LK="iMicrobiomeLang";
  function applyLang(l){
    document.body.classList.remove("lang-zh","lang-en");
    document.body.classList.add("lang-"+l);
    var btn=document.getElementById("lang-toggle");
    if(btn)btn.textContent=(l==="zh")?"EN":"中文";
    try{localStorage.setItem(LK,l);}catch(e){}
    document.documentElement.lang=(l==="zh")?"zh-CN":"en";
    document.title=(l==="zh"?ZH_TITLE:EN_TITLE)+" | 智能微生态与生物制造实验室";
  }
  var savedLang=null;
  try{savedLang=localStorage.getItem(LK);}catch(e){}
  applyLang(savedLang||((navigator.language||"").toLowerCase().indexOf("zh")===0?"zh":"en"));
  var lb=document.getElementById("lang-toggle");
  if(lb)lb.addEventListener("click",function(){applyLang(document.body.classList.contains("lang-zh")?"en":"zh");});
  /* ===== 明暗主题切换 ===== */
  var THEME_KEY="__THEME__";
  function applyTheme(t){
    document.documentElement.setAttribute("data-theme",t);
    var b=document.getElementById("theme-toggle");
    if(b)b.innerHTML=t==="dark"?'<i class="fas fa-sun"></i>':'<i class="fas fa-moon"></i>';
  }
  var savedTheme=null;
  try{savedTheme=localStorage.getItem(THEME_KEY);}catch(e){}
  var initialTheme=savedTheme||(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
  applyTheme(initialTheme);
  var tb=document.getElementById("theme-toggle");
  if(tb)tb.addEventListener("click",function(){
    var cur=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";
    applyTheme(cur);
    try{localStorage.setItem(THEME_KEY,cur);}catch(e){}
  });
  /* ===== 分享 ===== */
  function shareThis(){
    var u=location.href, t=document.title, d=document.querySelector('meta[name="twitter:description"]');
    var txt=d?d.getAttribute('content'):'';
    if(navigator.share){ navigator.share({title:t,text:txt,url:u}).catch(function(){}); }
    else{
      var ta=document.createElement('textarea');ta.value=u;document.body.appendChild(ta);
      ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);
      alert('链接已复制，去微信粘贴发给朋友：\\n'+u);
    }
  }
  var sb=document.getElementById('shareBtn');if(sb)sb.onclick=shareThis;
</script>
</body>
</html>"""


def build_date(n):
    """尽量生成 YYYY.MM.DD 完整日期。"""
    year = n.get("year") or ""
    month = n.get("month") or ""
    day = n.get("day") or ""
    raw = n.get("date") or ""

    # 如果 raw 已经是 YYYY.MM.DD，直接返回
    if raw and re.match(r"^\d{4}\.\d{2}\.\d{2}$", raw.strip()):
        return raw.strip()

    # 从 id 中的毫秒时间戳提取年份（例如 n-1785197807527）
    if not year:
        m = re.search(r"(\d{13})", n.get("id", ""))
        if m:
            try:
                year = datetime.fromtimestamp(int(m.group(1)) / 1000).strftime("%Y")
            except Exception:
                pass

    # 如果还没有年份，退而求其次用当前年
    if not year:
        year = datetime.now().strftime("%Y")

    parts = [p for p in [year, month, day] if p]
    if not parts:
        return raw
    # raw 形如 2026.07 且我们有 day，则补全为 2026.07.14
    if raw and len(parts) == 3 and not day and raw.count(".") == 1:
        return raw + "." + day
    return ".".join(parts)


def render_page(n):
    title_zh = n.get("titleZh") or ""
    title_en = n.get("titleEn") or ""
    date = build_date(n)
    ogt = esc_attr(title_zh or title_en)
    ogd = esc_attr(first_summary(n))
    url = "%s/news/%s.html" % (SITE, n.get("id"))
    ogimg = esc_attr(first_image(n))
    body = render_blocks(n.get("blocks"))
    return (TPL
            .replace("__TITLEZH__", html.escape(title_zh))
            .replace("__TITLEEN__", html.escape(title_en))
            .replace("__TITLEZH_ESC__", json.dumps(title_zh, ensure_ascii=False))
            .replace("__TITLEEN_ESC__", json.dumps(title_en, ensure_ascii=False))
            .replace("__OGTITLE__", ogt)
            .replace("__OGDESC__", ogd)
            .replace("__OGURL__", esc_attr(url))
            .replace("__OGIMAGE__", ogimg)
            .replace("__DATE__", html.escape(date or ""))
            .replace("__BODY__", body)
            .replace("__SITE__", SITE))


def main():
    assert TOKEN, "需要环境变量 GH_TOKEN（GitHub 个人访问令牌）"
    data, sha = get_live_json()
    cleaned = clean_base64(data)
    if cleaned:
        put_content_json(data, sha)
        print("已清理 %d 张 base64 内嵌图并改为 URL 引用" % cleaned)
    else:
        print("未检测到 base64 内嵌图，content.json 保持原样")
    os.makedirs(os.path.join(HERE, "news"), exist_ok=True)
    count = 0
    for n in data.get("news", []) or []:
        with open(os.path.join(HERE, "news", n["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(render_page(n))
        count += 1
    print("已生成 %d 个新闻分享页（news/<id>.html）" % count)


if __name__ == "__main__":
    main()
