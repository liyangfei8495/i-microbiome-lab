#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为每条团队动态生成独立的静态分享页（带 Open Graph / Twitter Card 标签）。

GitHub Pages 是纯静态托管，服务器不会按 ?news= 动态注入 <meta>；
而微信/QQ 等抓取机器人不执行 JS，只读取原始 HTML 里的 OG 标签。
因此必须给每条新闻生成独立静态页 news/<id>.html，粘贴链接才能显示标题+封面图。

用法（在 deploy-ghpages/ 目录下执行）：
    python gen_news_share.py
生成结果：deploy-ghpages/news/<id>.html  （随仓库一起 commit + push 即上线）
"""
import json, os, re, html, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://liang-lab.cn"
OUT_DIR = os.path.join(HERE, "news")

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="i-Microbiome Lab">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{img}">
<meta property="og:url" content="{url}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{img}">
<style>
  :root{{ --bg:#0e1116; --card:#171b22; --fg:#eef2f7; --muted:#9aa4b2; --accent:#5ad1a8; }}
  *{{box-sizing:border-box;}}
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:radial-gradient(1200px 600px at 50% -10%,#1b2330,#0e1116);
       font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Segoe UI,Roboto,sans-serif;
       color:var(--fg);padding:24px;}}
  .card{{width:100%;max-width:520px;background:var(--card);border:1px solid rgba(255,255,255,.08);
        border-radius:20px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.45);}}
  .card .cover{{width:100%;height:0;padding-bottom:56.25%;background:linear-gradient(135deg,#1d6b54,#0e3b30);
        position:relative;}}
  .card .cover img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;}}
  .body{{padding:22px 24px 26px;}}
  .tag{{display:inline-block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;
       color:var(--accent);margin-bottom:10px;}}
  h1{{font-size:21px;line-height:1.4;margin:0 0 10px;font-weight:700;}}
  .date{{font-size:13px;color:var(--muted);margin:0 0 12px;}}
  .desc{{font-size:14px;line-height:1.7;color:#c7cfdb;margin:0 0 20px;}}
  .btn{{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:#06231b;
       font-weight:700;text-decoration:none;padding:12px 20px;border-radius:12px;font-size:15px;
       transition:transform .2s ease, box-shadow .2s ease;}}
  .btn:hover{{transform:translateY(-2px);box-shadow:0 12px 30px rgba(90,209,168,.35);}}
  .btn-ghost{{background:transparent;color:var(--fg);border:1px solid rgba(255,255,255,.22);box-shadow:none;}}
  .btn-ghost:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(255,255,255,.08);}}
  .hint{{margin-top:14px;font-size:12px;color:var(--muted);}}
</style>
</head>
<body>
  <div class="card">
    <div class="cover">{cover_img}</div>
    <div class="body">
      <span class="tag">团队动态 · Team News</span>
      <h1>{title}</h1>
      <p class="date">{date}</p>
      <p class="desc">{desc}</p>
      <a class="btn" id="shareBtn" href="javascript:void(0)" onclick="shareThis()">分享给朋友 →</a>
      <a class="btn btn-ghost" href="{site}/?news={id}">在网站查看完整内容</a>
      <p class="hint">点「分享给朋友」即可直接发到微信等应用</p>
    </div>
  </div>
  <script>
    function shareThis(){{
      var url=location.href;
      var title=document.title;
      var meta=document.querySelector('meta[property="og:description"]');
      var text=meta?meta.getAttribute('content'):'';
      if(navigator.share){{
        navigator.share({{title:title,text:text,url:url}}).catch(function(){{}});
      }} else {{
        var t=document.createElement('textarea');t.value=url;document.body.appendChild(t);t.select();
        try{{document.execCommand('copy');}}catch(e){{}}
        document.body.removeChild(t);
        var b=document.getElementById('shareBtn');if(b){{b.textContent='链接已复制，去微信粘贴';}}
      }}
    }}
  </script>
</body>
</html>
"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def first_text(n):
    for b in n.get("blocks") or []:
        if b.get("type") == "text":
            t = b.get("zh") or b.get("en") or b.get("text") or ""
            t = re.sub(r"\s+", " ", str(t)).strip()
            if t:
                return t[:150]
    return ""


def first_image(n):
    for b in n.get("blocks") or []:
        if b.get("type") == "image" and str(b.get("src") or "").startswith("http"):
            return b["src"]
    return ""


def main():
    with open(os.path.join(HERE, "content.json"), encoding="utf-8") as f:
        data = json.load(f)
    news = data.get("news") or []
    os.makedirs(OUT_DIR, exist_ok=True)
    written = 0
    for n in news:
        nid = n.get("id")
        if not nid:
            continue
        title = n.get("titleZh") or n.get("titleEn") or n.get("title") or "团队动态"
        desc = first_text(n) or (n.get("titleEn") or "")
        date = n.get("date") or n.get("day") or ""
        img = first_image(n)
        url = f"{SITE}/news/{nid}.html"
        cover_img = f'<img src="{esc(img)}" alt="{esc(title)}">' if img else ""
        page = TPL.format(
            title=esc(title), desc=esc(desc), img=esc(img), url=esc(url),
            site=SITE, id=esc(nid), date=esc(date), cover_img=cover_img,
        )
        out = os.path.join(OUT_DIR, f"{nid}.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(page)
        written += 1
        print(f"  generated news/{nid}.html  (title={title[:30]!r}, img={'yes' if img else 'no'})")
    print(f"DONE: {written} share page(s) -> {OUT_DIR}")


if __name__ == "__main__":
    sys.exit(main())
