# -*- coding: utf-8 -*-
"""生成每位团队成员的独立分享/主页 members/<id>.html。

对齐 gen_news_share.py 的成熟机制：
- 与主站风格一致：日/夜主题切换（data-theme + CSS 变量）与中/英语言切换
- 渲染完整双语简历（姓名/头衔/简介/教育/成就/学术报告/招生/导师寄语/联系方式）
  + 关联研究方向 / 项目 / 平台（按 id 引用解析）
- 顶部写入 Open Graph + Twitter Card 标签（微信/QQ 抓取出带姓名+封面图的卡片）
- 页面内联脚本：地址栏无 ?v= 时自动补版本参数（绕过微信对已缓存结果的纯链接）
- 成员照片已是绝对 URL（https://liang-lab.cn/images/members/...），无需 base64 清理
- 无照片的成员（photo 为空）回退到站点默认 OG 图
- 主题/语言图标用 emoji，不依赖外部 Font Awesome，分享页可在任意环境稳定显示

用法：
  python gen_members_share.py
（不依赖 GH_TOKEN：直接读本地 content.json，成员照片为 URL 引用，无 API 写入需求）
"""
import os, re, json, html
from datetime import datetime

SITE = "https://liang-lab.cn"
HERE = os.path.dirname(os.path.abspath(__file__))
# 站点默认 OG 图（来自首页 og:image），成员无照片时回退
DEFAULT_OG = SITE + "/images/site/1784990973538-4875.jpg"

GROUP_LABELS = {
    "pi": "PI · 实验室负责人",
    "faculty": "课题组老师",
    "manager": "团队管理",
    "phd": "博士研究生",
    "master": "硕士研究生",
    "postdoc": "博士后",
    "alumni": "毕业生",
}


def slug(x):
    """归一化引用 id：去掉 prj/proj/project/pillar/fac 等前缀，只保留核心 slug，
    以兼容成员引用与数据定义前缀不一致（如 proj-gut vs prj-gut）。"""
    if not x:
        return x
    return re.sub(r"^(prj|proj|project|pillar|fac)-", "", x)


def esc_attr(s):
    return html.escape(s or "", quote=True)


def esc(s):
    return html.escape(s or "")


_URL_RE = re.compile(r"(https?://[^\s<]+)")


def linkify(escaped):
    """对已完成 html.escape 的文本，把裸 http(s) 链接包成 <a>。"""
    return _URL_RE.sub(r'<a href="\1" target="_blank" rel="noopener">\1</a>', escaped)


def render_paras(zh, en):
    """多行文本 → .zh / .en 两段 <p>；空段跳过；裸 URL 自动链接化。"""
    out = []
    if zh:
        for para in re.split(r"\n{2,}", zh.strip()):
            para = para.strip().replace("\n", "<br>")
            if para:
                out.append('<p class="zh">%s</p>' % linkify(para))
    if en:
        for para in re.split(r"\n{2,}", en.strip()):
            para = para.strip().replace("\n", "<br>")
            if para:
                out.append('<p class="en">%s</p>' % linkify(para))
    return "\n".join(out)


def render_section(zh_title, en_title, zh, en):
    if not (zh or en):
        return ""
    return (
        '<section class="m-sec">'
        '<h2><span class="zh">%s</span><span class="en">%s</span></h2>'
        '<div class="m-body">%s</div></section>'
        % (esc(zh_title), esc(en_title), render_paras(zh, en))
    )


def resolve_chips(ids, lookup):
    """ids: 列表; lookup: {slug: {zh,en}}; 返回 chip HTML。id 经 slug 归一化后再查。"""
    if not ids:
        return ""
    chips = []
    for i in ids:
        item = lookup.get(slug(i))
        if not item:
            continue
        zh = item.get("zh") or item.get("titleZh") or ""
        en = item.get("en") or item.get("titleEn") or ""
        chips.append('<span class="chip"><span class="zh">%s</span><span class="en">%s</span></span>'
                     % (esc(zh), esc(en)))
    # 去重保序
    seen = set()
    uniq = []
    for c in chips:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return "\n".join(uniq)


