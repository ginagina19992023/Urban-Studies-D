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
.modes{display:flex;gap:.3rem;flex-shrink:0}
.modes button{font-family:var(--font-sans);font-size:.7rem;border:1px solid var(--line);
              background:transparent;color:var(--muted);padding:.4rem .7rem;border-radius:999px;
              min-height:2.1rem;cursor:pointer;transition:all .15s}
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
.gitem:target,.gitem.flash{background:var(--accent-soft);border-radius:3px;padding:.6rem;margin-left:-.6rem;margin-right:-.6rem;transition:background 1.2s}

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

/* ---- navigator (floating button + tabbed panel: 目录 / 术语 / 批注) ---- */
#navBtn{position:fixed;right:.9rem;bottom:calc(.9rem + env(safe-area-inset-bottom,0px));z-index:60;
        font-family:var(--font-sans);font-size:.75rem;background:var(--accent);color:var(--paper);
        border:none;border-radius:999px;padding:.65rem 1.05rem;min-height:2.6rem;cursor:pointer;
        box-shadow:0 2px 10px rgba(0,0,0,.18);display:flex;align-items:center;gap:.4rem}
#navBtn .n{background:rgba(255,255,255,.28);border-radius:999px;padding:.05rem .45rem;
           display:inline-block;min-width:.6rem;text-align:center}
#navBtn .n:empty,#navBtn .n[data-zero="1"]{opacity:.55}

#navBackdrop{position:fixed;inset:0;z-index:65;background:rgba(0,0,0,.35);
             display:none;-webkit-tap-highlight-color:transparent}
#navBackdrop.open{display:block}

#navPanel{position:fixed;inset:auto 0 0 0;max-height:82vh;z-index:70;background:var(--paper);
          border-top:1px solid var(--line);box-shadow:0 -4px 24px rgba(0,0,0,.2);
          border-radius:14px 14px 0 0;
          display:none;flex-direction:column;
          padding-bottom:env(safe-area-inset-bottom,0px)}
#navPanel.open{display:flex}

.navtabs{display:flex;align-items:stretch;border-bottom:1px solid var(--line);
         font-family:var(--font-sans);flex-shrink:0}
.navtab{flex:1;background:none;border:none;color:var(--muted);font-size:.78rem;font-weight:600;
        padding:.8rem .4rem;min-height:2.7rem;cursor:pointer;border-bottom:2px solid transparent;
        display:flex;align-items:center;justify-content:center;gap:.3rem}
.navtab.active{color:var(--accent);border-bottom-color:var(--accent)}
.navtab .navbadge{font-size:.65rem;background:var(--line);color:var(--ink-soft);border-radius:999px;
                  padding:.02rem .4rem}
.navtab.active .navbadge{background:var(--accent-soft);color:var(--accent)}
#navClose{flex:0 0 auto;width:2.9rem;min-height:2.7rem;background:none;border:none;color:var(--muted);
          font-size:1rem;cursor:pointer}

.navbody{overflow-y:auto;padding:.7rem 1rem 1.2rem;max-width:46rem;margin:0 auto;width:100%}
.navpane[hidden]{display:none}

.tocrow{display:block;width:100%;text-align:left;background:none;border:none;cursor:pointer;
        font-family:var(--font-sans);color:var(--ink-soft);padding:.55rem .3rem;min-height:2.6rem;
        border-bottom:1px dashed var(--line)}
.tocrow:last-child{border-bottom:none}
.tocrow.lvl-h3{padding-left:1.3rem;color:var(--muted)}
.tocrow .en{display:block;font-size:.86rem;font-weight:600}
.tocrow.lvl-h3 .en{font-weight:500;font-size:.82rem;font-style:italic}
.tocrow .zh{display:block;font-family:var(--font-zh);font-size:.78rem;color:var(--muted);margin-top:.1rem}
.tocrow:hover .en{color:var(--accent)}

