#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a bilingual (EN/ZH) deep-reading page from a JSON spec.

Usage:
    python render_reading_page.py spec.json output.html

The spec carries the content; this script owns all presentation. That split is
the point: producing one of these pages should cost you a JSON file of
translation work, not several hundred lines of re-typed CSS.

See SKILL.md for the spec schema and the translation conventions.
"""
import json
import html
import sys


def esc(s):
    return html.escape(s or "", quote=False)


CSS = """
:root {
  --paper:#FAFAF8; --ink:#1a1a1a; --ink-soft:#333; --muted:#5f6b64;
  --line:#dfe3df; --accent:#2B5C6B; --accent-soft:#eef4f5;
  --hl:#9C6B33; --hl-soft:#f7efe3; --zh-bg:#f1f3f0;
  --font-serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif;
  --font-zh:"Songti SC","STSong","Noto Serif SC","PingFang SC","Hiragino Sans GB",serif;
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"PingFang SC",sans-serif;
}
:root[data-theme="dark"]{
  --paper:#14181a; --ink:#e8ece9; --ink-soft:#d2d8d4; --muted:#9aa8a0;
  --line:#333d3a; --accent:#7EB3C0; --accent-soft:#1a2729;
  --hl:#D6A85F; --hl-soft:#2a2419; --zh-bg:#1c2220;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#14181a; --ink:#e8ece9; --ink-soft:#d2d8d4; --muted:#9aa8a0;
    --line:#333d3a; --accent:#7EB3C0; --accent-soft:#1a2729;
    --hl:#D6A85F; --hl-soft:#2a2419; --zh-bg:#1c2220;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-serif);
     line-height:1.7;-webkit-font-smoothing:antialiased;-webkit-tap-highlight-color:transparent}

.topbar{position:sticky;top:0;z-index:50;background:var(--paper);
        border-bottom:1px solid var(--line);padding:.6rem 1rem .4rem}
.topbar-inner{max-width:46rem;margin:0 auto;display:flex;align-items:center;gap:.75rem}
.crumb{font-family:var(--font-sans);font-size:.7rem;color:var(--muted);flex:1;
       white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.modes{display:flex;gap:.25rem;flex-shrink:0}
.modes button{font-family:var(--font-sans);font-size:.68rem;border:1px solid var(--line);
              background:transparent;color:var(--muted);padding:.28rem .55rem;border-radius:999px;
              cursor:pointer;transition:all .15s}
.modes button.active{background:var(--accent);color:var(--paper);border-color:var(--accent)}
.progress{height:2px;background:var(--line);max-width:46rem;margin:.4rem auto 0;position:relative}
.progress span{position:absolute;left:0;top:0;bottom:0;width:0;background:var(--accent)}

main{max-width:46rem;margin:0 auto;padding:1.8rem 1.1rem 5rem}

.eyebrow{font-family:var(--font-sans);font-size:.65rem;text-transform:uppercase;
         letter-spacing:.14em;color:var(--hl);margin:0 0 .55rem;font-weight:700}
h1.title{font-size:1.5rem;line-height:1.3;margin:0 0 .5rem;font-weight:600;text-wrap:balance}
h1.title .zh{display:block;font-family:var(--font-zh);font-size:1.13rem;color:var(--muted);
             margin-top:.35rem;font-weight:500}
.byline{font-family:var(--font-sans);font-size:.82rem;color:var(--muted);margin:0 0 1rem;line-height:1.6}
.citation{font-family:var(--font-sans);font-size:.72rem;color:var(--muted);
          background:var(--accent-soft);border-left:3px solid var(--accent);
          padding:.7rem .9rem;border-radius:3px;margin:0 0 1.2rem;line-height:1.65}
.readnote{font-family:var(--font-sans);font-size:.76rem;color:var(--ink-soft);
          background:var(--hl-soft);border-left:3px solid var(--hl);
          padding:.7rem .9rem;border-radius:3px;margin:0 0 1.6rem;line-height:1.65}

article h2{margin:2.4rem 0 .9rem;padding-bottom:.45rem;border-bottom:1px solid var(--line)}
article h2 .en{display:block;font-size:1.08rem;color:var(--accent);font-weight:600}
article h2 .zh{display:block;font-family:var(--font-zh);font-size:.97rem;color:var(--accent);
               font-weight:600;margin-top:.22rem;opacity:.85}
article h3{margin:1.8rem 0 .7rem}
article h3 .en{display:block;font-size:.97rem;color:var(--ink);font-weight:600;font-style:italic}
article h3 .zh{display:block;font-family:var(--font-zh);font-size:.9rem;color:var(--ink-soft);margin-top:.18rem}

.bipara{margin:0 0 1.35rem;padding-bottom:1rem;border-bottom:1px dashed var(--line)}
.bipara:last-child{border-bottom:none}
.bipara p.en{margin:0 0 .55rem;color:var(--ink-soft);text-align:justify;hyphens:auto}
.bipara p.zh{margin:0;font-family:var(--font-zh);color:var(--muted);font-size:.92rem;
             line-height:1.9;background:var(--zh-bg);padding:.7rem .85rem;border-radius:3px}

blockquote.cited{margin:1.3rem 0 1.6rem;padding:.95rem 1.05rem;border-left:3px solid var(--hl);
                 background:var(--hl-soft);border-radius:3px}
blockquote.cited p.en{margin:0 0 .55rem;color:var(--ink-soft);font-style:italic;font-size:.93rem}
blockquote.cited p.zh{margin:0 0 .6rem;font-family:var(--font-zh);color:var(--ink-soft);
                      font-size:.9rem;line-height:1.9}
blockquote.cited .attrib{font-family:var(--font-sans);font-size:.71rem;color:var(--hl);
                         border-top:1px solid rgba(156,107,51,.28);padding-top:.45rem;
                         margin-top:.2rem;line-height:1.6;display:block}

a.gref{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent);cursor:help}
a.gref:hover{background:var(--accent-soft)}