MEM_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAMEZH__ | 智能微生态与生物制造实验室</title>
<meta property="og:type" content="profile">
<meta property="og:site_name" content="智能微生态与生物制造实验室">
<meta property="og:title" content="__OGTITLE__">
<meta property="og:description" content="__OGDESC__">
<meta property="og:url" content="__OGURL__?v=__BUILDVER__">
<meta property="og:image" content="__OGIMAGE__">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="__OGTITLE__">
<meta name="twitter:description" content="__OGDESC__">
<meta name="twitter:image" content="__OGIMAGE__">
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
          padding:6px 12px;font-size:16px;cursor:pointer;color:var(--text-color);line-height:1}
  .wrap{max-width:760px;margin:0 auto;padding:32px 22px 72px}
  .hero{display:flex;gap:22px;align-items:center;margin:10px 0 26px;flex-wrap:wrap}
  .avatar{width:118px;height:118px;border-radius:50%;object-fit:cover;
          border:3px solid var(--border-color);flex-shrink:0;background:var(--section-bg)}
  .hinfo{min-width:0;flex:1}
  .group-badge{display:inline-block;font-size:12px;color:var(--primary);
          border:1px solid color-mix(in srgb,var(--primary) 30%,transparent);
          padding:4px 12px;border-radius:999px;background:color-mix(in srgb,var(--primary) 8%,transparent);margin-bottom:10px}
  h1{font-size:27px;line-height:1.35;margin:0 0 8px;font-weight:700;letter-spacing:.01em}
  .role{color:var(--light-text-color);font-size:15px;line-height:1.6;margin-top:4px}
  .m-bio{font-size:16.5px;line-height:1.85;margin:6px 0 8px;color:var(--text-color)}
  .m-bio p{margin:0 0 14px}
  .m-sec{margin:30px 0 0;border-top:1px solid var(--border-color);padding-top:22px}
  .m-sec h2{font-size:18px;margin-bottom:14px;color:var(--text-color);display:flex;align-items:center;gap:9px;font-weight:700}
  .m-sec h2::before{content:"";width:4px;height:18px;background:var(--primary);border-radius:2px;display:inline-block;flex-shrink:0}
  .m-body p{margin:0 0 12px;font-size:15.5px;line-height:1.8;color:var(--text-color)}
  .m-body a{color:var(--primary);text-decoration:none;word-break:break-all}
  .m-body a:hover{text-decoration:underline}
  .m-related{margin:26px 0 0;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
  .m-rel-label{font-size:13px;color:var(--light-text-color);margin-right:2px}
  .chip{font-size:13px;border:1px solid var(--border-color);border-radius:999px;padding:6px 14px;
        background:var(--section-bg);color:var(--text-color)}
  .bar{display:flex;gap:12px;align-items:center;justify-content:center;margin-top:44px}
  .share{display:inline-flex;align-items:center;gap:8px;background:var(--primary);color:#fff;
         font-weight:600;border:none;border-radius:999px;padding:11px 22px;cursor:pointer;
         font-size:14px;transition:transform .2s,box-shadow .2s}
  .share:hover{transform:translateY(-2px);box-shadow:0 10px 26px color-mix(in srgb,var(--primary) 40%,transparent)}
  .foot{margin-top:40px;padding-top:22px;border-top:1px solid var(--border-color);
        text-align:center;color:var(--light-text-color);font-size:13px}
  .foot a{color:var(--primary);text-decoration:none}
  @media(max-width:600px){h1{font-size:22px}.avatar{width:92px;height:92px}.wrap{padding:24px 16px 60px}}
</style>
</head>
<body class="lang-zh">
  <div class="topbar">
    <a class="back" href="__SITE__/">← <span class="zh">返回实验室网站</span><span class="en">Back to Lab</span></a>
    <div class="topbar-right">
      <button id="lang-toggle" class="lang-toggle-btn" type="button">EN</button>
      <button id="theme-toggle" class="lang-toggle-btn" type="button" title="切换主题" aria-label="切换明暗主题">🌙</button>
    </div>
  </div>
  <div class="wrap">
    <div class="hero">
      <img class="avatar" src="__PHOTO__" alt="__NAMEZH__">
      <div class="hinfo">
        <span class="group-badge">__GROUPBADGE__</span>
        <h1><span class="zh">__NAMEZH__</span><span class="en">__NAMEEN__</span></h1>
        <div class="role"><span class="zh">__ROLEZH__</span><span class="en">__ROLEEN__</span></div>
      </div>
    </div>
    <div class="m-bio">
__BIO__
    </div>
__RELATED__
__EDU__
__ACH__
__CONF__
__RECRUIT__
__WORDS__
__CONTACT__
    <div class="bar">
      <button class="share" id="shareBtn">🔗 <span class="zh">分享给朋友</span><span class="en">Share</span></button>
    </div>
    <div class="foot">
      <span class="zh">来自</span><span class="en">From</span> <a href="__SITE__/">智能微生态与生物制造实验室</a>
    </div>
  </div>
<script>
  var ZH_TITLE=__NAMEZH_ESC__, EN_TITLE=__NAMEEN_ESC__;
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
  /* 自动给地址栏加版本参数：微信右上角分享时会按“新链接”重新抓取 OG 卡片，绕过微信对已缓存 404/旧版本的纯链接结果 */
  (function(){var v="__BUILDVER__";if(location.search.indexOf("v="+v)<0){var s=(location.search?location.search+"&":"?")+"v="+v;history.replaceState(null,"",location.pathname+s+location.hash);}})();
  var savedLang=null;
  try{savedLang=localStorage.getItem(LK);}catch(e){}
  applyLang(savedLang||((navigator.language||"").toLowerCase().indexOf("zh")===0?"zh":"en"));
  var lb=document.getElementById("lang-toggle");
  if(lb)lb.addEventListener("click",function(){applyLang(document.body.classList.contains("lang-zh")?"en":"zh");});
  /* ===== 明暗主题切换 ===== */
  var THEME_KEY="iMicrobiomeTheme";
  function applyTheme(t){
    document.documentElement.setAttribute("data-theme",t);
    var b=document.getElementById("theme-toggle");
    if(b)b.textContent=t==="dark"?"☀️":"🌙";
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
    var u=location.origin+location.pathname+location.search, t=document.title, d=document.querySelector('meta[name="twitter:description"]');
    var txt=d?d.getAttribute('content'):'';
    var isWx=/MicroMessenger/i.test(navigator.userAgent);
    if(navigator.share && !isWx){ navigator.share({title:t,text:txt,url:u}).catch(function(){}); }
    else{
      var ta=document.createElement('textarea');ta.value=u;document.body.appendChild(ta);
      ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);
      if(isWx){ alert('链接已复制，请点击右上角「···」粘贴发送给朋友，将自动显示标题与封面图'); }
      else{ alert('链接已复制，去微信粘贴发给朋友：\\n'+u); }
    }
  }
  var sb=document.getElementById('shareBtn');if(sb)sb.onclick=shareThis;