#gSearch{width:100%;font-family:var(--font-sans);font-size:.85rem;border:1px solid var(--line);
         background:var(--zh-bg);color:var(--ink);border-radius:6px;padding:.6rem .8rem;
         min-height:2.6rem;margin-bottom:.6rem}
#gSearch:focus{outline:none;border-color:var(--accent)}
.gcat-header{font-family:var(--font-sans);font-size:.65rem;letter-spacing:.08em;color:var(--hl);
             text-transform:uppercase;font-weight:700;margin:1rem 0 .3rem}
.gcat-header:first-child{margin-top:0}
.gpick{display:block;width:100%;text-align:left;background:none;border:none;cursor:pointer;
       padding:.55rem .3rem;border-bottom:1px dashed var(--line)}
.gpick:last-child{border-bottom:none}
.gpick .term{display:block;font-family:var(--font-zh);font-weight:600;color:var(--ink);font-size:.9rem}
.gpick .def{display:block;font-family:var(--font-zh);font-size:.78rem;color:var(--muted);
            margin-top:.15rem;line-height:1.6;
            display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.gpick:hover .term{color:var(--accent)}
.gempty{font-family:var(--font-sans);font-size:.76rem;color:var(--muted);padding:1.2rem 0;text-align:center}

#notesTools{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 .8rem}
#notesTools button{font-family:var(--font-sans);font-size:.72rem;border:1px solid var(--line);
                   background:transparent;color:var(--ink-soft);border-radius:6px;
                   padding:.5rem .75rem;min-height:2.4rem;cursor:pointer;transition:all .15s}
#notesTools button:hover{border-color:var(--accent);color:var(--accent)}
#notesTools button.primary{background:var(--accent);color:var(--paper);border-color:var(--accent)}
#notesHint{font-family:var(--font-sans);font-size:.68rem;color:var(--muted);line-height:1.6;
           margin:0 0 .8rem;padding:.5rem .65rem;background:var(--zh-bg);border-radius:4px}
#notesList .nrow{padding:.7rem .3rem;border-bottom:1px dashed var(--line)}
#notesList .nrow:last-child{border-bottom:none}
#notesList .nrow .src{font-family:var(--font-sans);font-size:.72rem;color:var(--muted);line-height:1.5;
           margin-bottom:.3rem;cursor:pointer;min-height:1.6rem}
#notesList .nrow .src:hover{color:var(--accent)}
#notesList .nrow .txt{font-family:var(--font-zh);font-size:.86rem;line-height:1.8;color:var(--ink-soft);white-space:pre-wrap}
.nempty{font-family:var(--font-sans);font-size:.76rem;color:var(--muted);padding:1.2rem 0;text-align:center}
#notesJumpRow{padding:.8rem .3rem .2rem;text-align:center}
#notesJump{font-family:var(--font-sans);font-size:.75rem;border:1px solid var(--line);background:none;
           color:var(--accent);border-radius:6px;padding:.5rem 1rem;min-height:2.4rem;cursor:pointer}

/* shared list-row styling reused across tabs, kept generic on purpose */
.nrow{padding:.7rem 0;border-bottom:1px dashed var(--line)}
.nrow:last-child{border-bottom:none}
.nrow .src{font-family:var(--font-sans);font-size:.68rem;color:var(--muted);line-height:1.5;
           margin-bottom:.3rem;cursor:pointer}
.nrow .src:hover{color:var(--accent)}
.nrow .txt{font-family:var(--font-zh);font-size:.86rem;line-height:1.8;color:var(--ink-soft);white-space:pre-wrap}

/* ---- end-of-document overview ---- */
#overview{margin-top:2.6rem;border-top:2px solid var(--accent);padding-top:1.1rem}
#overview h2.ovh{font-family:var(--font-sans);font-size:1.02rem;color:var(--accent);
                 font-weight:700;margin:0 0 .2rem;border:none;padding:0}
#overview .ovsub{font-family:var(--font-sans);font-size:.72rem;color:var(--muted);
                 margin:0 0 .9rem;line-height:1.6}
