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
  --font-zh:"PingFang SC","Microsoft YaHei","Heiti SC","Noto Sans SC","Hiragino Sans GB",sans-serif;
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

/* ---- persistent structure sidebar ----
   A real two-column layout (sidebar + main as flex siblings inside .layout),
   not a sidebar floating in whatever margin happens to be left outside a
   separately-centered main column. That old approach needed ~1440px of
   viewport just to have room on both sides; this one only needs enough width
   for sidebar + gap + article, so it shows up on an ordinary, non-maximized
   laptop window. Narrower than that, .layout stops being a flex row (falls
   back to block, sidebar hidden) and main reverts to centering itself exactly
   as it does with no sidebar at all — the floating navigator's 目录 tab is
   what covers narrow/mobile viewports. */
.layout{display:block}
@media (min-width:1040px){
  /* max-width is sized for THREE columns at once (TOC 13rem + gap 2rem +
     main's own 46rem cap + gap 2rem + notes 14.5rem = 77.5rem) rather than
     gating the notes sidebar behind a separate, higher breakpoint. Both
     sidebars use flex-shrink:0, so main (flex:1 1 auto, no shrink override)
     is what absorbs the squeeze below ~77.5rem*16px of actual viewport width
     — it just renders narrower than its 46rem ideal between 1040px and
     ~1240px, which still reads fine. Earlier this intentionally gated the
     notes sidebar at 1280px on the theory that main needed to stay near
     46rem; that was overcautious — the real floor is ~1040px, same as the
     TOC sidebar it sits next to, and gating it higher just meant it silently
     failed to appear on anyone whose window was 1040–1279px wide. */
  .layout{display:flex;align-items:flex-start;gap:2rem;max-width:77.5rem;margin:0 auto}
  main{margin:0;flex:1 1 auto;min-width:0}
}
#tocSidebar{display:none;width:13rem;flex-shrink:0;font-family:var(--font-sans)}
@media (min-width:1040px){
  #tocSidebar{display:block;position:sticky;top:5.5rem;
              max-height:calc(100vh - 7.5rem);overflow-y:auto}
}
#tocSidebar .sb-label,#noteSidebar .sb-label{font-size:.65rem;letter-spacing:.1em;text-transform:uppercase;
                       color:var(--hl);font-weight:700;margin:0 0 .9rem .3rem}
/* Tags live as an overlay LAYER on top of the TOC tree, not a swapped-out
   second pane. The left sidebar's one real destination is the TOC — that's
   what a reader reaches for most — so it gets one real button-sized label
   and the tree is never actually removed from the page; tags are a small
   switch that lays a floating panel over the tree (and back off again),
   not a second equally-weighted button implying two equally-likely
   destinations. */
.sb-toc-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin:0 0 .9rem}
.sb-toc-head .sb-label{margin:0}
.sb-layer-switch{display:flex;align-items:center;gap:.35rem;border:none;background:none;
                  cursor:pointer;font-family:var(--font-sans);color:var(--muted);padding:.1rem}
.sb-layer-switch-label{font-size:.65rem;letter-spacing:.05em;text-transform:uppercase}
.sb-layer-switch-track{width:1.7rem;height:.95rem;border-radius:999px;background:var(--line);
                        position:relative;flex-shrink:0;transition:background .15s}
.sb-layer-switch-thumb{position:absolute;top:.1rem;left:.1rem;width:.75rem;height:.75rem;
                        border-radius:50%;background:var(--paper);transition:left .15s;
                        box-shadow:0 1px 2px rgba(0,0,0,.3)}
.sb-layer-switch[aria-pressed="true"] .sb-layer-switch-track{background:var(--hl)}
.sb-layer-switch[aria-pressed="true"] .sb-layer-switch-thumb{left:.85rem}
.sb-layer-switch[aria-pressed="true"] .sb-layer-switch-label{color:var(--hl);font-weight:700}
.sb-tree-wrap{position:relative}
.sb-tag-overlay{position:absolute;inset:0;z-index:5;background:var(--paper);
                 border:1px solid var(--line);border-radius:8px;
                 box-shadow:0 8px 22px rgba(0,0,0,.14);padding:.7rem .65rem;
                 max-height:calc(100vh - 7.5rem);overflow-y:auto}
.sb-tag-overlay[hidden]{display:none}
.sb-tag-row{display:flex;align-items:center;justify-content:space-between;gap:.4rem;
            padding:.4rem .3rem;border-bottom:1px dashed var(--line);cursor:pointer;
            font-family:var(--font-sans);font-size:.78rem;color:var(--ink-soft)}
.sb-tag-row:last-child{border-bottom:none}
.sb-tag-row:hover{color:var(--accent)}
.sb-tag-row.active{color:var(--accent);font-weight:700}
.sb-tag-row .count{flex-shrink:0;font-size:.66rem;color:var(--muted);background:var(--zh-bg);
                    border-radius:999px;padding:.05rem .5rem}
.sb-tag-empty{font-family:var(--font-sans);font-size:.76rem;color:var(--muted);
              padding:1rem 0;text-align:center}
.sb-tree{position:relative;padding-left:1rem}
.sb-tree::before{content:"";position:absolute;left:.28rem;top:.4rem;bottom:.4rem;
                  width:1px;background:var(--line)}
.sb-node{position:relative;display:block;padding:.32rem .4rem .32rem .6rem;margin-bottom:.1rem;
         border-radius:4px;text-decoration:none;color:var(--muted);font-size:.78rem;line-height:1.4;
         transition:background .15s,color .15s}
.sb-node:hover{background:var(--accent-soft);color:var(--accent)}
.sb-node::before{content:"";position:absolute;left:-.72rem;top:.62rem;width:.42rem;height:.42rem;
                  border-radius:50%;background:var(--paper);border:2px solid var(--line)}
.sb-node.lvl-h2{font-weight:700;color:var(--ink-soft);margin-top:.55rem}
.sb-node.lvl-h2::before{width:.52rem;height:.52rem;left:-.77rem;border-color:var(--accent)}
.sb-node.lvl-h2:first-child{margin-top:0}
.sb-node.lvl-h3{padding-left:1.6rem;font-size:.73rem}
.sb-node.lvl-h3::before{left:-.72rem;border-color:var(--line)}
.sb-node .zh{display:block;font-size:.9em;opacity:.8;margin-top:.05rem}
.sb-node.active{background:var(--accent-soft);color:var(--accent)}
.sb-node.active::before{background:var(--accent);border-color:var(--accent)}

/* ---- persistent annotations sidebar (right column) ----
   Deliberately separate from the floating nav panel's 批注 tab: this one is
   always visible while reading (same ≥1040px breakpoint as #tocSidebar — see
   the .layout rule above for why that's wide enough for all three columns),
   and every row splits "jump to the passage" and "edit / link this note"
   into two distinct click targets, so re-reading your own annotations
   doesn't require scrolling away from wherever you currently are. */
#noteSidebar{display:none;width:14.5rem;flex-shrink:0;font-family:var(--font-sans)}
@media (min-width:1040px){
  #noteSidebar{display:block;position:sticky;top:5.5rem;
               max-height:calc(100vh - 7.5rem);overflow-y:auto}
}
.ns-row{position:relative;padding:.55rem 3.4rem .55rem .1rem;border-bottom:1px dashed var(--line)}
.ns-row:last-child{border-bottom:none}
.ns-q{font-size:.71rem;color:var(--muted);line-height:1.5;cursor:pointer;margin-bottom:.3rem}
.ns-q:hover{color:var(--accent)}
.ns-t{font-family:var(--font-zh);font-size:.78rem;line-height:1.65;color:var(--ink-soft);
      white-space:pre-wrap;word-break:break-word}
.ns-edit,.ns-ask{position:absolute;top:.5rem;width:1.5rem;height:1.5rem;border-radius:4px;
         border:1px solid var(--line);background:var(--paper);color:var(--muted);font-size:.72rem;
         line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;
         padding:0}