</script>
</body>
</html>"""


def first_summary(m, limit=120):
    s = (m.get("bioZh") or m.get("roleZh") or "").strip()
    s = re.sub(r"\s+", " ", s)
    return (s[:limit] + "…") if len(s) > limit else s


def render_page(m, data):
    name_zh = m.get("nameZh") or ""
    name_en = m.get("nameEn") or ""
    role_zh = m.get("roleZh") or ""
    role_en = m.get("roleEn") or ""
    group = m.get("group") or ""
    badge = GROUP_LABELS.get(group, group or "团队成员")
    photo = m.get("photo") or ""
    if not photo.startswith("http"):
        photo = DEFAULT_OG
    ogt = esc_attr(name_zh or name_en)
    ogd = esc_attr(first_summary(m))
    url = "%s/members/%s.html" % (SITE, m.get("id"))
    ogimg = esc_attr(photo)
    bio = render_paras(m.get("bioZh"), m.get("bioEn"))
    edu = render_section("教育经历", "Education", m.get("eduZh"), m.get("eduEn"))
    ach = render_section("主要成就", "Selected Achievements", m.get("achZh"), m.get("achEn"))
    conf = render_section("学术报告 / 会议", "Talks & Conferences",
                          m.get("confZh"), m.get("confEn"))
    recruit = render_section("招生信息", "Recruitment",
                             m.get("recruitZh"), m.get("recruitEn"))
    words = render_section("导师寄语", "Words", m.get("wordsZh"), m.get("wordsEn"))
    contact = render_section("联系方式", "Contact", m.get("contactZh"), m.get("contactEn"))
    # 关联研究方向 / 项目 / 平台（id 引用，经 slug 归一化后解析，兼容前缀不一致）
    pillars = {slug(p.get("id")): p for p in (data.get("research", {}).get("pillars") or [])}
    projects = {slug(p.get("id")): p for p in (data.get("projects") or [])}
    facilities = {slug(f.get("id")): f for f in (data.get("facilities") or [])}
    chips = resolve_chips(m.get("pillarIds"), pillars)
    chips += ("\n" + resolve_chips(m.get("projectIds"), projects)) if m.get("projectIds") else ""
    chips += ("\n" + resolve_chips(m.get("facilityIds"), facilities)) if m.get("facilityIds") else ""
    chips = chips.strip()
    related = ""
    if chips:
        related = ('<div class="m-related"><span class="m-rel-label"><span class="zh">研究方向 / 项目 / 平台</span>'
                   '<span class="en">Research / Projects / Facilities</span></span>%s</div>') % chips
    build_ver = datetime.now().strftime("%Y%m%d%H%M%S")
    return (MEM_TPL
            .replace("__NAMEZH__", esc(name_zh))
            .replace("__NAMEEN__", esc(name_en))
            .replace("__NAMEZH_ESC__", json.dumps(name_zh, ensure_ascii=False))
            .replace("__NAMEEN_ESC__", json.dumps(name_en, ensure_ascii=False))
            .replace("__ROLEZH__", esc(role_zh))
            .replace("__ROLEEN__", esc(role_en))
            .replace("__GROUPBADGE__", esc(badge))
            .replace("__PHOTO__", esc_attr(photo))
            .replace("__OGTITLE__", ogt)
            .replace("__OGDESC__", ogd)
            .replace("__OGURL__", esc_attr(url))
            .replace("__OGIMAGE__", ogimg)
            .replace("__BUILDVER__", build_ver)
            .replace("__BIO__", bio)
            .replace("__RELATED__", related)
            .replace("__EDU__", edu)
            .replace("__ACH__", ach)
            .replace("__CONF__", conf)
            .replace("__RECRUIT__", recruit)
            .replace("__WORDS__", words)
            .replace("__CONTACT__", contact)
            .replace("__SITE__", SITE))


def main():
    with open(os.path.join(HERE, "content.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.join(HERE, "members"), exist_ok=True)
    count = 0
    for m in data.get("members", []) or []:
        if not m.get("id"):
            continue
        with open(os.path.join(HERE, "members", m["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(render_page(m, data))
        count += 1
    print("已生成 %d 个成员分享页（members/<id>.html）" % count)


if __name__ == "__main__":
    main()