#ovTools{display:flex;flex-wrap:wrap;gap:.4rem;margin:.9rem 0 .2rem}
#ovTools button{font-family:var(--font-sans);font-size:.7rem;border:1px solid var(--line);
                background:transparent;color:var(--ink-soft);border-radius:4px;
                padding:.4rem .7rem;cursor:pointer;transition:all .15s}
#ovTools button:hover{border-color:var(--accent);color:var(--accent)}
#ovTools button.primary{background:var(--accent);color:var(--paper);border-color:var(--accent)}
#ovTools button.danger:hover{border-color:var(--warn,#8A3B2C);color:var(--warn,#8A3B2C)}
#ovHint{font-family:var(--font-sans);font-size:.68rem;color:var(--muted);
        line-height:1.7;margin-top:.7rem;padding:.6rem .8rem;background:var(--zh-bg);border-radius:4px}

/* ---- baked-in AI commentary (static, written by Claude, not generated by the page) ---- */
#aiCommentary{margin-top:2.6rem;border-top:2px solid var(--hl);padding-top:1.1rem}
.aic-entry{margin:0 0 1.8rem;padding-bottom:1.4rem;border-bottom:1px dashed var(--line)}
.aic-entry:last-child{border-bottom:none}
.aic-date{font-family:var(--font-sans);font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;
          color:var(--hl);font-weight:700;margin-bottom:.6rem}
.aic-body{font-family:var(--font-zh);font-size:.92rem;line-height:1.85;color:var(--ink-soft)}
.aic-body h3{font-family:var(--font-sans);font-size:.85rem;color:var(--hl);margin:1.3rem 0 .5rem;
             font-weight:700}
.aic-body h3:first-child{margin-top:0}
.aic-body p{margin:0 0 .8rem}
.aic-body ul{margin:0 0 .8rem;padding-left:1.3rem}
.aic-body li{margin:0 0 .5rem}
.aic-body blockquote{margin:.6rem 0;padding:.5rem .8rem;border-left:3px solid var(--line);
                      background:var(--zh-bg);font-size:.88rem;color:var(--muted)}
@media print{#navBtn,#navPanel,.note-add,.note-edit,.topbar{display:none!important}
             .note.has .note-body{display:block}}

footer{margin-top:2.6rem;padding-top:1rem;border-top:1px solid var(--line);
       font-family:var(--font-sans);font-size:.7rem;color:var(--muted);line-height:1.7}

