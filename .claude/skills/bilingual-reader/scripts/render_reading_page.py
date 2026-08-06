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
import hashlib
import html
import re
import sys


def esc(s):
    return html.escape(s or "", quote=False)


def nid(doc_key, en):
    """Stable per-block note id.

    Derived from the block's English text, not its position, so that adding
    sections to a spec and re-rendering keeps existing annotations attached to
    the paragraphs they were written against. Editing a paragraph's English
    does orphan its note — that is the deliberate trade: a note about a
    sentence that no longer exists should not silently reattach elsewhere.
    """
    h = hashlib.md5((doc_key + "\x00" + re.sub(r"\s+", " ", en or "").strip()).encode("utf-8"))
    return h.hexdigest()[:10]


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

/* ---- annotations ---- */
.note{margin:.55rem 0 0}
.note-add{font-family:var(--font-sans);font-size:.7rem;color:var(--muted);background:none;
          border:1px dashed var(--line);border-radius:4px;padding:.25rem .6rem;cursor:pointer;
          opacity:.55;transition:opacity .15s,border-color .15s}
.bipara:hover .note-add, blockquote.cited:hover .note-add, .note-add:focus{opacity:1;border-color:var(--accent);color:var(--accent)}
.note.has .note-add{display:none}
.note-body{display:none;font-family:var(--font-zh);font-size:.87rem;line-height:1.8;
           color:var(--ink-soft);background:var(--accent-soft);border-left:3px solid var(--accent);
           border-radius:3px;padding:.55rem .75rem;cursor:text;white-space:pre-wrap;word-break:break-word}
.note.has .note-body{display:block}
.note-body .lbl{display:block;font-family:var(--font-sans);font-size:.62rem;letter-spacing:.06em;
                color:var(--accent);margin-bottom:.25rem;opacity:.85}
.note-edit{display:none;width:100%;font-family:var(--font-zh);font-size:.87rem;line-height:1.8;
           color:var(--ink);background:var(--paper);border:1px solid var(--accent);border-radius:3px;
           padding:.55rem .75rem;resize:vertical;min-height:4.2rem}
.note-edit:focus{outline:none;box-shadow:0 0 0 2px var(--accent-soft)}
.note.editing .note-body,.note.editing .note-add{display:none}
.note.editing .note-edit{display:block}
.note-status{font-family:var(--font-sans);font-size:.62rem;color:var(--accent);
             margin-top:.22rem;height:.9rem;opacity:0;transition:opacity .2s}
.note-status.show{opacity:.8}

/* ---- notes drawer ---- */
#notesBtn{position:fixed;right:.9rem;bottom:.9rem;z-index:60;font-family:var(--font-sans);
          font-size:.72rem;background:var(--accent);color:var(--paper);border:none;
          border-radius:999px;padding:.55rem .95rem;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.18)}
#notesBtn .n{background:rgba(255,255,255,.28);border-radius:999px;padding:0 .35rem;margin-left:.3rem}
#notesPanel{position:fixed;inset:auto 0 0 0;max-height:78vh;z-index:70;background:var(--paper);
            border-top:1px solid var(--line);box-shadow:0 -4px 24px rgba(0,0,0,.2);
            display:none;flex-direction:column}
#notesPanel.open{display:flex}
#notesPanel header{display:flex;align-items:center;gap:.6rem;padding:.7rem 1rem;
                   border-bottom:1px solid var(--line);font-family:var(--font-sans);font-size:.8rem}
#notesPanel header strong{flex:1}
#notesPanel button{font-family:var(--font-sans);font-size:.68rem;border:1px solid var(--line);
                   background:transparent;color:var(--muted);border-radius:4px;padding:.3rem .6rem;cursor:pointer}
