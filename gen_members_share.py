# -*- coding: utf-8 -*-
"""生成每位团队成员的独立分享/主页 members/<id>.html。

严格对齐首页 openDetail(type==="member") 的历史渲染内容（仅“单开成独立页”，内容字段逐一对齐）：
  1. 个人简介  2. 自我介绍(intro+introImage)  3. 教育背景与工作经历
  4. 研究方向(researchZh, pre-line)  5. 主要学术成绩  6. 国内外会议与学术报告(conf)
  7. 代表性论文(repPubsZh, pre-line)  8. 招生与团队(recruit)  9. 寄语(words)  10. 联系方式(contact)
  11. 在研课题（按 research.projects[].memberIds 反向关联，原 modal 第10块）

- 与主站风格一致：日/夜主题切换 + 中/英语言切换（both() 输出 span.zh/span.en，随站点 lang 切换）
- 顶部写入 Open Graph + Twitter Card 标签（微信/QQ 抓取出带姓名+封面图的卡片）
- 页面内联脚本：地址栏无 ?v= 时自动补版本参数（绕过微信对已缓存结果的纯链接）
- 成员照片已是绝对 URL，无需 base64 清理；无照片回退站点默认 OG 图
- 主题/语言图标用 emoji，不依赖外部 Font Awesome，分享页可在任意环境稳定显示

用法：python gen_members_share.py（不依赖 GH_TOKEN，直接读本地 content.json）
"""
import os, re, json, html
from datetime import datetime

SITE = "https://liang-lab.cn"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OG = SITE + "/images/site/1784990973538-4875.jpg"


def esc_attr(s):
    return html.escape(s or "", quote=True)


def esc(s):
    return html.escape(s or "")


# 对齐首页 both()/zh()/en()：双语以 span.zh / span.en 包裹，随站点语言切换显隐
def zh(s):
    return '<span class="zh">%s</span>' % esc(s)


def en(s):
    return '<span class="en">%s</span>' % esc(s)


def both(zh_t, en_t):
    return zh(zh_t) + en(en_t)


def block(zh_title, en_title, zh_c, en_c, pre=False, image=None):
    """对齐首页 modal-block：标题 both()，正文 <p>both(zh,en)</p>；
    换行由全局 CSS .m-body p{white-space:pre-wrap} 统一保留（与首页 .modal-block p 一致）。
    pre 参数保留仅为兼容旧调用，换行已由 CSS 处理。内容缺失则整段不渲染。"""
    if not (zh_c or en_c):
        return ""
    out = '<section class="m-sec"><h2>%s</h2>' % both(zh_title, en_title)
    if image:
        out += '<img class="m-banner" src="%s" alt="">' % esc_attr(image)
    out += '<div class="m-body"><p>%s</p></div></section>' % both(zh_c, en_c)
    return out