@media (max-width:520px){
  h1.title{font-size:1.3rem}
  article h2 .en{font-size:1.05rem}
  main{padding:1.3rem .9rem 5.5rem}
  article{font-size:1rem}
  .bipara p.en{font-size:1rem}
  .bipara p.zh{font-size:.95rem;padding:.8rem .9rem}
  blockquote.cited p.en,blockquote.cited p.zh{font-size:.95rem}
  .note-add{padding:.5rem .8rem;min-height:2.3rem}
  .crumb{font-size:.68rem}
  #navBtn{padding:.7rem 1.1rem;font-size:.8rem}
  .navtab{font-size:.82rem}
  a.gref{padding:.05rem 0}
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
    var n=count();
    var badge=document.querySelector('#navBtn .n');
    if(badge){ badge.textContent=n; badge.dataset.zero = n===0 ? '1' : '0'; }
    var tabBadge=document.getElementById('notesTabBadge');
    if(tabBadge) tabBadge.textContent=n;
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
    paint(wrap);
    /* rebuild both views, not just the badge: the end-of-document overview is
       always on the page, so a note written mid-read must appear there without
       requiring the drawer to be opened first. */
    refreshAll();
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
  var panel=document.getElementById('navPanel');

  function entries(){
    var out=[];
    document.querySelectorAll('.note').forEach(function(w){
      var v=(notes[w.dataset.nid]||'').trim();
      if(!v) return;
      var host=w.closest('.bipara')||w.closest('blockquote');
      var en=host?host.querySelector('.en'):null;
      var zh=host?host.querySelector('.zh'):null;
      out.push({el:host, src:en?en.textContent.trim():'',
                zh:zh?zh.textContent.trim():'', txt:v,
                isQuote: !!(host&&host.tagName==='BLOCKQUOTE')});
    });
    return out;
  }
  function buildList(list, closeAfterJump){
    var rows=entries();
    list.innerHTML='';
    if(!rows.length){
      list.innerHTML='<div class="nempty">还没有批注。点击任意段落下方的「＋ 批注」开始。</div>';
      return;
    }
    rows.forEach(function(r){
      var d=document.createElement('div'); d.className='nrow';
      var s=document.createElement('div'); s.className='src';
      s.textContent=(r.isQuote?'［引文］“':'“')+r.src.slice(0,110)+(r.src.length>110?'…':'')+'”';
      s.addEventListener('click', function(){
        if(closeAfterJump) closePanel();
        r.el.scrollIntoView({behavior:'smooth',block:'center'});
      });
      var t=document.createElement('div'); t.className='txt'; t.textContent=r.txt;
      d.appendChild(s); d.appendChild(t); list.appendChild(d);
    });
  }
  function refreshAll(){
    buildList(document.getElementById('notesList'), true);
    buildList(document.getElementById('ovList'), false);
    refreshBtn();
  }

  var TITLE=document.querySelector('h1.title') ? document.querySelector('h1.title').textContent.trim() : '';
  var CITE=document.querySelector('.citation') ? document.querySelector('.citation').textContent.trim() : '';

  function markdown(){
    var rows=entries();
    var out=['# 批注 — '+TITLE, '', CITE, ''];
    rows.forEach(function(r){
      out.push('> '+r.src.replace(/\\s+/g,' '));
      out.push('');
      out.push(r.txt);
      out.push('');
      out.push('---');
      out.push('');
    });
    return out.join('\\n');
  }

  function reviewPrompt(){
    var rows=entries();
    var out=[];
    out.push('我正在精读下面这篇文献，附上原文段落与我自己写的批注。请据此完成三件事，要具体，不要泛泛而谈：');
    out.push('');
    out.push('【1. 提炼】我的批注实际上在追问什么？归纳成 2–4 条主线问题，并指出我可能自己还没意识到的关注点。');
    out.push('【2. 评价】逐条判断：哪些批注准确抓住了论证要害？哪些是误读、过度解读，或者把作者引来批驳的对立观点误当成了作者本人立场？请指名道姓地说，并给出理由。');
    out.push('【3. 建议】基于我的关注方向，指出下一步该读什么，以及哪几条批注有潜力发展成论文里的一个论证段落。');
    out.push('');
    out.push('文献：'+TITLE);
    if(CITE) out.push(CITE);
    out.push('批注条数：'+rows.length);
    out.push('');
    rows.forEach(function(r,i){
      out.push('════ 第 '+(i+1)+' 条'+(r.isQuote?'（针对引文）':'')+' ════');
      out.push('【原文】'+r.src.replace(/\\s+/g,' '));
      if(r.zh) out.push('【译文】'+r.zh.replace(/\\s+/g,' '));
      out.push('【我的批注】'+r.txt);
      out.push('');
    });
    return out.join('\\n');
  }

  function copyText(txt, btn, label){
    function done(ok){
      btn.textContent = ok?'✓ 已复制':'复制失败';
      setTimeout(function(){ btn.textContent=label; },1800);
    }
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(txt).then(function(){done(true);},function(){done(false);});
    } else {
      var ta=document.createElement('textarea'); ta.value=txt;
      ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select();
      var ok=false; try{ ok=document.execCommand('copy'); }catch(e){}
      document.body.removeChild(ta); done(ok);
    }
  }
  function guardEmpty(){
    if(!entries().length){ alert('还没有批注。先在段落下方写几条再来。'); return true; }
    return false;
  }

  /* ---- navigator: tab switching ---- */
  function showTab(name){
    document.querySelectorAll('.navtab').forEach(function(b){ b.classList.toggle('active', b.dataset.tab===name); });
    document.querySelectorAll('.navpane').forEach(function(p){ p.hidden = (p.dataset.pane!==name); });
    try{ localStorage.setItem('brNavTab', name); }catch(e){}
  }
  document.querySelectorAll('.navtab').forEach(function(b){
    b.addEventListener('click', function(){ showTab(b.dataset.tab); });
  });
  var backdrop=document.getElementById('navBackdrop');
  function openPanel(){ refreshAll(); panel.classList.add('open'); backdrop.classList.add('open'); }
  function closePanel(){ panel.classList.remove('open'); backdrop.classList.remove('open'); }
  /* The FAB sits under the panel once it's open (the sheet covers that corner
     of the screen), so a real tap there can never reach this button again —
     it always hits the backdrop first, which already closes on click. So this
     only ever needs to open; a toggle-to-close branch here would be dead code. */
  document.getElementById('navBtn').addEventListener('click', openPanel);
  document.getElementById('navClose').addEventListener('click', closePanel);
  backdrop.addEventListener('click', closePanel);
  document.getElementById('notesJump').addEventListener('click', function(){
    closePanel();
    document.getElementById('overview').scrollIntoView({behavior:'smooth',block:'start'});
  });

  /* ---- 目录 tab ---- */
  function buildToc(){
    var list=document.getElementById('tocList');
    var toc=window.__BR_TOC||[];
    list.innerHTML='';
    if(!toc.length){ list.innerHTML='<div class="gempty">这篇没有分节标题。</div>'; return; }
    toc.forEach(function(t){
      var b=document.createElement('button');
      b.type='button'; b.className='tocrow lvl-'+t.level;
      var en=document.createElement('span'); en.className='en'; en.textContent=t.en;
      b.appendChild(en);
      if(t.zh){ var zh=document.createElement('span'); zh.className='zh'; zh.textContent=t.zh; b.appendChild(zh); }
      b.addEventListener('click', function(){
        closePanel();
        var el=document.getElementById(t.id);
        if(el) el.scrollIntoView({behavior:'smooth',block:'start'});
      });
      list.appendChild(b);
    });
  }

  /* ---- 术语 tab ---- */
  var GLOSS_CAT_ORDER=['理论/思潮','人物','概念','政策/机构','地名'];
  function stripTags(html){
    var d=document.createElement('div'); d.innerHTML=html||''; return d.textContent||'';
  }
  function buildGlossary(filter){
    var list=document.getElementById('gList');
    var items=window.__BR_GLOSSARY||[];
    var q=(filter||'').trim().toLowerCase();
    var filtered=items.filter(function(g){
      if(!q) return true;
      var hay=(g.term+' '+stripTags(g.def)).toLowerCase();
      return hay.indexOf(q)!==-1;
    });
    list.innerHTML='';
    if(!filtered.length){ list.innerHTML='<div class="gempty">没有匹配的术语。</div>'; return; }
    var byCat={};
    filtered.forEach(function(g){ (byCat[g.cat||'其他']=byCat[g.cat||'其他']||[]).push(g); });
    var cats=Object.keys(byCat).sort(function(a,b){
      var ia=GLOSS_CAT_ORDER.indexOf(a), ib=GLOSS_CAT_ORDER.indexOf(b);
      if(ia===-1) ia=99; if(ib===-1) ib=99;
      return ia-ib;
    });
    cats.forEach(function(cat){
      var h=document.createElement('div'); h.className='gcat-header'; h.textContent=cat;
      list.appendChild(h);
      byCat[cat].forEach(function(g){
        var b=document.createElement('button');
        b.type='button'; b.className='gpick';
        var term=document.createElement('span'); term.className='term'; term.textContent=g.term;
        var def=document.createElement('span'); def.className='def'; def.textContent=stripTags(g.def);
        b.appendChild(term); b.appendChild(def);
        b.addEventListener('click', function(){
          closePanel();
          var el=document.getElementById(g.id);
          if(!el) return;
          var details=el.closest('details'); if(details) details.open=true;
          el.scrollIntoView({behavior:'smooth',block:'center'});
          el.classList.add('flash');
          setTimeout(function(){ el.classList.remove('flash'); }, 1500);
        });
        list.appendChild(b);
      });
    });
  }
  var gSearch=document.getElementById('gSearch');
  if(gSearch){ gSearch.addEventListener('input', function(){ buildGlossary(gSearch.value); }); }

  buildToc();
  buildGlossary('');
  try{ showTab(localStorage.getItem('brNavTab')||'toc'); }catch(e){ showTab('toc'); }

  document.getElementById('ovCopy').addEventListener('click', function(){
    if(guardEmpty()) return; copyText(markdown(), this, '复制为 Markdown');
  });
  document.getElementById('ovReview').addEventListener('click', function(){
    if(guardEmpty()) return; copyText(reviewPrompt(), this, '生成 AI 点评请求（复制）');
  });
  /* same actions, duplicated in the 批注 nav tab so they're reachable in two
     taps from anywhere mid-read, instead of requiring a detour through the
     end-of-document overview every time. */
  document.getElementById('navCopyMd').addEventListener('click', function(){
    if(guardEmpty()) return; copyText(markdown(), this, '复制为 Markdown');
  });
  document.getElementById('navReview').addEventListener('click', function(){
    if(guardEmpty()) return; copyText(reviewPrompt(), this, '生成 AI 点评请求（复制）');
  });
  document.getElementById('ovClear').addEventListener('click', function(){
    if(guardEmpty()) return;
    if(!confirm('清空本篇全部批注？此操作无法撤销。建议先导出备份。')) return;
    notes={}; persist();
    document.querySelectorAll('.note').forEach(paint);
    refreshAll();
  });

  /* file export — only when the downloads capability is present in this view */
  var dl = (window.claude && window.claude.downloads) ? window.claude.downloads : null;
  var slug=(window.__BR_DOC||'notes').replace(/[^a-zA-Z0-9_-]+/g,'-').slice(0,60);
  if(dl){
    ['ovSaveMd','ovSaveJson'].forEach(function(id){
      var b=document.getElementById(id); if(b) b.style.display='';
    });
    function offer(btn, label, filename, data){
      btn.disabled=true;
      dl.save({filename:filename, data:data}).then(function(){
        btn.textContent='✓ 已保存';
      }).catch(function(err){
        var c=err&&err.code;
        btn.textContent = c==='declined' ? '已取消'
                        : c==='rate_limited' ? '稍后再试'
                        : c==='too_large' ? '文件过大'
                        : '保存不可用';
        if(c==='unavailable'||c==='not_granted'||c==='capability_disabled'||c==='capability_removed'){
          btn.style.display='none';
        }
      }).then(function(){
        btn.disabled=false;
        setTimeout(function(){ if(btn.style.display!=='none') btn.textContent=label; },1800);
      });
    }
    document.getElementById('ovSaveMd').addEventListener('click', function(){
      if(guardEmpty()) return;
      offer(this,'下载 .md', slug+'-notes.md', markdown());
    });
    document.getElementById('ovSaveJson').addEventListener('click', function(){
      if(guardEmpty()) return;
      offer(this,'备份 .json', slug+'-notes.json',
            JSON.stringify({doc:window.__BR_DOC, saved:new Date().toISOString(), notes:notes}, null, 2));
    });
  }

  refreshAll();
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

    toc = []

    a("<article>")
    for i, it in enumerate(spec.get("items", [])):
        k = it.get("kind")
        en, zh = it.get("en", ""), it.get("zh", "")
        if k in ("h2", "h3"):
            sec_id = f"sec-{i}"
            toc.append({"id": sec_id, "level": k, "en": en, "zh": zh})
            a(f'<{k} id="{sec_id}"><span class="en">{esc(en)}</span><span class="zh">{esc(zh)}</span></{k}>')
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

    ai_entries = spec.get("ai_commentary", [])
    if ai_entries:
        a('<section id="aiCommentary">')
        a('<h2 class="ovh">AI 点评</h2>')
        a('<p class="ovsub">基于你贴给 Claude 的批注写成，烧进页面里存着，'
          '不是页面自己生成的——每次你发来新一批笔记，Claude 会在这里追加一条新记录，'
          '旧的保留，不覆盖。</p>')
        for e in ai_entries:
            date = esc(e.get("date", ""))
            a('<div class="aic-entry">')
            if date:
                a(f'<div class="aic-date">{date}</div>')
            a(f'<div class="aic-body">{e.get("html", "")}</div>')
            a("</div>")
        a("</section>")

    a('<section id="overview">')
    a('<h2 class="ovh">我的批注 · 总览</h2>')
    a('<p class="ovsub">下列为你在本页写下的全部批注，按出现顺序排列。点击引用的原文句可跳回该段。</p>')
    a('<div id="ovList"></div>')
    a('<div id="ovTools">'
      '<button id="ovReview" class="primary" type="button">生成 AI 点评请求（复制）</button>'
      '<button id="ovCopy" type="button">复制为 Markdown</button>'
      '<button id="ovSaveMd" type="button" style="display:none">下载 .md</button>'
      '<button id="ovSaveJson" type="button" style="display:none">备份 .json</button>'
      '<button id="ovClear" class="danger" type="button">清空</button>'
      "</div>")
    a('<div id="ovHint"><strong>关于「AI 点评」：</strong>发布页无法直接调用大模型，'
      '所以这个按钮的作用是把<strong>你的全部批注 + 对应原文 + 一份写好的点评指令</strong>'
      '打包复制到剪贴板。粘给 Claude 即可得到点评——它会做三件事：提炼你的关注主线、'
      '逐条判断哪些批注抓住了要害／哪些是误读（尤其是把作者引来批驳的观点误当成作者立场）、'
      '以及指出哪几条有潜力发展成论文段落。</div>')
    a("</section>")

    if m.get("footer"):
        a(f"<footer>{m['footer']}</footer>")
    a("</main>")

    a('<button id="navBtn" type="button">☰ 导航 <span class="n" data-zero="1">0</span></button>')
    a('<div id="navBackdrop"></div>')
    a('<div id="navPanel">')
    a('<div class="navtabs">'
      '<button class="navtab active" data-tab="toc" type="button">目录</button>'
      '<button class="navtab" data-tab="gloss" type="button">术语</button>'
      '<button class="navtab" data-tab="notes" type="button">批注 <span class="navbadge" id="notesTabBadge">0</span></button>'
      '<button id="navClose" type="button">✕</button>'
      '</div>')
    a('<div class="navbody">')
    a('<div class="navpane" data-pane="toc"><div id="tocList"></div></div>')
    a('<div class="navpane" data-pane="gloss" hidden>'
      '<input id="gSearch" type="search" placeholder="搜索术语、人物、地名…">'
      '<div id="gList"></div></div>')
    a('<div class="navpane" data-pane="notes" hidden>'
      '<div id="notesTools">'
      '<button id="navReview" class="primary" type="button">生成 AI 点评请求（复制）</button>'
      '<button id="navCopyMd" type="button">复制为 Markdown</button>'
      '</div>'
      '<p id="notesHint">点「生成 AI 点评请求」→ 粘贴进与 Claude 的对话 → 发送。'
      '页面本身无法直接调用 AI，这一步跳不过去。</p>'
      '<div id="notesList"></div>'
      '<div id="notesJumpRow"><button id="notesJump" type="button">前往总览（导出文件 / 清空）→</button></div>'
      '</div>')
    a('</div></div>')

    glossary_js = [
        {"id": g.get("id", ""), "cat": g.get("cat", ""), "term": g.get("term", ""), "def": g.get("def", "")}
        for g in gl
    ]
    a(f"<script>window.__BR_DOC={json.dumps(doc_key)};"
      f"window.__BR_TOC={json.dumps(toc, ensure_ascii=False)};"
      f"window.__BR_GLOSSARY={json.dumps(glossary_js, ensure_ascii=False)};</script>")
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