.ns-edit{right:0}
.ns-ask{right:1.75rem}
.ns-edit:hover,.ns-ask:hover{border-color:var(--accent);color:var(--accent)}
.ns-empty{font-family:var(--font-sans);font-size:.76rem;color:var(--muted);padding:1.2rem 0;text-align:center}
/* 「AI 解读」 is the same can't-call-an-LLM-at-runtime constraint as the
   「AI 点评」 button (see SKILL.md), just scoped to ONE annotation instead of
   the whole set: it copies that single note treated AS A QUESTION, plus
   its source passage, to the clipboard as a ready-to-paste prompt. */
.ask-ai-btn{margin-top:.4rem;font-family:var(--font-sans);font-size:.68rem;border:1px solid var(--line);
            background:none;color:var(--muted);border-radius:999px;padding:.25rem .6rem;cursor:pointer}
.ask-ai-btn:hover{border-color:var(--accent);color:var(--accent)}

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
.bipara p.zh{margin:0;font-family:var(--font-zh);font-weight:600;color:var(--ink);font-size:.94rem;
             line-height:1.9;background:var(--zh-bg);padding:.7rem .85rem;border-radius:3px}

blockquote.cited{margin:1.3rem 0 1.6rem;padding:.95rem 1.05rem;border-left:3px solid var(--hl);
                 background:var(--hl-soft);border-radius:3px}
blockquote.cited p.en{margin:0 0 .55rem;color:var(--ink-soft);font-style:italic;font-size:.93rem}
blockquote.cited p.zh{margin:0 0 .6rem;font-family:var(--font-zh);font-weight:600;color:var(--ink);
                      font-size:.92rem;line-height:1.9}
blockquote.cited .attrib{font-family:var(--font-sans);font-size:.71rem;color:var(--hl);
                         border-top:1px solid rgba(156,107,51,.28);padding-top:.45rem;
                         margin-top:.2rem;line-height:1.6;display:block}

a.gref{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent);cursor:help}
a.gref:hover{background:var(--accent-soft)}

/* ---- glossary term popover ----
   a.gref used to be a plain anchor jump to the glossary section near the
   bottom of the page — fine for a short article, disorienting on a long one:
   you lose your place and have to scroll all the way back. This intercepts
   the click and shows the definition in a floating popover right where you
   clicked instead; the glossary section itself still exists as a fallback
   (reachable from the 术语 nav tab, or the "查看完整条目" link in the popover)
   for anyone who wants the full list with category grouping. */
#grefPop{position:fixed;z-index:85;width:19rem;max-width:88vw;
         background:var(--paper);border:1px solid var(--line);border-radius:10px;
         box-shadow:0 6px 28px rgba(0,0,0,.22);padding:.85rem .95rem;
         font-family:var(--font-sans);display:none}
#grefPop .gp-cat{display:inline-block;font-size:.62rem;letter-spacing:.05em;color:var(--paper);
                 background:var(--muted);padding:.12rem .45rem;border-radius:999px;margin-bottom:.4rem}
#grefPop .gp-term{display:block;font-family:var(--font-zh);font-weight:600;color:var(--ink);
                  font-size:.95rem;margin-bottom:.4rem}
#grefPop .gp-def{font-family:var(--font-zh);font-size:.84rem;line-height:1.8;color:var(--ink-soft);
                 max-height:40vh;overflow-y:auto}
#grefPop .gp-def p{margin:0 0 .6rem}
#grefPop .gp-def p:last-child{margin-bottom:0}
#grefPop .gp-jump{display:inline-block;margin-top:.55rem;font-size:.68rem;color:var(--accent);
                  text-decoration:none;border-bottom:1px dotted var(--accent)}
@media (max-width:640px){
  #grefPop{left:.8rem;right:.8rem;width:auto;top:auto!important;bottom:.8rem}
}
@media print{#grefPop{display:none!important}}

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
.note-tags{display:none;width:100%;margin-top:.35rem;font-family:var(--font-sans);font-size:.72rem;
           color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:3px;
           padding:.35rem .55rem;box-sizing:border-box}
.note-tags:focus{outline:none;border-color:var(--accent)}
.note.editing .note-tags{display:block}
.note-status{font-family:var(--font-sans);font-size:.62rem;color:var(--accent);
             margin-top:.22rem;height:.9rem;opacity:0;transition:opacity .2s}
.note-status.show{opacity:.8}

/* ---- self-assigned tags (free-form, not a fixed taxonomy) ---- */
.tag-row,.note-tagrow{margin-top:.4rem;display:flex;flex-wrap:wrap;gap:.3rem}
.tag-chip{display:inline-block;font-family:var(--font-sans);font-size:.64rem;color:var(--accent);
          background:var(--accent-soft);border-radius:999px;padding:.1rem .5rem;cursor:pointer;
          border:1px solid transparent}
.tag-chip:hover{border-color:var(--accent)}
.tag-chip.active{background:var(--accent);color:var(--paper)}
.note-body .tag-chip{background:var(--paper);border-color:var(--accent)}
.tag-filter-bar{font-family:var(--font-sans);font-size:.7rem;color:var(--ink-soft);
                background:var(--zh-bg);border-radius:4px;padding:.4rem .6rem;margin-bottom:.6rem;
                display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
.tag-filter-clear{font-family:var(--font-sans);font-size:.68rem;border:1px solid var(--line);
                   background:none;color:var(--muted);border-radius:4px;padding:.2rem .5rem;cursor:pointer}
.tag-filter-clear:hover{border-color:var(--accent);color:var(--accent)}

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

/* a linked (多段关联) highlight note's row: a badge plus one clickable line
   per fragment, each jumping to its own passage — see renderSrcInto() */
.frag-badge{font-weight:700;color:var(--hl);margin-bottom:.35rem}
.frag-row{display:flex;align-items:flex-start;gap:.35rem;cursor:pointer;margin-bottom:.3rem;
          color:var(--muted);line-height:1.5}
.frag-row:hover{color:var(--accent)}
.frag-row:hover .jump-icon{color:var(--accent)}
.frag-row .jump-icon{flex-shrink:0;color:var(--hl);font-weight:700}
.nrow .frag-badge,.nrow .frag-row{font-family:var(--font-sans);font-size:.7rem}
.ns-row .frag-badge,.ns-row .frag-row{font-family:var(--font-sans);font-size:.7rem}

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
/* ---- selection-anchored highlight annotations ----
   A second, complementary annotation mode: select any phrase/sentence inside
   a paragraph (not just the whole block) and a small pill offers to attach a
   note to exactly that selection. The note card can also pull in a second,
   unrelated selection elsewhere in the article ("+ 关联另一段") so one note
   can discuss the relationship between two passages. Lives in its own
   localStorage key and its own DOM marks, but feeds into the same entries()/
   markdown()/reviewPrompt() used by paragraph notes, so export and the
   AI-review prompt cover both kinds without separate UI. */
#selPill{position:absolute;z-index:80;font-family:var(--font-sans);font-size:.72rem;
         background:var(--accent);color:var(--paper);border:none;border-radius:999px;
         padding:.35rem .75rem;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2)}
mark.hl-anno{background:var(--hl-soft);color:inherit;border-bottom:2px solid var(--hl);
             padding:0 .1em;cursor:pointer}
/* Only the estimated CORRESPONDING span of the sibling paragraph (same
   block, other language) gets underlined, not the whole paragraph — same
   --hl color as mark.hl-anno's own border-bottom, so it reads as "this
   corresponds to a highlight," not a separate badge/marker. A <span>, not
   <mark>: <mark> is reserved for the exact, click-to-edit match. Purely a
   visual cue, not interactive — open the note from the sidebar/nav/overview
   instead. */
span.linked-underline{
  text-decoration: underline;
  text-decoration-color: var(--hl);
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}
#hlHint{position:fixed;top:.8rem;left:50%;transform:translateX(-50%);z-index:85;
        font-family:var(--font-sans);font-size:.72rem;color:var(--paper);background:var(--hl);
        padding:.5rem .9rem;border-radius:999px;box-shadow:0 2px 10px rgba(0,0,0,.25)}