#notesPanel button:hover{border-color:var(--accent);color:var(--accent)}
#notesList{overflow-y:auto;padding:.6rem 1rem 1.4rem;max-width:46rem;margin:0 auto;width:100%}
.nrow{padding:.7rem 0;border-bottom:1px dashed var(--line)}
.nrow:last-child{border-bottom:none}
.nrow .src{font-family:var(--font-sans);font-size:.68rem;color:var(--muted);line-height:1.5;
           margin-bottom:.3rem;cursor:pointer}
.nrow .src:hover{color:var(--accent)}
.nrow .txt{font-family:var(--font-zh);font-size:.86rem;line-height:1.8;color:var(--ink-soft);white-space:pre-wrap}
.nempty{font-family:var(--font-sans);font-size:.76rem;color:var(--muted);padding:1.2rem 0;text-align:center}
@media print{#notesBtn,#notesPanel,.note-add,.note-edit,.topbar{display:none!important}
             .note.has .note-body{display:block}}

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

/* ---------------- annotations ---------------- */
(function(){
  var KEY='br-notes:'+(window.__BR_DOC||'doc');
  var notes={};
  try{ notes=JSON.parse(localStorage.getItem(KEY)||'{}'); }catch(e){ notes={}; }

  function persist(){
    try{ localStorage.setItem(KEY, JSON.stringify(notes)); return true; }
    catch(e){ return false; }
  }
  function count(){ return Object.keys(notes).filter(function(k){return (notes[k]||'').trim();}).length; }
  function refreshBtn(){
    var b=document.getElementById('notesBtn');
    if(b) b.querySelector('.n').textContent=count();
  }
  function paint(wrap){
    var id=wrap.dataset.nid, v=(notes[id]||'').trim();
    var body=wrap.querySelector('.note-body');
    if(v){ wrap.classList.add('has'); body.innerHTML='<span class="lbl">我的批注</span>'; body.appendChild(document.createTextNode(v)); }
    else { wrap.classList.remove('has'); body.textContent=''; }
  }
  function flash(wrap){
    var s=wrap.querySelector('.note-status');
    var t=new Date();
    s.textContent='已保存 · '+String(t.getHours()).padStart(2,'0')+':'+String(t.getMinutes()).padStart(2,'0');
    s.classList.add('show');
    clearTimeout(wrap.__ft); wrap.__ft=setTimeout(function(){ s.classList.remove('show'); },1800);
  }
  function save(wrap){
    var id=wrap.dataset.nid, ta=wrap.querySelector('.note-edit');
    var v=ta.value.trim();
    if(v) notes[id]=v; else delete notes[id];
    if(persist()){ flash(wrap); } else {
      var s=wrap.querySelector('.note-status');
      s.textContent='保存失败(浏览器存储不可用)'; s.classList.add('show');
    }
    paint(wrap); refreshBtn();
  }
  function edit(wrap){
    var ta=wrap.querySelector('.note-edit');
    ta.value=notes[wrap.dataset.nid]||'';
    wrap.classList.add('editing');
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    autogrow(ta);
  }
  function autogrow(ta){ ta.style.height='auto'; ta.style.height=(ta.scrollHeight+2)+'px'; }

  document.querySelectorAll('.note').forEach(function(wrap){
    paint(wrap);
    wrap.querySelector('.note-add').addEventListener('click', function(){ edit(wrap); });
    wrap.querySelector('.note-body').addEventListener('click', function(){ edit(wrap); });
    var ta=wrap.querySelector('.note-edit');
    ta.addEventListener('input', function(){
      autogrow(ta);
      clearTimeout(wrap.__st);
      wrap.__st=setTimeout(function(){ save(wrap); }, 500);
    });
    ta.addEventListener('blur', function(){
      clearTimeout(wrap.__st); save(wrap); wrap.classList.remove('editing');
    });
    ta.addEventListener('keydown', function(e){
      if(e.key==='Escape'){ ta.blur(); }
      if(e.key==='Enter' && (e.metaKey||e.ctrlKey)){ ta.blur(); }
    });
  });
  refreshBtn();

  /* drawer */
  var panel=document.getElementById('notesPanel');
  document.getElementById('notesBtn').addEventListener('click', function(){
    buildList(); panel.classList.toggle('open');
  });
  document.getElementById('notesClose').addEventListener('click', function(){ panel.classList.remove('open'); });

  function entries(){
    var out=[];
    document.querySelectorAll('.note').forEach(function(w){
      var v=(notes[w.dataset.nid]||'').trim();
      if(!v) return;
      var host=w.closest('.bipara')||w.closest('blockquote');
      var en=host?host.querySelector('.en'):null;
      out.push({el:host, src:en?en.textContent.trim():'', txt:v});
    });
    return out;
  }
  function buildList(){
    var list=document.getElementById('notesList'), rows=entries();
    list.innerHTML='';
    if(!rows.length){ list.innerHTML='<div class="nempty">还没有批注。点击任意段落下方的「＋ 批注」开始。</div>'; return; }
    rows.forEach(function(r){
      var d=document.createElement('div'); d.className='nrow';
      var s=document.createElement('div'); s.className='src';
      s.textContent='“'+r.src.slice(0,110)+(r.src.length>110?'…':'')+'”';
      s.addEventListener('click', function(){
        panel.classList.remove('open');
        r.el.scrollIntoView({behavior:'smooth',block:'center'});
      });
      var t=document.createElement('div'); t.className='txt'; t.textContent=r.txt;
      d.appendChild(s); d.appendChild(t); list.appendChild(d);
    });
  }
  function markdown(){
    var rows=entries();
    var out=['# 批注 — '+(document.title||'')+'\\n'];
    rows.forEach(function(r){
      out.push('> '+r.src.replace(/\\n+/g,' '));
      out.push('');
      out.push(r.txt);
      out.push('');
      out.push('---');
      out.push('');
    });
    return out.join('\\n');
  }
  document.getElementById('notesCopy').addEventListener('click', function(){
    var md=markdown(), btn=this;
    function done(ok){ btn.textContent = ok?'已复制':'复制失败'; setTimeout(function(){btn.textContent='复制为 Markdown';},1600); }
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(md).then(function(){done(true);},function(){done(false);});
    } else {
      var ta=document.createElement('textarea'); ta.value=md; document.body.appendChild(ta);
      ta.select(); var ok=false; try{ ok=document.execCommand('copy'); }catch(e){}
      document.body.removeChild(ta); done(ok);
    }
  });
  document.getElementById('notesClear').addEventListener('click', function(){
    if(!confirm('清空本篇全部批注?此操作无法撤销。')) return;
    notes={}; persist();
    document.querySelectorAll('.note').forEach(paint);
    refreshBtn(); buildList();
  });
})();
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

    doc_key = m.get("doc_id") or m.get("title_en") or "doc"

    def note(en):
        return (
            f'<div class="note" data-nid="{nid(doc_key, en)}">'
            '<div class="note-body"></div>'
            '<textarea class="note-edit" placeholder="写下你的批注…（自动保存；Esc 或 ⌘/Ctrl+Enter 收起）"></textarea>'
            '<button class="note-add" type="button">＋ 批注</button>'
            '<div class="note-status"></div>'
            "</div>"
        )

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
            a(note(en))
            a("</blockquote>")
        else:
            a('<div class="bipara">')
            a(f'<p class="en">{esc(en)}</p>')
            a(f'<p class="zh">{zh}</p>')
            a(note(en))
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

    a('<button id="notesBtn" type="button">批注 <span class="n">0</span></button>')
    a('<div id="notesPanel"><header><strong>我的批注</strong>'
      '<button id="notesCopy" type="button">复制为 Markdown</button>'
      '<button id="notesClear" type="button">清空</button>'
      '<button id="notesClose" type="button">关闭</button></header>'
      '<div id="notesList"></div></div>')

    a(f"<script>window.__BR_DOC={json.dumps(doc_key)};</script>")
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
