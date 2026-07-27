# -*- coding: utf-8 -*-
"""生成每条新闻的独立分享/阅读页 news/<id>.html。

特性：
- 渲染完整正文（标题/日期/段落/图片），不仅预览卡片
- 顶部写入 Open Graph + Twitter Card 标签（微信/QQ 抓取直接出标题+封面卡片）
- 自动根治 base64 内嵌图：发现 news 图片块为 base64 时，解码上传到仓库
  images/news/<id>-<i>.jpg 并改写为绝对 URL（同时让 content.json 减重、OG 有图）
- 页面内「分享给朋友」(原生 Web Share) + 「返回实验室网站」

用法：
  GH_TOKEN=xxx python gen_news_share.py
"""
import os, re, json, base64, time, html, urllib.request, urllib.error

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
    out = []
    for b in blocks or []:
        t = b.get("type")
        if t == "image":
            src = b.get("src") or ""
            cap = b.get("caption") or ""
            if src.startswith("data:image"):
                out.append('<figure class="n-img"><img src="%s" alt="%s" loading="lazy"></figure>'
                           % (esc_attr(src), esc_attr(cap)))
            else:
                fig = '<figure class="n-img"><img src="%s" alt="%s" loading="lazy">' % (
                    esc_attr(src), esc_attr(cap))
                if cap:
                    fig += '<figcaption>%s</figcaption>' % html.escape(cap)
                fig += "</figure>"
                out.append(fig)
        elif t == "heading":
            out.append("<h2>%s</h2>" % html.escape(b.get("text") or b.get("zh") or ""))
        else:  # text / 默认
            txt = b.get("text") or b.get("zh") or ""
            for para in re.split(r"\n{2,}", txt):
                para = para.strip()
                if not para:
                    continue
                para = para.replace("\n", "<br>")
                out.append("<p>%s</p>" % para)
    return "\n".join(out)


def first_image(n):
    for b in n.get("blocks", []) or []:
        if b.get("type") == "image" and isinstance(b.get("src"), str) \
                and b["src"].startswith("http"):
            return b["src"]
    return ""


def first_summary(n, limit=120):
    for b in n.get("blocks", []) or []:
        if b.get("type") in (None, "text") and (b.get("text") or b.get("zh")):
            s = re.sub(r"\s+", " ", (b.get("text") or b.get("zh")).strip())
            return (s[:limit] + "…") if len(s) > limit else s
    return ""


TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ | 智能微生态与生物制造实验室</title>
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
<style>
  :root{--bg:#0f1419;--card:#161d26;--text:#e8edf2;--muted:#9aa7b4;--accent:#5ad1a8;--accent2:#3a8ed0;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:radial-gradient(1200px 600px at 50% -10%,#1b2734,#0f1419 60%);color:var(--text);
       line-height:1.7;-webkit-font-smoothing:antialiased;min-height:100vh}
  .wrap{max-width:720px;margin:0 auto;padding:32px 20px 64px}
  .kicker{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--accent);
          letter-spacing:.08em;text-transform:uppercase;border:1px solid rgba(90,209,168,.3);
          padding:6px 14px;border-radius:999px;background:rgba(90,209,168,.08)}
  h1{font-size:26px;line-height:1.4;margin:18px 0 10px;font-weight:700;letter-spacing:.01em}
  .date{color:var(--muted);font-size:14px;margin-bottom:22px}
  .hero{width:100%;border-radius:16px;overflow:hidden;margin:8px 0 26px;
        box-shadow:0 18px 50px rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.06)}
  .hero img{width:100%;display:block}
  .content{font-size:16px;color:#dde4ea}
  .content p{margin:0 0 16px}
  .content h2{font-size:19px;margin:26px 0 12px;color:#fff}
  .content .n-img{margin:18px 0}
  .content .n-img img{width:100%;border-radius:12px;display:block}
  .content .n-img figcaption{font-size:13px;color:var(--muted);text-align:center;margin-top:8px}
  .bar{position:sticky;top:0;z-index:5;display:flex;gap:12px;align-items:center;
       justify-content:space-between;padding:12px 0;margin-bottom:8px;
       background:linear-gradient(180deg,rgba(15,20,25,.95),rgba(15,20,25,.6));backdrop-filter:blur(10px)}
  .back{color:var(--muted);text-decoration:none;font-size:14px;display:inline-flex;align-items:center;gap:6px}
  .back:hover{color:var(--text)}
  .share{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,var(--accent),var(--accent2));
         color:#06121a;font-weight:600;border:none;border-radius:999px;padding:10px 18px;cursor:pointer;
         font-size:14px;box-shadow:0 8px 22px rgba(90,209,168,.35);transition:transform .2s,box-shadow .2s}
  .share:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(90,209,168,.5)}
  .foot{margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,.08);
        text-align:center;color:var(--muted);font-size:13px}
  .foot a{color:var(--accent);text-decoration:none}
</style>
</head>
<body>
  <div class="wrap">
    <div class="bar">
      <a class="back" href="__SITE__/">← 返回实验室网站</a>
      <button class="share" id="shareBtn">🔗 分享给朋友</button>
    </div>
    <span class="kicker">团队动态 · News</span>
    <h1>__TITLE__</h1>
    <div class="date">__DATE__</div>
    __HERO__
    <div class="content">
__BODY__
    </div>
    <div class="foot">
      来自 <a href="__SITE__/">智能微生态与生物制造实验室</a> · 蚯蚓粪源微生物与微生物模块化组装研究
    </div>
  </div>
<script>
  function shareThis(){
    var u=location.href, t=document.title, d=document.querySelector('meta[name="twitter:description"]');
    var txt=d?d.getAttribute('content'):'';
    if(navigator.share){
      navigator.share({title:t,text:txt,url:u}).catch(function(){});
    }else{
      var ta=document.createElement('textarea');ta.value=u;document.body.appendChild(ta);
      ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);
      alert('链接已复制，去微信粘贴发给朋友：\\n'+u);
    }
  }
  var sb=document.getElementById('shareBtn');if(sb)sb.onclick=shareThis;
</script>
</body>
</html>"""


def render_page(n):
    title = n.get("titleZh") or n.get("titleEn") or "团队动态"
    date = n.get("date") or ((n.get("year") or "") + "." + (n.get("month") or ""))
    ogt = esc_attr(title)
    ogd = esc_attr(first_summary(n))
    url = "%s/news/%s.html" % (SITE, n.get("id"))
    ogimg = esc_attr(first_image(n))
    hero = ""
    if ogimg:
        hero = '<div class="hero"><img src="%s" alt="%s" loading="lazy"></div>' % (ogimg, ogt)
    body = render_blocks(n.get("blocks"))
    return (TPL
            .replace("__TITLE__", html.escape(title))
            .replace("__OGTITLE__", ogt)
            .replace("__OGDESC__", ogd)
            .replace("__OGURL__", esc_attr(url))
            .replace("__OGIMAGE__", ogimg)
            .replace("__DATE__", html.escape(date or ""))
            .replace("__HERO__", hero)
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