body.zh-only .bipara p.en, body.zh-only article h2 .en,
body.zh-only article h3 .en, body.zh-only blockquote.cited p.en{display:none}
body.en-only .bipara p.zh, body.en-only article h2 .zh,
body.en-only article h3 .zh, body.en-only blockquote.cited p.zh{display:none}

details.pack{margin-top:2.2rem;border-top:1px solid var(--line);padding-top:.9rem}
details.pack summary{cursor:pointer;font-size:1rem;color:var(--accent);font-weight:600;
                     list-style:none;padding:.35rem 0;font-family:var(--font-sans)}
details.pack summary::-webkit-details-marker{display:none}
details.pack summary::before{content:"▸ "}
details.pack[open] summary::before{content:"▾ "}

.gitem{margin:.9rem 0;padding-bottom:.8rem;border-bottom:1px dashed var(--line)}
.gitem:last-child{border-bottom:none}
.gitem .cat{display:inline-block;font-family:var(--font-sans);font-size:.62rem;
            letter-spacing:.05em;color:var(--paper);background:var(--muted);
            padding:.12rem .45rem;border-radius:999px;margin-right:.45rem;vertical-align:.12em}
.gitem .term{font-family:var(--font-zh);font-weight:600;color:var(--ink)}
.gitem .def{font-family:var(--font-zh);font-size:.87rem;color:var(--muted);
            line-height:1.85;margin:.4rem 0 0}
.gitem:target{background:var(--accent-soft);border-radius:3px;padding:.6rem;margin-left:-.6rem;margin-right:-.6rem}

.refs{font-family:var(--font-sans);font-size:.72rem;color:var(--muted);line-height:1.8;margin-top:.8rem}

footer{margin-top:2.6rem;padding-top:1rem;border-top:1px solid var(--line);
       font-family:var(--font-sans);font-size:.7rem;color:var(--muted);line-height:1.7}