def projects_block(m, data):
    """在研课题：research.projects 中 memberIds 含本成员的，原 modal 第10块。"""
    projs = [p for p in (data.get("research", {}).get("projects") or [])
             if m.get("id") and m["id"] in (p.get("memberIds") or [])]
    if not projs:
        return ""
    items = "".join('<li>%s</li>' % esc(p.get("titleZh") or p.get("titleEn") or p.get("id"))
                    for p in projs)
    return ('<section class="m-sec"><h2>%s</h2><div class="m-body"><ul class="proj-list">%s</ul></div></section>'
            % (both("在研课题", "Current Projects"), items))


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
  .avatar-fallback{display:flex;align-items:center;justify-content:center;font-size:44px;color:#fff;font-weight:700}
  .hinfo{min-width:0;flex:1}
  h1{font-size:27px;line-height:1.35;margin:0 0 8px;font-weight:700;letter-spacing:.01em}
  .role{color:var(--light-text-color);font-size:15px;line-height:1.6;margin-top:4px}
  .m-sec{margin:30px 0 0;border-top:1px solid var(--border-color);padding-top:22px}
  .m-sec h2{font-size:18px;margin-bottom:14px;color:var(--text-color);display:flex;align-items:center;gap:9px;font-weight:700}
  .m-sec h2::before{content:"";width:4px;height:18px;background:var(--primary);border-radius:2px;display:inline-block;flex-shrink:0}
  .m-body p{margin:0;font-size:15.5px;line-height:1.85;color:var(--text-color);white-space:pre-wrap}
  .m-banner{width:100%;max-height:320px;object-fit:cover;border-radius:14px;margin:4px 0 14px}
  .proj-list{margin:0;padding-left:20px}
  .proj-list li{font-size:15.5px;line-height:1.9;color:var(--text-color)}
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
__HERO__
    </div>
__CONTENT__
    <div class="bar">
      <button class="share" id="shareBtn">🔗 <span class="zh">分享给朋友</span><span class="en">Share</span></button>
    </div>
    <div class="foot">
      <div class="views" style="margin-bottom:10px"><i class="fas fa-eye"></i>&nbsp;<span class="zh">浏览量</span><span class="en">Views</span>&nbsp;<span id="busuanzi_container_page_pv"><span id="busuanzi_value_page_pv">0</span></span></div>
      <span class="zh">来自</span><span class="en">From</span> <a href="__SITE__/">智能微生态与生物制造实验室</a>
    </div>
  </div>
<script async src="https://busuanzi.9420.ltd/busuanzi.pure.mini.js"></script>
<script>
  var ZH_TITLE=__NAMEZH_ESC__, EN_TITLE=__NAMEEN_ESC__;
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
    photo = m.get("photo") or ""
    if photo and not photo.startswith("http"):
        photo = SITE.rstrip("/") + "/" + photo.lstrip("/")
    if photo:
        hero = ('<img class="avatar" src="%s" alt="%s">' % (esc_attr(photo), esc_attr(name_zh)))
    else:
        photo = DEFAULT_OG
        hero = ('<div class="avatar avatar-fallback" style="background-color:hsl(%d,52%%,50%%)">%s</div>'
                % (sum(ord(c) for c in (name_zh or name_en or "?")) % 360, esc((name_zh or name_en or "?")[0])))
    hero += '<div class="hinfo">'
    # 严格对齐首页 openDetail member：姓名 = esc(nameZh) + ' ' + en(nameEn)，下接 role（无额外徽章）
    hero += '<h1>%s %s</h1>' % (esc(name_zh), en(name_en))
    hero += '<div class="role">%s</div>' % both(role_zh, role_en)
    hero += '</div>'

    # 严格按 openDetail(type==="member") 顺序渲染 11 段
    content = ""
    content += block("个人简介", "Bio", m.get("bioZh"), m.get("bioEn"))
    content += block("自我介绍", "About", m.get("introZh"), m.get("introEn"), image=m.get("introImage"))
    content += block("教育背景与工作经历", "Education & Experience", m.get("eduZh"), m.get("eduEn"))
    content += block("研究方向", "Research Directions", m.get("researchZh"), m.get("researchEn"), pre=True)
    content += block("主要学术成绩", "Academic Achievements", m.get("achZh"), m.get("achEn"))
    content += block("国内外会议与学术报告", "Conferences & Talks", m.get("confZh"), m.get("confEn"))
    content += block("代表性论文", "Representative Publications", m.get("repPubsZh"), m.get("repPubsEn"), pre=True)
    content += block("招生与团队", "Recruitment & Team", m.get("recruitZh"), m.get("recruitEn"))
    content += block("寄语", "Message", m.get("wordsZh"), m.get("wordsEn"))
    content += block("联系方式", "Contact", m.get("contactZh"), m.get("contactEn"))
    content += projects_block(m, data)

    ogt = esc_attr(name_zh or name_en)
    ogd = esc_attr(first_summary(m))
    url = "%s/members/%s.html" % (SITE, m.get("id"))
    build_ver = datetime.now().strftime("%Y%m%d%H%M%S")
    return (MEM_TPL
            .replace("__NAMEZH__", esc(name_zh))
            .replace("__NAMEEN__", esc(name_en))
            .replace("__NAMEZH_ESC__", json.dumps(name_zh, ensure_ascii=False))
            .replace("__NAMEEN_ESC__", json.dumps(name_en, ensure_ascii=False))
            .replace("__OGTITLE__", ogt)
            .replace("__OGDESC__", ogd)
            .replace("__OGURL__", esc_attr(url))
            .replace("__OGIMAGE__", esc_attr(photo))
            .replace("__BUILDVER__", build_ver)
            .replace("__HERO__", hero)
            .replace("__CONTENT__", content)
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