#selCard{position:fixed;z-index:85;width:19rem;max-width:90vw;right:1rem;top:4.2rem;
         background:var(--paper);border:1px solid var(--line);border-radius:10px;
         box-shadow:0 6px 28px rgba(0,0,0,.22);padding:.9rem;font-family:var(--font-sans)}
.hl-head{font-size:.7rem;color:var(--muted);margin-bottom:.5rem;font-weight:600}
#hlFrags{margin-bottom:.5rem;max-height:7rem;overflow-y:auto}
.hl-frag{font-family:var(--font-zh);font-size:.78rem;color:var(--ink-soft);
         background:var(--hl-soft);border-left:3px solid var(--hl);border-radius:3px;
         padding:.4rem .55rem;margin-bottom:.4rem;line-height:1.6}
#hlNote{width:100%;font-family:var(--font-zh);font-size:.87rem;line-height:1.75;color:var(--ink);
        background:var(--zh-bg);border:1px solid var(--line);border-radius:4px;
        padding:.5rem .65rem;resize:vertical;min-height:4.4rem;box-sizing:border-box}
#hlNote:focus{outline:none;border-color:var(--accent)}
#hlTags{width:100%;margin-top:.4rem;font-family:var(--font-sans);font-size:.78rem;color:var(--ink);
        background:var(--zh-bg);border:1px solid var(--line);border-radius:4px;
        padding:.4rem .55rem;box-sizing:border-box}
#hlTags:focus{outline:none;border-color:var(--accent)}
.hl-actions{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.6rem}
.hl-actions button{font-size:.7rem;border:1px solid var(--line);background:none;color:var(--ink-soft);
                    border-radius:6px;padding:.4rem .7rem;cursor:pointer}