@media (max-width:520px){
  h1.title{font-size:1.25rem}
  article h2 .en{font-size:1rem}
  main{padding:1.3rem .9rem 3.5rem}
  .bipara p.zh{font-size:.9rem}
}
"""

JS = """
function setMode(m, btn){
  document.body.className = m;
  document.querySelectorAll('.modes button').forEach(b=>b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  try{ localStorage.setItem('brMode', m); }catch(e){}
}
document.addEventListener('DOMContentLoaded', function(){
  var saved='bilingual';
  try{ saved = localStorage.getItem('brMode') || 'bilingual'; }catch(e){}
  var map={'bilingual':0,'en-only':1,'zh-only':2};
  var btns=document.querySelectorAll('.modes button');
  setMode(saved, btns[map[saved]!==undefined?map[saved]:0]);
});
document.addEventListener('scroll', function(){
  var h=document.documentElement;
  var pct=(h.scrollTop)/((h.scrollHeight-h.clientHeight)||1)*100;
  var bar=document.querySelector('.progress span');
  if(bar) bar.style.width=Math.min(100,Math.max(0,pct))+'%';
}, {passive:true});
"""


def render(spec):
    m = spec.get("meta", {})
    out = []
    a = out.append

    title = m.get("title_en") or "Bilingual reading"
    a(f"<title>{esc(title)}{' — 中英对照' if m.get('title_zh') else ''}</title>")
    a('<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
    a(f"<style>{CSS}</style>")

    a('<div class="topbar"><div class="topbar-inner">')
    a(f'<span class="crumb">{esc(m.get("crumb") or title)}</span>')
    a('<div class="modes">'
      '<button onclick="setMode(\'bilingual\',this)">双语</button>'
      '<button onclick="setMode(\'en-only\',this)">EN</button>'
      '<button onclick="setMode(\'zh-only\',this)">中文</button>'
      '</div>')
    a('</div><div class="progress"><span></span></div></div>')

    a("<main>")
    if m.get("eyebrow"):
        a(f'<div class="eyebrow">{esc(m["eyebrow"])}</div>')
    a('<h1 class="title">' + esc(m.get("title_en", "")))
    if m.get("title_zh"):
        a(f'<span class="zh">{esc(m["title_zh"])}</span>')
    a("</h1>")
    if m.get("byline"):
        a(f'<div class="byline">{esc(m["byline"])}</div>')
    if m.get("citation"):
        a(f'<div class="citation"><strong>Cite as</strong> · {esc(m["citation"])}</div>')
    if m.get("note"):
        a(f'<div class="readnote">{m["note"]}</div>')

    a("<article>")
    for it in spec.get("items", []):
        k = it.get("kind")
        en, zh = it.get("en", ""), it.get("zh", "")
        if k in ("h2", "h3"):
            a(f'<{k}><span class="en">{esc(en)}</span><span class="zh">{esc(zh)}</span></{k}>')
        elif k == "quote":
            a('<blockquote class="cited">')
            a(f'<p class="en">{esc(en)}</p>')
            a(f'<p class="zh">{zh}</p>')
            if it.get("attrib"):
                a(f'<span class="attrib">{esc(it["attrib"])}</span>')
            a("</blockquote>")
        else:
            a('<div class="bipara">')
            a(f'<p class="en">{esc(en)}</p>')
            a(f'<p class="zh">{zh}</p>')
            a("</div>")
    a("</article>")

    gl = spec.get("glossary", [])
    if gl:
        a(f'<details class="pack" open><summary>名词与人物详解 <span style="font-weight:400;font-size:.75rem">({len(gl)} 条)</span></summary>')
        for g in gl:
            gid = esc(g.get("id", ""))
            a(f'<div class="gitem" id="{gid}">')
            if g.get("cat"):
                a(f'<span class="cat">{esc(g["cat"])}</span>')
            a(f'<span class="term">{esc(g.get("term",""))}</span>')
            a(f'<p class="def">{g.get("def","")}</p>')
            a("</div>")
        a("</details>")

    if spec.get("references"):
        a('<details class="pack"><summary>References（原文参考文献）</summary>')
        a(f'<p class="refs">{spec["references"]}</p></details>')

    if m.get("footer"):
        a(f"<footer>{m['footer']}</footer>")
    a("</main>")
    a(f"<script>{JS}</script>")
    return "\n".join(out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)
    out = render(spec)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(out)
    n_items = len(spec.get("items", []))
    n_q = sum(1 for i in spec.get("items", []) if i.get("kind") == "quote")
    n_g = len(spec.get("glossary", []))
    print(f"wrote {sys.argv[2]}: {n_items} blocks ({n_q} quotes), {n_g} glossary entries")


if __name__ == "__main__":
    main()