.hl-actions button.primary{background:var(--accent);color:var(--paper);border-color:var(--accent)}
@media (max-width:640px){
  #selCard{left:.8rem;right:.8rem;width:auto;top:auto;bottom:.8rem}
}
@media print{#selPill,#selCard,#hlHint{display:none!important}}

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

  var HL_KEY='br-highlights:'+(window.__BR_DOC||'doc');
  var highlights=[];
  try{ highlights=JSON.parse(localStorage.getItem(HL_KEY)||'[]'); }catch(e){ highlights=[]; }
  function persistHL(){
    try{ localStorage.setItem(HL_KEY, JSON.stringify(highlights)); return true; }
    catch(e){ return false; }
  }

  function persist(){
    try{ localStorage.setItem(KEY, JSON.stringify(notes)); return true; }
    catch(e){ return false; }
  }
  /* Free-form tags, self-assigned by the reader (e.g. "可引用 待查"), not a
     fixed taxonomy. Paragraph notes predate tags and were plain strings in
     localStorage — noteOf() reads either the legacy string form or the new
     {text,tags} object form, so existing saved notes don't need migrating. */
  function parseTags(s){
    return (s||'').split(/[,，\s]+/).map(function(t){return t.trim();}).filter(Boolean);
  }
  function tagsLabel(tags){ return (tags||[]).join(' '); }
  function noteOf(id){
    var raw=notes[id];
    if(!raw) return {text:'', tags:[]};
    if(typeof raw==='string') return {text:raw, tags:[]};
    return {text:raw.text||'', tags:raw.tags||[]};
  }
  function focusSoon(el){
    el.focus();
    requestAnimationFrame(function(){ el.focus(); });
  }
  var activeTagFilter=null;
  function toggleTagFilter(tag){
    activeTagFilter=(activeTagFilter===tag)?null:tag;
    refreshAll();
  }
  function buildTagRow(tags){
    var row=document.createElement('div'); row.className='tag-row';
    tags.forEach(function(t){
      var chip=document.createElement('span'); chip.className='tag-chip';
      if(t===activeTagFilter) chip.classList.add('active');
      chip.textContent='#'+t;
      chip.addEventListener('click', function(e){ e.stopPropagation(); toggleTagFilter(t); });
      row.appendChild(chip);
    });
    return row;
  }
  function count(){
    var n=Object.keys(notes).filter(function(k){return noteOf(k).text.trim();}).length;
    n += highlights.filter(function(h){return (h.note||'').trim();}).length;
    return n;
  }
  function refreshBtn(){
    var n=count();
    var badge=document.querySelector('#navBtn .n');
    if(badge){ badge.textContent=n; badge.dataset.zero = n===0 ? '1' : '0'; }
    var tabBadge=document.getElementById('notesTabBadge');
    if(tabBadge) tabBadge.textContent=n;
  }
  function paint(wrap){
    var id=wrap.dataset.nid, nd=noteOf(id), v=nd.text.trim();
    var body=wrap.querySelector('.note-body');
    if(v){
      wrap.classList.add('has');
      body.innerHTML='<span class="lbl">我的批注</span>';
      body.appendChild(document.createTextNode(v));
      if(nd.tags.length) body.appendChild(buildTagRow(nd.tags));
    }
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
    var tagInput=wrap.querySelector('.note-tags');
    var v=ta.value.trim();
    var tags=tagInput?parseTags(tagInput.value):[];
    if(v) notes[id]={text:v, tags:tags}; else delete notes[id];
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
    var tagInput=wrap.querySelector('.note-tags');
    var nd=noteOf(wrap.dataset.nid);
    ta.value=nd.text;
    if(tagInput) tagInput.value=tagsLabel(nd.tags);
    wrap.classList.add('editing');
    focusSoon(ta);
    ta.setSelectionRange(ta.value.length, ta.value.length);
    autogrow(ta);
  }
  function autogrow(ta){ ta.style.height='auto'; ta.style.height=(ta.scrollHeight+2)+'px'; }
  function scheduleCollapseCheck(wrap){
    /* Tabbing from the note textarea to its tag-input field blurs the
       textarea, but focus is still inside the SAME note — collapsing the
       editing UI on that blur would hide the tag field before the reader
       can even reach it. Defer the check a tick so the newly-focused element
       (if it's still within this wrap) is already document.activeElement. */
    setTimeout(function(){
      if(!wrap.contains(document.activeElement)) wrap.classList.remove('editing');
    }, 0);
  }

  var nidToBlock={};
  document.querySelectorAll('.note').forEach(function(wrap){
    paint(wrap);
    var host0=wrap.closest('.bipara')||wrap.closest('blockquote');
    if(host0) nidToBlock[wrap.dataset.nid]=host0;
    wrap.querySelector('.note-add').addEventListener('click', function(){ edit(wrap); });
    wrap.querySelector('.note-body').addEventListener('click', function(){ edit(wrap); });
    var ta=wrap.querySelector('.note-edit');
    var tagInput=wrap.querySelector('.note-tags');
    ta.addEventListener('input', function(){
      autogrow(ta);
      clearTimeout(wrap.__st);
      wrap.__st=setTimeout(function(){ save(wrap); }, 500);
    });
    ta.addEventListener('blur', function(){
      clearTimeout(wrap.__st); save(wrap); scheduleCollapseCheck(wrap);
    });
    ta.addEventListener('keydown', function(e){
      if(e.key==='Escape'){ ta.blur(); }
      if(e.key==='Enter' && (e.metaKey||e.ctrlKey)){ ta.blur(); }
    });
    if(tagInput){
      tagInput.addEventListener('input', function(){
        clearTimeout(wrap.__st);
        wrap.__st=setTimeout(function(){ save(wrap); }, 500);
      });
      tagInput.addEventListener('blur', function(){
        clearTimeout(wrap.__st); save(wrap); scheduleCollapseCheck(wrap);
      });
      tagInput.addEventListener('keydown', function(e){
        if(e.key==='Escape'){ tagInput.blur(); }
        if(e.key==='Enter'){ e.preventDefault(); tagInput.blur(); }
      });
    }
  });
  var panel=document.getElementById('navPanel');

  function entries(){
    var out=[];
    document.querySelectorAll('.note').forEach(function(w){
      var nd=noteOf(w.dataset.nid);
      var v=nd.text.trim();
      if(!v) return;
      var host=w.closest('.bipara')||w.closest('blockquote');
      var en=host?host.querySelector('.en'):null;
      var zh=host?host.querySelector('.zh'):null;
      out.push({el:host, src:en?en.textContent.trim():'',
                zh:zh?zh.textContent.trim():'', txt:v,
                isQuote: !!(host&&host.tagName==='BLOCKQUOTE'), tags:nd.tags});
    });
    highlights.forEach(function(h){
      var v=(h.note||'').trim();
      if(!v || !h.frags || !h.frags.length) return;
      out.push({el:nidToBlock[h.frags[0].nid], src:h.frags.map(function(f){return f.text;}).join('" ... "'),
                zh:'', txt:v, isQuote:false, isHighlight:true, frags:h.frags, hlId:h.id, tags:h.tags||[]});
    });
    return out;
  }
  function filteredRows(){
    var rows=entries();
    if(!activeTagFilter) return rows;
    return rows.filter(function(r){ return (r.tags||[]).indexOf(activeTagFilter)!==-1; });
  }
  function filterBarInto(container){
    if(!activeTagFilter) return;
    var bar=document.createElement('div'); bar.className='tag-filter-bar';
    bar.appendChild(document.createTextNode('筛选：#'+activeTagFilter+' '));
    var clear=document.createElement('button');
    clear.type='button'; clear.className='tag-filter-clear'; clear.textContent='✕ 清除筛选';
    clear.addEventListener('click', function(){ activeTagFilter=null; refreshAll(); });
    bar.appendChild(clear);
    container.appendChild(bar);
  }
  /* Shared by buildList() (nav 批注 tab / overview) and buildSidebarList():
     a highlight note with more than one linked fragment ("+ 关联另一段")
     used to collapse into one joined-quote line that jumped only to the
     FIRST fragment — the other fragment(s) were invisible and unreachable
     from the list. Now a multi-fragment row gets a "🔗 关联 N 处" badge plus
     one small jump row per fragment, each independently clickable, so the
     list actually reflects that this note spans more than one passage. */
  function renderSrcInto(container, r, opts){
    opts=opts||{};
    var truncLen=opts.truncLen||110;
    var singleClass=opts.singleClass||'src';
    if(r.isHighlight && r.frags && r.frags.length>1){
      var badge=document.createElement('div'); badge.className='frag-badge';
      badge.textContent='🔗 关联 '+r.frags.length+' 处，点击分别跳转：';
      container.appendChild(badge);
      r.frags.forEach(function(f){
        var fr=document.createElement('div'); fr.className='frag-row';
        var icon=document.createElement('span'); icon.className='jump-icon'; icon.textContent='↳';
        fr.appendChild(icon);
        fr.appendChild(document.createTextNode('“'+fragLabel(f.text)+'”'));
        fr.addEventListener('click', function(){
          var host=nidToBlock[f.nid];
          if(host) host.scrollIntoView({behavior:'smooth',block:'center'});
          if(opts.afterJump) opts.afterJump();
        });
        container.appendChild(fr);
      });
    } else {
      var s=document.createElement('div'); s.className=singleClass;
      s.textContent=(r.isHighlight?'［选段］“':(r.isQuote?'［引文］“':'“'))+r.src.slice(0,truncLen)+(r.src.length>truncLen?'…':'')+'”';
      s.addEventListener('click', function(){
        if(r.el) r.el.scrollIntoView({behavior:'smooth',block:'center'});
        if(opts.afterJump) opts.afterJump();
      });
      container.appendChild(s);
    }
  }
  function buildList(list, closeAfterJump){
    var rows=filteredRows();
    list.innerHTML='';
    filterBarInto(list);
    if(!rows.length){
      var empty=document.createElement('div'); empty.className='nempty';
      empty.textContent=activeTagFilter?('没有标签为 "'+activeTagFilter+'" 的批注。'):'还没有批注。点击任意段落下方的「＋ 批注」开始。';
      list.appendChild(empty);
      return;
    }
    rows.forEach(function(r){
      var d=document.createElement('div'); d.className='nrow';
      renderSrcInto(d, r, {truncLen:110, singleClass:'src',
        afterJump:function(){ if(closeAfterJump) closePanel(); }});
      var t=document.createElement('div'); t.className='txt'; t.textContent=r.txt;
      d.appendChild(t);
      if(r.tags && r.tags.length) d.appendChild(buildTagRow(r.tags));
      d.appendChild(buildAskBtn(r, false));
      list.appendChild(d);
    });
  }
  function buildSidebarList(){
    var list=document.getElementById('nsList');
    if(!list) return;
    var rows=filteredRows();
    list.innerHTML='';
    filterBarInto(list);
    if(!rows.length){
      var empty=document.createElement('div'); empty.className='ns-empty';
      empty.textContent=activeTagFilter?('没有标签为 "'+activeTagFilter+'" 的批注。'):'还没有批注。选中文字，或点段落下方的「＋批注」。';
      list.appendChild(empty);
      return;
    }
    rows.forEach(function(r){
      var row=document.createElement('div'); row.className='ns-row';
      renderSrcInto(row, r, {truncLen:70, singleClass:'ns-q'});
      var t=document.createElement('div'); t.className='ns-t';
      t.textContent=r.txt.slice(0,90)+(r.txt.length>90?'…':'');
      var editBtn=document.createElement('button');
      editBtn.type='button'; editBtn.className='ns-edit'; editBtn.textContent='✎';
      if(r.isHighlight){
        editBtn.title='编辑或关联其他段落（不跳转）';
        editBtn.addEventListener('click', function(e){ e.stopPropagation(); openCardById(r.hlId); });
      } else {
        editBtn.title='前往并编辑';
        editBtn.addEventListener('click', function(e){
          e.stopPropagation();
          if(!r.el) return;
          r.el.scrollIntoView({behavior:'smooth',block:'center'});
          var w=r.el.querySelector('.note');
          if(w) setTimeout(function(){ edit(w); }, 650);
        });
      }
      row.appendChild(t);
      if(r.tags && r.tags.length) row.appendChild(buildTagRow(r.tags));
      row.appendChild(buildAskBtn(r, true));
      row.appendChild(editBtn);
      list.appendChild(row);
    });
  }
  /* Previously-used tags become pickable rather than needing to be retyped
     each time: every .note-tags / #hlTags input shares one <datalist>,
     refreshed from whatever tags already exist across both notes and
     highlights. A plain HTML5 datalist only replaces the WHOLE input value
     when a suggestion is picked, so it helps most for a field's first tag;
     typing a second tag after a space still needs typing it out. That's an
     accepted limit of using the native control instead of a custom
     multi-chip widget, not a bug. */
  function allDistinctTags(){
    var set={};
    Object.keys(notes).forEach(function(k){ noteOf(k).tags.forEach(function(t){ set[t]=true; }); });
    highlights.forEach(function(h){ (h.tags||[]).forEach(function(t){ set[t]=true; }); });
    return Object.keys(set).sort();
  }
  function refreshTagOptions(){
    var dl=document.getElementById('tagOptions');
    if(!dl) return;
    dl.innerHTML='';
    allDistinctTags().forEach(function(t){
      var opt=document.createElement('option'); opt.value=t;
      dl.appendChild(opt);
    });
  }
  function buildTagDirectory(){
    var list=document.getElementById('sbTagList');
    if(!list) return;
    var counts={};
    entries().forEach(function(r){ (r.tags||[]).forEach(function(t){ counts[t]=(counts[t]||0)+1; }); });
    var tags=Object.keys(counts).sort();
    list.innerHTML='';
    if(!tags.length){
      list.innerHTML='<div class="sb-tag-empty">还没有标签。写批注时顺手加几个吧。</div>';
      return;
    }
    tags.forEach(function(t){
      var row=document.createElement('div'); row.className='sb-tag-row';
      if(t===activeTagFilter) row.classList.add('active');
      var label=document.createElement('span'); label.textContent='#'+t;
      var count=document.createElement('span'); count.className='count'; count.textContent=counts[t];
      row.appendChild(label); row.appendChild(count);
      row.addEventListener('click', function(){ toggleTagFilter(t); });
      list.appendChild(row);
    });
  }
  function refreshAll(){
    buildList(document.getElementById('notesList'), true);
    buildList(document.getElementById('ovList'), false);
    buildSidebarList();
    buildTagDirectory();
    refreshTagOptions();
    refreshBtn();
  }

  var TITLE=document.querySelector('h1.title') ? document.querySelector('h1.title').textContent.trim() : '';
  var CITE=document.querySelector('.citation') ? document.querySelector('.citation').textContent.trim() : '';

  function markdown(){
    var rows=filteredRows();
    var out=['# 批注 — '+TITLE, '', CITE, ''];
    if(activeTagFilter){ out.push('（仅导出标签：#'+activeTagFilter+'）'); out.push(''); }
    rows.forEach(function(r){
      if(r.isHighlight && r.frags && r.frags.length>1){
        r.frags.forEach(function(f){ out.push('> '+f.text.replace(/\\s+/g,' ')); });
      } else {
        out.push('> '+r.src.replace(/\\s+/g,' '));
      }
      out.push('');
      out.push(r.txt);
      if(r.tags && r.tags.length) out.push('标签：'+r.tags.map(function(t){return '#'+t;}).join(' '));
      out.push('');
      out.push('---');
      out.push('');
    });
    return out.join('\\n');
  }

  function reviewPrompt(){
    var rows=filteredRows();
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
    if(activeTagFilter) out.push('（仅包含标签 #'+activeTagFilter+' 的批注）');
    out.push('');
    rows.forEach(function(r,i){
      var tag = r.isQuote ? '（针对引文）'
              : r.isHighlight ? (r.frags.length>1 ? '（关联 '+r.frags.length+' 段）' : '（选中片段）')
              : '';
      out.push('════ 第 '+(i+1)+' 条'+tag+' ════');
      if(r.isHighlight && r.frags && r.frags.length>1){
        r.frags.forEach(function(f,fi){ out.push('【原文片段'+(fi+1)+'】'+f.text.replace(/\\s+/g,' ')); });
      } else {
        out.push('【原文】'+r.src.replace(/\\s+/g,' '));
      }
      if(r.zh) out.push('【译文】'+r.zh.replace(/\\s+/g,' '));
      out.push('【我的批注】'+r.txt);
      if(r.tags && r.tags.length) out.push('【标签】'+r.tags.map(function(t){return '#'+t;}).join(' '));
      out.push('');
    });
    return out.join('\\n');
  }

  /* Per-note counterpart to reviewPrompt(): treats ONE annotation's text as
     a QUESTION rather than folding it into a batch review, since "what does
     this bit even mean" and "judge my whole reading" are different asks and
     a reader shouldn't have to wade through every other note to get the
     first one answered. */
  function askPrompt(r){
    var out=[];
    out.push('请把我下面这条批注当作一个问题来解读：先说明原文这段在论证什么，再针对性地回答或解读我提出的问题，不要泛泛而谈。如果我的批注本身有误读的地方，也请指出来。');
    out.push('');
    out.push('文献：'+TITLE);
    if(CITE) out.push(CITE);
    out.push('');
    if(r.isHighlight && r.frags && r.frags.length>1){
      r.frags.forEach(function(f,fi){ out.push('【原文片段'+(fi+1)+'】'+f.text.replace(/\\s+/g,' ')); });
    } else {
      out.push('【原文】'+r.src.replace(/\\s+/g,' '));
    }
    if(r.zh) out.push('【译文】'+r.zh.replace(/\\s+/g,' '));
    out.push('');
    out.push('【我的问题/批注】'+r.txt);
    if(r.tags && r.tags.length) out.push('【标签】'+r.tags.map(function(t){return '#'+t;}).join(' '));
    return out.join('\\n');
  }

  function copyText(txt, btn, label, opts){
    opts=opts||{};
    var okText=opts.okText||'✓ 已复制', failText=opts.failText||'复制失败';
    function done(ok){
      btn.textContent = ok?okText:failText;
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
  /* Shared by buildList() and buildSidebarList(): a small button per row
     that copies askPrompt(r) to the clipboard. `compact` picks the icon-only
     ns-row variant (no room there for a text label) over the pill-with-
     label variant used in the wider nav/overview rows. */
  function buildAskBtn(r, compact){
    var b=document.createElement('button');
    b.type='button';
    if(compact){
      b.className='ns-ask'; b.textContent='💬';
      b.title='生成 AI 解读请求（复制），把这条批注当问题问 AI';
    } else {
      b.className='ask-ai-btn'; b.textContent='💬 AI 解读';
      b.title='把这条批注当问题，复制一份可直接粘贴给 AI 的解读请求';
    }
    var label=b.textContent;
    b.addEventListener('click', function(e){
      e.stopPropagation();
      copyText(askPrompt(r), b, label, compact?{okText:'✓',failText:'✕'}:undefined);
    });
    return b;
  }
  function guardEmpty(){
    if(!filteredRows().length){
      alert(activeTagFilter ? ('没有标签为 "'+activeTagFilter+'" 的批注。') : '还没有批注。先在段落下方写几条再来。');
      return true;
    }
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

  /* Tags overlay the TOC tree as a layer, toggled by one small switch —
     see the .sb-toc-head CSS comment for why this isn't a second pane. */
  (function(){
    var toggle=document.getElementById('tagLayerToggle');
    var overlay=document.getElementById('sbTagOverlay');
    if(!toggle || !overlay) return;
    function setLayer(on){
      toggle.setAttribute('aria-pressed', on?'true':'false');
      overlay.hidden=!on;
      try{ localStorage.setItem('brTagLayer', on?'1':'0'); }catch(e){}
    }
    toggle.addEventListener('click', function(){
      setLayer(toggle.getAttribute('aria-pressed')!=='true');
    });
    try{ setLayer(localStorage.getItem('brTagLayer')==='1'); }catch(e){}
  })();

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
    highlights=[]; persistHL();
    document.querySelectorAll('.note').forEach(paint);
    paintHighlights();
    refreshAll();
  });

  /* file export: the Claude-artifact `downloads` capability when present
     (gives the viewer a save-location picker), falling back to a universal
     Blob + <a download> otherwise — so export keeps working when this same
     rendered HTML is served as a plain web page (e.g. from GitHub Pages),
     where window.claude doesn't exist at all. */
  function nativeDownload(filename, data){
    try{
      var blob=new Blob([data], {type:'text/plain;charset=utf-8'});
      var url=URL.createObjectURL(blob);
      var a=document.createElement('a');
      a.href=url; a.download=filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
      return true;
    }catch(e){ return false; }
  }
  var dl = (window.claude && window.claude.downloads) ? window.claude.downloads : null;
  var slug=(window.__BR_DOC||'notes').replace(/[^a-zA-Z0-9_-]+/g,'-').slice(0,60);
  ['ovSaveMd','ovSaveJson'].forEach(function(id){
    var b=document.getElementById(id); if(b) b.style.display='';
  });
  function offer(btn, label, filename, data){
    btn.disabled=true;
    function settle(ok, msg){
      btn.textContent = ok ? '✓ 已保存' : (msg||'保存不可用');
      btn.disabled=false;
      setTimeout(function(){ if(btn.style.display!=='none') btn.textContent=label; },1800);
    }
    if(dl){
      dl.save({filename:filename, data:data}).then(function(){ settle(true); }).catch(function(err){
        var c=err&&err.code;
        if(c==='unavailable'||c==='not_granted'||c==='capability_disabled'||c==='capability_removed'){
          settle(nativeDownload(filename, data));
        } else {
          settle(false, c==='declined'?'已取消':c==='rate_limited'?'稍后再试':c==='too_large'?'文件过大':'保存不可用');
        }
      });
    } else {
      settle(nativeDownload(filename, data));
    }
  }
  document.getElementById('ovSaveMd').addEventListener('click', function(){
    if(guardEmpty()) return;
    offer(this,'下载 .md', slug+'-notes.md', markdown());
  });
  document.getElementById('ovSaveJson').addEventListener('click', function(){
    if(guardEmpty()) return;
    offer(this,'备份 .json', slug+'-notes.json',
          JSON.stringify({doc:window.__BR_DOC, saved:new Date().toISOString(), notes:notes, highlights:highlights}, null, 2));
  });

  /* import: restores a previously exported "备份 .json" — the other half of
     moving between hosts (e.g. a Claude artifact -> this page served
     elsewhere), since there is no live channel between two pages' separate
     localStorage to migrate data automatically. Merges by key/id rather than
     replacing outright, so importing doesn't silently discard anything
     already written on THIS page since the backup was made. */
  var importBtn=document.getElementById('ovImport');
  var importFile=document.getElementById('ovImportFile');
  if(importBtn && importFile){
    importBtn.addEventListener('click', function(){ importFile.click(); });
    importFile.addEventListener('change', function(){
      var file=importFile.files[0];
      importFile.value='';
      if(!file) return;
      var reader=new FileReader();
      reader.onload=function(){
        var data;
        try{ data=JSON.parse(reader.result); }catch(e){
          alert('这不是有效的备份文件（JSON 解析失败）。'); return;
        }
        if(data.doc && data.doc!==window.__BR_DOC){
          if(!confirm('这份备份来自另一篇文献（'+data.doc+'），当前页面是「'+window.__BR_DOC+'」。确定仍要导入吗？')) return;
        }
        var existingCount=count();
        if(existingCount>0 && !confirm('导入会与当前已有的 '+existingCount+' 条批注合并（相同位置的批注会被备份中的版本覆盖）。确定继续吗？')) return;
        if(data.notes){ Object.keys(data.notes).forEach(function(k){ notes[k]=data.notes[k]; }); persist(); }
        if(data.highlights){
          var byId={}; highlights.forEach(function(h){ byId[h.id]=h; });
          data.highlights.forEach(function(h){ byId[h.id]=h; });
          highlights=Object.keys(byId).map(function(k){ return byId[k]; });
          persistHL();
        }
        document.querySelectorAll('.note').forEach(paint);
        paintHighlights();
        refreshAll();
        alert('导入完成。');
      };
      reader.readAsText(file);
    });
  }

  /* ---- selection-anchored highlight annotations ---- */
  var pill=document.getElementById('selPill');
  var card=document.getElementById('selCard');
  var hint=document.getElementById('hlHint');
  var pendingFrags=null;      /* set while waiting for a second selection to link */
  var pendingNoteDraft='';
  var pendingTagsDraft='';
  var editingHlId=null;
  var draftFrags=[];

  function findBlockNid(el){
    var host=el.closest('.bipara')||el.closest('blockquote.cited');
    if(!host) return null;
    var w=host.querySelector('.note');
    return w?w.dataset.nid:null;
  }
  function fragLabel(t){ return t.length>90 ? t.slice(0,90)+'…' : t; }
  function hidePill(){ pill.style.display='none'; }

  function textOffsetInAncestor(ancestor, node, offset){
    var walker=document.createTreeWalker(ancestor, NodeFilter.SHOW_TEXT, null, false);
    var total=0, n;
    while(n=walker.nextNode()){
      if(n===node) return total+offset;
      total+=n.nodeValue.length;
    }
    return total;
  }
  /* Splits plain text into sentence-sized chunks on EN/ZH sentence-ending
     punctuation (keeping trailing closing quotes/brackets with the sentence
     they close). This is a cheap heuristic — it over-splits on abbreviations
     like "e.g." and under-splits on some run-ons — but it needs no spec.json
     changes and no manual re-segmentation of existing content: it runs on
     whatever EN/ZH text is already in the page. Used to narrow the
     cross-language underline from "a fraction of the whole paragraph" down
     to "a fraction of one sentence," which is the fix for the proportional
     guess being noticeably off on longer paragraphs. */
  function sentenceRanges(text){
    var out=[], re=/[^.!?。！？…]*[.!?。！？…]+[”"'’）)]*\s*/g, m;
    while((m=re.exec(text))){
      if(!m[0].length){ re.lastIndex++; continue; }
      out.push({start:m.index, end:m.index+m[0].length});
    }
    var covered=out.length?out[out.length-1].end:0;
    if(covered<text.length) out.push({start:covered, end:text.length});
    if(!out.length) out.push({start:0, end:text.length});
    return out;
  }
  function locateInSentences(sents, globalOffset){
    for(var i=0;i<sents.length;i++){
      var s=sents[i];
      if(globalOffset<s.end || i===sents.length-1){
        var len=Math.max(1, s.end-s.start);
        return {idx:i, frac:Math.max(0, Math.min(1, (globalOffset-s.start)/len))};
      }
    }
    return {idx:0, frac:0};
  }
  function validSelection(){
    var sel=window.getSelection();
    if(!sel||sel.isCollapsed||!sel.rangeCount) return null;
    if(!sel.toString().trim()) return null;
    var range=sel.getRangeAt(0);

    /* Anchor on the paragraph the selection STARTS in, not on requiring the
       whole raw Range to live inside one <p>. p.en and p.zh sit close
       together, and a real mouse drag very easily overshoots the end of a
       wrapped line by a few pixels — enough for the browser to resolve the
       end point into the next paragraph (even the other language). Demanding
       the entire selection stay inside one element made that overshoot
       silently reject the WHOLE selection, which is what made annotating a
       paragraph look broken. */
    var startEl=range.startContainer.nodeType===1?range.startContainer:range.startContainer.parentElement;
    var pEl=startEl?startEl.closest('p.en, p.zh'):null;
    if(!pEl) return null;
    var nidv=findBlockNid(pEl);
    if(!nidv) return null;

    var clipped=range.cloneRange();
    if(!pEl.contains(clipped.endContainer)){
      try{ clipped.setEnd(pEl, pEl.childNodes.length); }catch(e){}
    }
    var text=clipped.toString().trim();
    if(!text) return null;

    /* Where this selection falls WITHIN its own paragraph. There is no real
       word/clause alignment between the EN and ZH translations of a block,
       so none of this is a guarantee — but a flat whole-paragraph fraction
       noticeably drifted on longer paragraphs, so this also locates the
       selection by SENTENCE (ssIdx/esIdx within srcSentCount sentences, via
       sentenceRanges()) plus a fraction WITHIN that sentence (ssFrac/esFrac).
       When the sibling paragraph splits into the same number of sentences,
       markLinkedRange() maps sentence-to-sentence by index instead of
       guessing over the whole paragraph — much tighter in the common case.
       startFrac/endFrac (the old whole-paragraph fraction) are kept as the
       fallback for when the sibling's sentence count doesn't match. */
    var startOffAbs=textOffsetInAncestor(pEl, clipped.startContainer, clipped.startOffset);
    var endOffAbs=textOffsetInAncestor(pEl, clipped.endContainer, clipped.endOffset);
    var fullLen=pEl.textContent.length || 1;
    var srcSents=sentenceRanges(pEl.textContent);
    var startLoc=locateInSentences(srcSents, startOffAbs);
    var endLoc=locateInSentences(srcSents, endOffAbs);

    return {text:text, lang:pEl.classList.contains('zh')?'zh':'en', nid:nidv, clippedRange:clipped,
            startFrac:startOffAbs/fullLen, endFrac:endOffAbs/fullLen,
            ssIdx:startLoc.idx, ssFrac:startLoc.frac,
            esIdx:endLoc.idx, esFrac:endLoc.frac, srcSentCount:srcSents.length};
  }
  document.addEventListener('selectionchange', function(){
    clearTimeout(window.__selT);
    window.__selT=setTimeout(function(){
      var v=validSelection();
      if(!v){ hidePill(); return; }
      var rect=v.clippedRange.getBoundingClientRect();
      if(!rect||(!rect.width&&!rect.height)){ hidePill(); return; }
      pill.style.display='block';
      var top=window.scrollY+rect.top-42;
      var left=window.scrollX+rect.left;
      var maxLeft=window.scrollX+document.documentElement.clientWidth-140;
      pill.style.top=Math.max(window.scrollY+4, top)+'px';
      pill.style.left=Math.min(Math.max(8, left), maxLeft)+'px';
      pill.__sel=v;
    }, 120);
  });
  document.addEventListener('mousedown', function(e){
    if(pill.style.display!=='none' && !pill.contains(e.target) && !card.contains(e.target)) hidePill();
  });
  pill.addEventListener('mousedown', function(e){ e.preventDefault(); });
  pill.addEventListener('click', function(){
    var v=pill.__sel;
    if(!v) return;
    hidePill();
    var frag={nid:v.nid, lang:v.lang, text:v.text, startFrac:v.startFrac, endFrac:v.endFrac,
              ssIdx:v.ssIdx, ssFrac:v.ssFrac, esIdx:v.esIdx, esFrac:v.esFrac, srcSentCount:v.srcSentCount};
    if(pendingFrags){
      pendingFrags.push(frag);
      hint.style.display='none';
      openCard(pendingFrags, editingHlId, pendingNoteDraft, pendingTagsDraft);
      pendingFrags=null;
    } else {
      openCard([frag], null);
    }
    window.getSelection().removeAllRanges();
  });

  function renderCardFrags(){
    var wrap=document.getElementById('hlFrags');
    wrap.innerHTML='';
    draftFrags.forEach(function(f){
      var d=document.createElement('div'); d.className='hl-frag';
      d.textContent='“'+fragLabel(f.text)+'”';
      wrap.appendChild(d);
    });
  }
  function closeCard(){
    card.style.display='none';
    hint.style.display='none';
    pendingFrags=null; editingHlId=null; draftFrags=[];
  }
  function openCard(frags, hlId, presetNote, presetTags){
    draftFrags=frags; editingHlId=hlId||null;
    renderCardFrags();
    var ta=document.getElementById('hlNote');
    var tagsInput=document.getElementById('hlTags');
    var existing = hlId ? highlights.filter(function(h){return h.id===hlId;})[0] : null;
    if(typeof presetNote==='string') ta.value=presetNote;
    else ta.value = existing ? (existing.note||'') : '';
    if(typeof presetTags==='string') tagsInput.value=presetTags;
    else tagsInput.value = existing ? tagsLabel(existing.tags) : '';
    document.getElementById('hlDelete').style.display = hlId ? '' : 'none';
    card.style.display='block';
    focusSoon(ta);
  }
  function openCardById(hlId){
    var h=highlights.filter(function(x){return x.id===hlId;})[0];
    if(!h) return;
    openCard(h.frags.slice(), hlId);
  }
  document.getElementById('hlLink').addEventListener('click', function(){
    pendingFrags=draftFrags.slice();
    pendingNoteDraft=document.getElementById('hlNote').value;
    pendingTagsDraft=document.getElementById('hlTags').value;
    card.style.display='none';
    hint.style.display='block';
  });
  document.getElementById('hlCancel').addEventListener('click', closeCard);
  document.getElementById('hlSave').addEventListener('click', function(){
    var txt=document.getElementById('hlNote').value.trim();
    var tags=parseTags(document.getElementById('hlTags').value);
    if(!txt){ closeCard(); return; }
    if(editingHlId){
      var h=highlights.filter(function(x){return x.id===editingHlId;})[0];
      if(h){ h.note=txt; h.frags=draftFrags; h.tags=tags; }
    } else {
      highlights.push({id:'hl'+Date.now()+Math.random().toString(36).slice(2,6),
                        frags:draftFrags, note:txt, tags:tags, ts:new Date().toISOString()});
    }
    persistHL();
    closeCard();
    paintHighlights();
    refreshAll();
  });
  document.getElementById('hlDelete').addEventListener('click', function(){
    if(!editingHlId) return;
    highlights=highlights.filter(function(x){return x.id!==editingHlId;});
    persistHL();
    closeCard();
    paintHighlights();
    refreshAll();
  });
  document.addEventListener('keydown', function(e){
    if(e.key!=='Escape') return;
    if(pendingFrags){ pendingFrags=null; hint.style.display='none'; }
    if(card.style.display==='block') closeCard();
  });

  function unwrapMarks(){
    ['mark.hl-anno', 'span.linked-underline'].forEach(function(sel){
      document.querySelectorAll(sel).forEach(function(m){
        var parent=m.parentNode;
        while(m.firstChild) parent.insertBefore(m.firstChild, m);
        parent.removeChild(m);
        parent.normalize();
      });
    });
  }
  function rangeFromGlobalOffsets(container, startOff, endOff){
    var walker=document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    var total=0, node, range=document.createRange(), started=false;
    while(node=walker.nextNode()){
      var len=node.nodeValue.length;
      if(!started && total+len>=startOff){
        range.setStart(node, Math.max(0, startOff-total));
        started=true;
      }
      if(started && total+len>=endOff){
        range.setEnd(node, Math.max(0, Math.min(len, endOff-total)));
        return range;
      }
      total+=len;
    }
    return null;
  }
  function markLinkedRange(p, f){
    /* The exact selected phrase can only be marked in the language it was
       actually selected in — there is no real word/clause alignment between
       the EN and ZH translations of a block to compute the true
       corresponding substring. Preferred approximation: if the sibling
       paragraph splits into the SAME number of sentences as the source did
       at selection time (f.srcSentCount, via sentenceRanges()), map
       sentence-to-sentence by index and apply the within-sentence fraction
       — narrows the guess from "a span of the whole paragraph" down to "a
       span of one sentence," which is what fixed the guess being visibly
       off on longer paragraphs. Falls back to the old whole-paragraph
       fraction (f.startFrac/endFrac) when the sentence counts don't match.
       Either way this is still an approximation, not a guarantee, and still
       much closer than underlining the sibling's full text, which an
       earlier version did and was explicitly rejected as wrong
       ("应该只有对应划线的那部分也有划线，而不应该是现在这样全段划上").
       Wraps the estimated span in a plain <span class="linked-underline">
       (not <mark>, which is reserved for the exact, click-to-edit match) —
       purely a visual cue, no click handler. Best-effort like
       wrapTextInNode(): if the estimated range happens to straddle an inline
       tag boundary in a way surroundContents() can't wrap, this just skips
       rather than falling back to the whole paragraph. */
    var fullLen=p.textContent.length;
    if(!fullLen) return;
    var startOff, endOff;
    if(typeof f.ssIdx==='number' && typeof f.srcSentCount==='number'){
      var sibSents=sentenceRanges(p.textContent);
      if(sibSents.length===f.srcSentCount){
        var ss=sibSents[Math.min(f.ssIdx, sibSents.length-1)];
        var es=sibSents[Math.min(f.esIdx, sibSents.length-1)];
        startOff=Math.round(ss.start+f.ssFrac*(ss.end-ss.start));
        endOff=Math.round(es.start+f.esFrac*(es.end-es.start));
      }
    }
    if(typeof startOff!=='number' || typeof endOff!=='number'){
      startOff=Math.round(f.startFrac*fullLen);
      endOff=Math.round(f.endFrac*fullLen);
    }
    startOff=Math.max(0, Math.min(fullLen, startOff));
    endOff=Math.max(startOff+1, Math.min(fullLen, endOff));
    var range=rangeFromGlobalOffsets(p, startOff, endOff);
    if(!range) return;
    var span=document.createElement('span');
    span.className='linked-underline';
    try{ range.surroundContents(span); }catch(e){ /* straddles a tag boundary; skip */ }
  }
  function wrapTextInNode(p, text, hlId){
    /* best-effort: only wraps when the selected text sits intact inside a
       single text node (not split across inline tags like a.gref). When the
       original selection crossed such a boundary the note is still saved and
       still shows up in the list/overview/export — it just won't also get an
       inline highlight. */
    var walker=document.createTreeWalker(p, NodeFilter.SHOW_TEXT, null, false);
    var node;
    while(node=walker.nextNode()){
      if(node.parentElement && node.parentElement.closest('mark.hl-anno')) continue;
      var idx=node.nodeValue.indexOf(text);
      if(idx===-1) continue;
      var range=document.createRange();
      range.setStart(node, idx);
      range.setEnd(node, idx+text.length);
      var mark=document.createElement('mark');
      mark.className='hl-anno'; mark.dataset.hlid=hlId;
      try{ range.surroundContents(mark); }catch(e){ continue; }
      mark.addEventListener('click', function(){ openCardById(hlId); });
      return true;
    }
    return false;
  }
  function paintHighlights(){
    unwrapMarks();
    highlights.forEach(function(h){
      h.frags.forEach(function(f){
        var host=nidToBlock[f.nid];
        if(!host) return;
        var p=host.querySelector(f.lang==='zh'?'p.zh':'p.en');
        if(!p) return;
        wrapTextInNode(p, f.text, h.id);
        var siblingP=host.querySelector(f.lang==='zh'?'p.en':'p.zh');
        if(siblingP && typeof f.startFrac==='number' && typeof f.endFrac==='number'){
          markLinkedRange(siblingP, f);
        }
      });
    });
  }
  paintHighlights();

  refreshAll();
})();

/* ---------------- glossary term popover (a.gref) ---------------- */
(function(){
  var pop=document.getElementById('grefPop');
  if(!pop) return;
  var byId={};
  (window.__BR_GLOSSARY||[]).forEach(function(g){ byId[g.id]=g; });

  function closePop(){ pop.style.display='none'; }
  function openPop(g, anchorEl){
    pop.innerHTML='';
    if(g.cat){ var c=document.createElement('span'); c.className='gp-cat'; c.textContent=g.cat; pop.appendChild(c); }
    var t=document.createElement('span'); t.className='gp-term'; t.textContent=g.term; pop.appendChild(t);
    var d=document.createElement('div'); d.className='gp-def'; d.innerHTML=g.def||''; pop.appendChild(d);
    var jump=document.createElement('a'); jump.className='gp-jump'; jump.href='#'+g.id;
    jump.textContent='在术语表中查看完整条目 →';
    jump.addEventListener('click', function(e){
      e.preventDefault(); closePop();
      var el=document.getElementById(g.id);
      if(!el) return;
      var details=el.closest('details'); if(details) details.open=true;
      el.scrollIntoView({behavior:'smooth',block:'center'});
      el.classList.add('flash'); setTimeout(function(){ el.classList.remove('flash'); }, 1500);
    });
    pop.appendChild(jump);

    pop.style.display='block';
    var rect=anchorEl.getBoundingClientRect();
    var popW=pop.offsetWidth||304, popH=pop.offsetHeight||160;
    var left=Math.min(Math.max(8, rect.left), window.innerWidth-popW-8);
    var top=rect.bottom+8;
    if(top+popH > window.innerHeight-8) top=Math.max(8, rect.top-popH-8);
    pop.style.left=left+'px';
    pop.style.top=top+'px';
  }
  document.addEventListener('click', function(e){
    var a=e.target.closest?e.target.closest('a.gref'):null;
    if(a){
      if(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey) return;
      e.preventDefault();
      var id=(a.getAttribute('href')||'').replace(/^#/, '');
      var g=byId[id];
      if(g) openPop(g, a);
      return;
    }
    if(!pop.contains(e.target)) closePop();
  });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') closePop(); });
})();

/* ---------------- sidebar scroll-spy ---------------- */
(function(){
  var nodes = document.querySelectorAll('#tocSidebar .sb-node');
  if(!nodes.length || !('IntersectionObserver' in window)) return;
  var byId = {};
  nodes.forEach(function(n){ byId[n.dataset.secid] = n; });
  var current = null;
  function setActive(id){
    if(id === current) return;
    if(current && byId[current]) byId[current].classList.remove('active');
    current = id;
    if(id && byId[id]) byId[id].classList.add('active');
  }
  var observer = new IntersectionObserver(function(entries){
    var visible = entries.filter(function(e){ return e.isIntersecting; });
    if(!visible.length) return;
    visible.sort(function(a,b){ return a.boundingClientRect.top - b.boundingClientRect.top; });
    setActive(visible[0].target.id);
  }, {rootMargin: '-10% 0px -70% 0px', threshold: 0});
  document.querySelectorAll('article h2[id], article h3[id]').forEach(function(h){
    observer.observe(h);
  });
})();
"""


def render(spec):
    m = spec.get("meta", {})
    out = []
    a = out.append

    # Pre-scan for section headings so the persistent sidebar (which sits
    # before <main> in the DOM) can be built before the article loop reaches
    # them. Sec-ids are purely positional (sec-{index}) and regenerated fresh
    # on every render — unlike note ids, nothing persists across renders that
    # depends on them, so it's fine that they shift if items are reordered.
    toc = [
        {"id": f"sec-{i}", "level": it["kind"], "en": it.get("en", ""), "zh": it.get("zh", "")}
        for i, it in enumerate(spec.get("items", []))
        if it.get("kind") in ("h2", "h3")
    ]

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

    a('<div class="layout">')
    if toc:
        a('<nav id="tocSidebar">')
        a('<div class="sb-toc-head"><span class="sb-label">目录</span>'
          '<button type="button" id="tagLayerToggle" class="sb-layer-switch" aria-pressed="false" '
          'title="在目录上叠加显示标签层">'
          '<span class="sb-layer-switch-track"><span class="sb-layer-switch-thumb"></span></span>'
          '<span class="sb-layer-switch-label">标签</span>'
          '</button></div>')
        a('<div class="sb-tree-wrap">')
        a('<div class="sb-tree">')
        for t in toc:
            a(f'<a class="sb-node lvl-{t["level"]}" href="#{t["id"]}" data-secid="{t["id"]}">'
              f'<span class="en">{esc(t["en"])}</span>'
              + (f'<span class="zh">{esc(t["zh"])}</span>' if t["zh"] else "")
              + "</a>")
        a("</div>")
        a('<div class="sb-tag-overlay" id="sbTagOverlay" hidden><div id="sbTagList"></div></div>')
        a("</div>")
        a("</nav>")

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
            '<input type="text" class="note-tags" list="tagOptions" placeholder="标签（可选，空格分隔，如：可引用 待查）">'
            '<button class="note-add" type="button">＋ 批注</button>'
            '<div class="note-status"></div>'
            "</div>"
        )

    a("<article>")
    for i, it in enumerate(spec.get("items", [])):
        k = it.get("kind")
        en, zh = it.get("en", ""), it.get("zh", "")
        if k in ("h2", "h3"):
            sec_id = f"sec-{i}"
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
      '<button id="ovImport" type="button">导入备份 .json</button>'
      '<input type="file" id="ovImportFile" accept="application/json" style="display:none">'
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
    a('<nav id="noteSidebar"><div class="sb-label">我的批注</div><div id="nsList"></div></nav>')
    a("</div>")  # .layout

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

    a('<div id="selPill" style="display:none">＋ 批注</div>')
    a('<div id="hlHint" style="display:none">请选中另一段文字，然后点击出现的＋按钮完成关联</div>')
    a('<div id="selCard" style="display:none">'
      '<div class="hl-head">选中内容的批注</div>'
      '<div id="hlFrags"></div>'
      '<textarea id="hlNote" placeholder="写下你的批注…（可用电脑自带的语音输入直接对着这里说）"></textarea>'
      '<input type="text" id="hlTags" list="tagOptions" placeholder="标签（可选，空格分隔，如：可引用 待查）">'
      '<div class="hl-actions">'
      '<button id="hlLink" type="button">+ 关联另一段</button>'
      '<button id="hlDelete" type="button" style="display:none">删除</button>'
      '<button id="hlCancel" type="button">取消</button>'
      '<button id="hlSave" class="primary" type="button">保存</button>'
      '</div></div>')
    a('<div id="grefPop" style="display:none"></div>')
    a('<datalist id="tagOptions"></datalist>')

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
