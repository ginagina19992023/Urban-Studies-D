#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a dual-pane comparative reading page from a LIBRARY of bilingual-
reader specs -- not a fixed pair.

Usage:
    python render_comparative_page.py spec1.json spec2.json [spec3.json ...] output.html

Takes two or more specs. The page embeds ALL of them and lets the reader pick
ANY two, independently, from a dropdown on each pane -- this matters once the
library grows past two papers, since a fixed pair baked in at build time would
mean a new static page (and a fresh, disconnected set of cross-links) for
every combination the reader wants to compare. One cross-reference annotation
("跨文献批注": select a passage on one side, select its counterpart on the
other, write one note attached to both) genuinely connects exactly two
documents, so it's stored with BOTH documents' ids on it (`{doc, nid, text}`
per side) in ONE shared library-wide list, not scoped to whichever pair
happened to be open when it was made -- switch away to a different pair and
back, and it's still there; switch to a DIFFERENT pair and only links
relevant to THAT pair show, without the irrelevant ones cluttering the list
or getting lost.

Unlike render_reading_page.py (one document, EN/ZH columns), this renders
documents side by side, each independently scrollable, so a reader can work
through two related papers in parallel. Only `h2`/`h3`/`quote`/`p` items are
rendered; this page does not let you WRITE a per-paragraph note (that's what
the full single-document reading pages are for). It DOES read-and-display,
read-only, whatever per-paragraph notes/highlights already exist in
localStorage under the same keys the full pages use (`br-notes:<doc_id>` /
`br-highlights:<doc_id>`) for whichever two documents are currently open --
but that only finds anything when this page is SAME-ORIGIN with the full
pages it's reading from (e.g. all served from the same GitHub Pages site);
opened as a standalone Claude Artifact, it's a different origin and that
lookup will always come back empty, which is a real browser limitation, not
a bug to fix here. The cross-document link feature itself has no such
dependency: it's this page's OWN state, so it works from an Artifact.
"""
import hashlib
import json
import html
import re
import sys


def nid(doc_key, en):
    """Same per-block id as render_reading_page.py's nid() -- MUST match
    exactly, since it's how this page finds the full single-document pages'
    existing notes/highlights for the same paragraph in their localStorage."""
    h = hashlib.md5((doc_key + "\x00" + re.sub(r"\s+", " ", en or "").strip()).encode("utf-8"))
    return h.hexdigest()[:10]


def esc(s):
    return html.escape(s or "", quote=False)


CSS = """
:root {
  --paper:#FAFAF8; --ink:#1a1a1a; --ink-soft:#333; --muted:#5f6b64;
  --line:#dfe3df; --accent:#2B5C6B; --accent-soft:#eef4f5;
  --hl:#9C6B33; --hl-soft:#f7efe3; --zh-bg:#f1f3f0; --danger:#a1443b;
  --font-serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif;
  --font-zh:"PingFang SC","Microsoft YaHei","Heiti SC","Noto Sans SC","Hiragino Sans GB",sans-serif;
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"PingFang SC",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#14181a; --ink:#e8ece9; --ink-soft:#d2d8d4; --muted:#9aa8a0;
    --line:#333d3a; --accent:#7EB3C0; --accent-soft:#1a2729;
    --hl:#D6A85F; --hl-soft:#2a2419; --zh-bg:#1c2220; --danger:#d98d85;
  }
}
:root[data-theme="dark"]{
  --paper:#14181a; --ink:#e8ece9; --ink-soft:#d2d8d4; --muted:#9aa8a0;
  --line:#333d3a; --accent:#7EB3C0; --accent-soft:#1a2729;
  --hl:#D6A85F; --hl-soft:#2a2419; --zh-bg:#1c2220; --danger:#d98d85;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-serif);
     line-height:1.65;-webkit-font-smoothing:antialiased;display:flex;flex-direction:column;
     overflow:hidden}

.topbar{flex:0 0 auto;border-bottom:1px solid var(--line);padding:.6rem 1rem;
        display:flex;align-items:center;gap:1rem;font-family:var(--font-sans)}
.topbar h1{font-size:.95rem;font-weight:700;margin:0;flex:1;min-width:0}
.topbar .sub{font-size:.7rem;color:var(--muted);font-weight:400;display:block;margin-top:.1rem}
.modes{display:flex;gap:.3rem;flex-shrink:0}
.modes button{font-family:var(--font-sans);font-size:.7rem;border:1px solid var(--line);
              background:transparent;color:var(--muted);padding:.35rem .65rem;border-radius:999px;
              cursor:pointer}
.modes button.active{background:var(--accent);color:var(--paper);border-color:var(--accent)}
.xrefCountBtn{font-family:var(--font-sans);font-size:.72rem;border:1px solid var(--accent);
              background:var(--accent-soft);color:var(--accent);padding:.4rem .8rem;
              border-radius:999px;cursor:pointer;flex-shrink:0;white-space:nowrap}
#ownNoteBanner{font-family:var(--font-sans);font-size:.68rem;color:var(--muted);
               padding:.3rem .9rem;border-bottom:1px solid var(--line)}

.panes{flex:1 1 auto;display:flex;min-height:0}
@media (max-width:860px){ .panes{flex-direction:column} }
.pane{flex:1 1 0;min-width:0;display:flex;flex-direction:column;min-height:0}
.pane + .pane{border-left:1px solid var(--line)}
@media (max-width:860px){ .pane + .pane{border-left:none;border-top:1px solid var(--line)} }
.pane-head{flex:0 0 auto;padding:.7rem 1rem .5rem;border-bottom:1px solid var(--line);
           background:var(--accent-soft)}
.pane-head .t-en{display:block;font-family:var(--font-sans);font-weight:700;font-size:.82rem;color:var(--ink);
                  margin-top:.4rem}
.pane-head .t-zh{display:block;font-family:var(--font-zh);font-size:.74rem;color:var(--muted);margin-top:.15rem}
.pane-head select{width:100%;font-family:var(--font-sans);font-size:.72rem;
                   padding:.3rem .4rem;border-radius:5px;border:1px solid var(--line);
                   background:var(--paper);color:var(--ink-soft)}
.pane-head select.jumpSelect{margin-top:.4rem}
.pane-head select.paneDocSelect{font-weight:700;color:var(--accent);border-color:var(--accent)}
.pane-scroll{flex:1 1 auto;overflow-y:auto;padding:1.1rem 1.2rem 4rem}

h2.sec,h3.sec{font-family:var(--font-sans);font-weight:700;color:var(--ink-soft);margin:1.6rem 0 .6rem}
h2.sec{font-size:1rem}
h3.sec{font-size:.88rem;padding-left:.8rem}
h2.sec:first-child,h3.sec:first-child{margin-top:0}
h2.sec .zh,h3.sec .zh{display:block;font-family:var(--font-zh);font-weight:500;color:var(--muted);
                       font-size:.85em;margin-top:.1rem}

.para{margin:0 0 1.1rem;position:relative}
.para.quote{border-left:3px solid var(--hl);background:var(--hl-soft);padding:.6rem .8rem;border-radius:4px}
.para p{margin:0}
.para p.en{font-size:.95rem}
.para p.zh{font-family:var(--font-zh);color:var(--ink-soft);font-size:.86rem;margin-top:.35rem}
.para .attrib{display:block;font-family:var(--font-sans);font-size:.68rem;color:var(--muted);margin-top:.35rem}
.own-note{margin-top:.5rem;padding:.45rem .6rem;border-radius:5px;background:var(--accent-soft);
          font-family:var(--font-sans);font-size:.72rem;color:var(--ink-soft);line-height:1.6}
.own-note .lbl{display:block;font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;
               color:var(--accent);margin-bottom:.2rem;font-weight:700}
.own-note + .own-note{margin-top:.3rem}
body[data-mode="en-only"] .para p.zh{display:none}
body[data-mode="zh-only"] .para p.en{display:none}

mark.xref{background:var(--hl-soft);color:inherit;border-bottom:2px solid var(--hl);
          cursor:pointer;padding:0 .05rem;border-radius:2px}
mark.xref.flash{background:var(--hl);color:var(--paper)}

#selPill{position:absolute;z-index:60;font-family:var(--font-sans);font-size:.72rem;
         background:var(--accent);color:var(--paper);padding:.35rem .7rem;border-radius:999px;
         cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25)}
#xrefHint{position:fixed;left:50%;bottom:1rem;transform:translateX(-50%);z-index:70;
          font-family:var(--font-sans);font-size:.78rem;background:var(--ink);color:var(--paper);
          padding:.6rem 1rem;border-radius:999px;box-shadow:0 6px 18px rgba(0,0,0,.3);
          display:flex;align-items:center;gap:.7rem}
#xrefHint button{font-family:var(--font-sans);font-size:.7rem;background:rgba(255,255,255,.15);
                  color:var(--paper);border:none;border-radius:999px;padding:.3rem .6rem;cursor:pointer}

#xrefCard{position:fixed;z-index:80;left:50%;top:50%;transform:translate(-50%,-50%);
          width:min(34rem,92vw);max-height:80vh;overflow-y:auto;background:var(--paper);
          border:1px solid var(--line);border-radius:10px;box-shadow:0 20px 50px rgba(0,0,0,.35);
          padding:1.1rem 1.2rem;font-family:var(--font-sans)}
#xrefCard .hl-head{font-size:.75rem;font-weight:700;color:var(--hl);text-transform:uppercase;
                    letter-spacing:.06em;margin-bottom:.7rem}
#xrefCard .xq{font-size:.82rem;color:var(--ink-soft);background:var(--zh-bg);border-radius:6px;
              padding:.55rem .7rem;margin-bottom:.5rem;font-family:var(--font-serif);line-height:1.5}
#xrefCard .xq .side-lbl{display:block;font-family:var(--font-sans);font-size:.62rem;
                         text-transform:uppercase;letter-spacing:.06em;color:var(--accent);margin-bottom:.25rem}
#xrefCard textarea{width:100%;min-height:5rem;margin-top:.3rem;font-family:var(--font-sans);
                    font-size:.82rem;padding:.5rem .6rem;border-radius:6px;border:1px solid var(--line);
                    background:var(--paper);color:var(--ink);resize:vertical}
#xrefCard textarea:focus{outline:none;border-color:var(--accent)}
#xrefCard .actions{display:flex;justify-content:flex-end;gap:.5rem;margin-top:.8rem}
#xrefCard button{font-family:var(--font-sans);font-size:.78rem;border:1px solid var(--line);
                  background:transparent;color:var(--ink-soft);padding:.4rem .9rem;border-radius:6px;
                  cursor:pointer}
#xrefCard button.primary{background:var(--accent);color:var(--paper);border-color:var(--accent)}
#xrefCard button.danger{color:var(--danger);border-color:var(--danger)}
#xrefBackdrop{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:75;display:none}
#xrefBackdrop.open{display:block}

#xrefPanel{position:fixed;z-index:65;right:0;top:0;bottom:0;width:min(24rem,88vw);
           background:var(--paper);border-left:1px solid var(--line);box-shadow:-8px 0 24px rgba(0,0,0,.2);
           transform:translateX(100%);transition:transform .2s;display:flex;flex-direction:column;
           font-family:var(--font-sans)}
#xrefPanel.open{transform:translateX(0)}
#xrefPanel .ph{flex:0 0 auto;padding:.9rem 1rem;border-bottom:1px solid var(--line);
               display:flex;align-items:center;justify-content:space-between}
#xrefPanel .ph b{font-size:.85rem}
#xrefPanel .ph button{border:none;background:none;font-size:1.1rem;cursor:pointer;color:var(--muted)}
#xrefList{flex:1 1 auto;overflow-y:auto;padding:.6rem .8rem}
.xrow{border:1px solid var(--line);border-radius:8px;padding:.6rem .7rem;margin-bottom:.6rem;cursor:pointer}
.xrow:hover{border-color:var(--accent)}
.xrow .xq{font-size:.74rem;color:var(--muted);margin-bottom:.3rem}
.xrow .xq b{color:var(--ink-soft);font-weight:600}
.xrow .xnote{font-size:.8rem;color:var(--ink);white-space:pre-wrap}
.xempty{font-size:.8rem;color:var(--muted);text-align:center;padding:2rem 1rem}
#xrefTools{flex:0 0 auto;padding:.7rem .9rem;border-top:1px solid var(--line);display:flex;
           flex-wrap:wrap;gap:.4rem}
#xrefTools button{font-family:var(--font-sans);font-size:.72rem;border:1px solid var(--line);
                   background:transparent;color:var(--ink-soft);padding:.4rem .6rem;border-radius:6px;
                   cursor:pointer;flex:1 1 auto}
"""

JS = r"""
(function(){
  var CR_DOCS=window.__CR_DOCS, DOC_ORDER=window.__CR_DOC_ORDER;

  var modeBtns=document.querySelectorAll('.modes button');
  function setMode(m){
    document.body.dataset.mode=m;
    modeBtns.forEach(function(b){ b.classList.toggle('active', b.dataset.mode===m); });
    try{ localStorage.setItem('crMode', m); }catch(e){}
  }
  modeBtns.forEach(function(b){ b.addEventListener('click', function(){ setMode(b.dataset.mode); }); });
  var savedMode='bilingual';
  try{ savedMode=localStorage.getItem('crMode')||'bilingual'; }catch(e){}
  setMode(savedMode);

  /* jump-to-heading selects are rebuilt every time a pane's document
     changes, so this is delegated rather than bound once at load. */
  document.addEventListener('change', function(e){
    if(!e.target.classList.contains('jumpSelect')) return;
    var sel=e.target;
    if(!sel.value) return;
    var el=document.getElementById(sel.value);
    if(el) el.scrollIntoView({behavior:'smooth', block:'start'});
    sel.value='';
  });

  function escHtml(s){ var d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }
  function truncate(s,n){ return s.length>n ? s.slice(0,n)+'…' : s; }
  function docLabel(id){ return CR_DOCS[id] ? CR_DOCS[id].meta.crumb : id; }

  /* ---- shared, library-wide cross-reference link store ----
     ONE key for the whole library, not one per pair: a link genuinely
     connects two SPECIFIC documents (recorded on the link itself as
     {doc,nid,text} per side), so it stays valid and findable no matter
     which pair happens to be open when you look for it again. */
  var KEY='br-crossrefs:library';
  var links=[];
  try{ links=JSON.parse(localStorage.getItem(KEY)||'[]'); }catch(e){ links=[]; }
  function persist(){ try{ localStorage.setItem(KEY, JSON.stringify(links)); }catch(e){} }

  var currentDoc={A:null, B:null};
  function relevantLinks(){
    var pair=[currentDoc.A, currentDoc.B];
    return links.filter(function(l){
      return pair.indexOf(l.a.doc)!==-1 && pair.indexOf(l.b.doc)!==-1;
    });
  }

  function paneOf(pid){ return pid.charAt(0); }
  function paraElForSide(side){
    return document.querySelector('.para[data-doc="'+side.doc+'"][data-nid="'+side.nid+'"] p.en');
  }

  function unwrapXrefs(){
    document.querySelectorAll('mark.xref').forEach(function(m){
      var parent=m.parentNode;
      while(m.firstChild) parent.insertBefore(m.firstChild, m);
      parent.removeChild(m);
      parent.normalize();
    });
  }
  function wrapText(pEl, text, linkId){
    if(!pEl || !text) return false;
    var walker=document.createTreeWalker(pEl, NodeFilter.SHOW_TEXT, null, false);
    var node;
    while(node=walker.nextNode()){
      if(node.parentElement && node.parentElement.closest('mark.xref')) continue;
      var idx=node.nodeValue.indexOf(text);
      if(idx===-1) continue;
      var range=document.createRange();
      range.setStart(node, idx); range.setEnd(node, idx+text.length);
      var mark=document.createElement('mark');
      mark.className='xref'; mark.dataset.xrefId=linkId;
      try{ range.surroundContents(mark); }catch(e){ continue; }
      mark.addEventListener('click', function(){ openLinkCard(linkId); });
      return true;
    }
    return false;
  }
  function paintLinks(){
    unwrapXrefs();
    relevantLinks().forEach(function(l){
      wrapText(paraElForSide(l.a), l.a.text, l.id);
      wrapText(paraElForSide(l.b), l.b.text, l.id);
    });
  }

  function flashLink(id){
    document.querySelectorAll('mark.xref[data-xref-id="'+id+'"]').forEach(function(m){
      m.classList.add('flash');
      setTimeout(function(){ m.classList.remove('flash'); }, 1200);
    });
  }
  function jumpToLink(l){
    [l.a, l.b].forEach(function(side){
      var el=paraElForSide(side);
      if(el) el.closest('.para').scrollIntoView({behavior:'smooth', block:'center'});
    });
    setTimeout(function(){ flashLink(l.id); }, 350);
  }

  /* ---- selection -> pill -> second selection -> note card ---- */
  var pill=document.getElementById('selPill');
  var hint=document.getElementById('xrefHint');
  var hintText=document.getElementById('xrefHintText');
  var hintCancel=document.getElementById('xrefHintCancel');
  var pendingSel=null;   /* {pane,pid,doc,nid,text} currently under the pill */
  var draftSide=null;    /* the FIRST side already committed by clicking the pill */

  function hidePill(){ pill.style.display='none'; pendingSel=null; }
  function clearDraft(){ draftSide=null; hint.style.display='none'; hidePill(); }
  hintCancel.addEventListener('click', clearDraft);
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') clearDraft(); });

  function currentSelectionInfo(){
    var sel=window.getSelection();
    if(!sel || sel.isCollapsed) return null;
    var text=sel.toString().trim();
    if(!text) return null;
    var range=sel.getRangeAt(0);
    var container=range.commonAncestorContainer;
    var elc=container.nodeType===3?container.parentElement:container;
    var pWrap=elc.closest('.para');
    var pEn=elc.closest('p.en');
    if(!pWrap || !pEn) return null;   /* only EN text is linkable (ZH may carry inline markup) */
    return {pane:paneOf(pWrap.dataset.pid), pid:pWrap.dataset.pid,
             doc:pWrap.dataset.doc, nid:pWrap.dataset.nid, text:text, range:range};
  }
  document.addEventListener('selectionchange', function(){
    clearTimeout(window.__crSelT);
    window.__crSelT=setTimeout(function(){
      var info=currentSelectionInfo();
      if(!info){ hidePill(); return; }
      var r=info.range.getBoundingClientRect();
      if(!r || (!r.width && !r.height)){ hidePill(); return; }
      pendingSel=info;
      pill.style.left=Math.max(8, r.left+window.scrollX)+'px';
      pill.style.top=Math.max(8, r.top+window.scrollY-34)+'px';
      pill.style.display='block';
    }, 120);
  });
  document.addEventListener('mousedown', function(e){
    if(pill.style.display!=='none' && !pill.contains(e.target) && !card.contains(e.target)) hidePill();
  });
  pill.addEventListener('mousedown', function(e){ e.preventDefault(); });
  pill.addEventListener('click', function(){
    if(!pendingSel) return;
    if(!draftSide){
      draftSide=pendingSel;
      hidePill();
      window.getSelection().removeAllRanges();
      hintText.textContent='已选中'+(draftSide.pane==='A'?'左侧':'右侧')+'文字。请在'+
        (draftSide.pane==='A'?'右侧':'左侧')+'选中对应段落以完成关联（Esc 取消）。';
      hint.style.display='flex';
    } else {
      if(pendingSel.pane===draftSide.pane){
        alert('请在另一侧选中对应段落，而不是同一侧。');
        return;
      }
      var a = draftSide.pane==='A' ? draftSide : pendingSel;
      var b = draftSide.pane==='A' ? pendingSel : draftSide;
      hidePill();
      window.getSelection().removeAllRanges();
      hint.style.display='none';
      draftSide=null;
      openNoteCard({a:{doc:a.doc, nid:a.nid, text:a.text}, b:{doc:b.doc, nid:b.nid, text:b.text}}, null);
    }
  });

  /* ---- note card (create or edit) ---- */
  var card=document.getElementById('xrefCard');
  var backdrop=document.getElementById('xrefBackdrop');
  var cardA=document.getElementById('xrefCardA');
  var cardB=document.getElementById('xrefCardB');
  var cardNote=document.getElementById('xrefCardNote');
  var cardSave=document.getElementById('xrefCardSave');
  var cardDelete=document.getElementById('xrefCardDelete');
  var cardCancel=document.getElementById('xrefCardCancel');
  var editingId=null, draftPair=null;

  function closeCard(){ card.style.display='none'; backdrop.classList.remove('open'); editingId=null; draftPair=null; }
  function openNoteCard(pair, existingId){
    /* Opening ANY card (new link or editing an existing one) abandons a
       half-started link: without this, clicking an unrelated existing mark
       while "已选中左侧文字，请在右侧选中..." is still showing left the hint
       and the stale pending selection sitting there after the card closed,
       confusing about what state the UI was actually in. */
    draftSide=null; hint.style.display='none'; hidePill();
    editingId=existingId;
    draftPair=pair;
    cardA.querySelector('.side-lbl').textContent=docLabel(pair.a.doc);
    cardB.querySelector('.side-lbl').textContent=docLabel(pair.b.doc);
    cardA.querySelector('.q').textContent='“'+pair.a.text+'”';
    cardB.querySelector('.q').textContent='“'+pair.b.text+'”';
    var existing=existingId?links.find(function(l){return l.id===existingId;}):null;
    cardNote.value=existing?existing.note:'';
    cardDelete.style.display=existingId?'':'none';
    card.style.display='block'; backdrop.classList.add('open');
    setTimeout(function(){ cardNote.focus(); }, 30);
  }
  function openLinkCard(id){
    var l=links.find(function(x){return x.id===id;});
    if(!l) return;
    openNoteCard({a:l.a, b:l.b}, id);
  }
  window.__openLinkCard=openLinkCard;
  backdrop.addEventListener('click', closeCard);
  cardCancel.addEventListener('click', closeCard);
  cardSave.addEventListener('click', function(){
    var text=cardNote.value.trim();
    if(!text){ alert('写点什么再保存吧。'); return; }
    if(editingId){
      var l=links.find(function(x){return x.id===editingId;});
      if(l) l.note=text;
    } else {
      links.push({id:'x'+Date.now().toString(36)+Math.random().toString(36).slice(2,6),
                  a:draftPair.a, b:draftPair.b, note:text, ts:new Date().toISOString()});
    }
    persist(); paintLinks(); refreshPanel(); closeCard();
  });
  cardDelete.addEventListener('click', function(){
    if(!confirm('删除这条跨文献批注？')) return;
    links=links.filter(function(x){return x.id!==editingId;});
    persist(); paintLinks(); refreshPanel(); closeCard();
  });

  /* ---- side list panel (scoped to whichever pair is CURRENTLY open) ---- */
  var panel=document.getElementById('xrefPanel');
  var list=document.getElementById('xrefList');
  var openBtn=document.getElementById('xrefOpenBtn');
  var closeBtn=document.getElementById('xrefCloseBtn');
  function refreshPanel(){
    var rel=relevantLinks();
    openBtn.textContent='跨文献批注 ('+rel.length+')';
    list.innerHTML='';
    if(!rel.length){
      list.innerHTML='<div class="xempty">这两篇之间还没有跨文献批注。在左右两侧各选一段对应的文字，点出现的「+ 关联」即可建立一条。</div>';
      return;
    }
    rel.forEach(function(l){
      var row=document.createElement('div'); row.className='xrow';
      var qa=document.createElement('div'); qa.className='xq';
      qa.innerHTML='<b>'+escHtml(docLabel(l.a.doc))+'</b> “'+escHtml(truncate(l.a.text,60))+'”';
      var qb=document.createElement('div'); qb.className='xq';
      qb.innerHTML='<b>'+escHtml(docLabel(l.b.doc))+'</b> “'+escHtml(truncate(l.b.text,60))+'”';
      var note=document.createElement('div'); note.className='xnote'; note.textContent=l.note;
      row.appendChild(qa); row.appendChild(qb); row.appendChild(note);
      row.addEventListener('click', function(){ jumpToLink(l); });
      list.appendChild(row);
    });
  }
  openBtn.addEventListener('click', function(){ panel.classList.add('open'); });
  closeBtn.addEventListener('click', function(){ panel.classList.remove('open'); });

  /* ---- export / backup / import (same pattern as the single-paper pages).
     Export/clear act on the CURRENTLY OPEN PAIR only; import merges into the
     full shared library store by id regardless of which pair is open, so a
     backup can carry links spanning the whole library, not just one pair. */
  function markdown(){
    var rel=relevantLinks();
    var out=['# 跨文献批注 — '+docLabel(currentDoc.A)+' × '+docLabel(currentDoc.B), ''];
    rel.forEach(function(l,i){
      out.push('════ 第 '+(i+1)+' 条 ════');
      out.push('【'+docLabel(l.a.doc)+'】'+l.a.text);
      out.push('【'+docLabel(l.b.doc)+'】'+l.b.text);
      out.push('【批注】'+l.note);
      out.push('');
    });
    return out.join('\n');
  }
  function nativeDownload(filename, data){
    try{
      var blob=new Blob([data], {type:'text/plain;charset=utf-8'});
      var url=URL.createObjectURL(blob);
      var a=document.createElement('a'); a.href=url; a.download=filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
      return true;
    }catch(e){ return false; }
  }
  var dl=(window.claude && window.claude.downloads) ? window.claude.downloads : null;
  function offer(filename, data){
    if(dl){ dl.save({filename:filename, data:data}).catch(function(){ nativeDownload(filename, data); }); }
    else { nativeDownload(filename, data); }
  }
  document.getElementById('xrefExportMd').addEventListener('click', function(){
    if(!relevantLinks().length){ alert('这两篇之间还没有跨文献批注。'); return; }
    offer('cross-reference-notes.md', markdown());
  });
  document.getElementById('xrefExportJson').addEventListener('click', function(){
    var rel=relevantLinks();
    if(!rel.length){ alert('这两篇之间还没有跨文献批注。'); return; }
    offer('cross-reference-backup.json',
          JSON.stringify({pair:[currentDoc.A,currentDoc.B], saved:new Date().toISOString(), links:rel}, null, 2));
  });
  var importFile=document.getElementById('xrefImportFile');
  document.getElementById('xrefImportBtn').addEventListener('click', function(){ importFile.click(); });
  importFile.addEventListener('change', function(){
    var file=importFile.files[0]; importFile.value='';
    if(!file) return;
    var reader=new FileReader();
    reader.onload=function(){
      var data;
      try{ data=JSON.parse(reader.result); }catch(e){ alert('这不是有效的备份文件（JSON 解析失败）。'); return; }
      if(!Array.isArray(data.links)){ alert('备份文件里没有找到批注数据。'); return; }
      var byId={}; links.forEach(function(l){ byId[l.id]=l; });
      data.links.forEach(function(l){ byId[l.id]=l; });
      links=Object.keys(byId).map(function(k){ return byId[k]; });
      persist(); paintLinks(); refreshPanel();
      alert('导入完成，库里现有 '+links.length+' 条跨文献批注（含所有文献对）。');
    };
    reader.readAsText(file);
  });
  document.getElementById('xrefClear').addEventListener('click', function(){
    var rel=relevantLinks();
    if(!rel.length) return;
    if(!confirm('清空「'+docLabel(currentDoc.A)+'」和「'+docLabel(currentDoc.B)+'」之间的跨文献批注（共 '+rel.length+' 条）？'
      +'此操作无法撤销，建议先导出备份。其他文献对之间的批注不受影响。')) return;
    var relIds={}; rel.forEach(function(l){ relIds[l.id]=true; });
    links=links.filter(function(l){ return !relIds[l.id]; });
    persist(); paintLinks(); refreshPanel();
  });

  /* ---- read-only display of each OPEN side's OWN per-paragraph
     notes/highlights (from the full single-document reading pages) ----
     Only finds anything when this page is same-origin with those pages
     (e.g. all served from the same GitHub Pages site) -- localStorage is
     per-origin, so opened as a standalone Artifact this simply finds
     nothing, which is expected, not a bug. Read-only: editing a paragraph's
     own note/highlight is still the single-document page's job. */
  function parseNoteVal(raw){
    if(!raw) return '';
    if(typeof raw==='string') return raw;
    return raw.text||'';
  }
  function loadOwnAnnotations(docId){
    var byNid={};
    try{
      var notes=JSON.parse(localStorage.getItem('br-notes:'+docId)||'{}');
      Object.keys(notes).forEach(function(k){
        var v=parseNoteVal(notes[k]).trim();
        if(v) (byNid[k]=byNid[k]||[]).push(v);
      });
    }catch(e){}
    try{
      var hls=JSON.parse(localStorage.getItem('br-highlights:'+docId)||'[]');
      hls.forEach(function(h){
        var v=(h.note||'').trim();
        if(!v || !h.frags || !h.frags.length) return;
        (byNid[h.frags[0].nid]=byNid[h.frags[0].nid]||[]).push(v);
      });
    }catch(e){}
    return byNid;
  }
  function paintOwnAnnotations(){
    var total=0;
    ['A','B'].forEach(function(side){
      var docId=currentDoc[side];
      if(!docId) return;
      var byNid=loadOwnAnnotations(docId);
      document.querySelectorAll('.pane[data-side="'+side+'"] .para[data-nid]').forEach(function(para){
        para.querySelectorAll('.own-note').forEach(function(n){ n.remove(); });
        var texts=byNid[para.dataset.nid];
        if(!texts) return;
        total+=texts.length;
        texts.forEach(function(t){
          var box=document.createElement('div'); box.className='own-note';
          var lbl=document.createElement('span'); lbl.className='lbl'; lbl.textContent='已有批注';
          box.appendChild(lbl);
          box.appendChild(document.createTextNode(t));
          para.appendChild(box);
        });
      });
    });
    document.getElementById('ownNoteBanner').style.display = total ? 'none' : '';
    return total;
  }

  /* ---- paper picker: pick ANY two documents from the library ---- */
  function renderPane(side, docId){
    var doc=CR_DOCS[docId];
    var paneEl=document.querySelector('.pane[data-side="'+side+'"]');
    paneEl.querySelector('.t-en').textContent=doc.meta.title_en;
    var zhEl=paneEl.querySelector('.t-zh');
    zhEl.textContent=doc.meta.title_zh||'';
    zhEl.style.display=doc.meta.title_zh?'':'none';
    paneEl.querySelector('.pane-scroll').innerHTML=doc.html;
    paneEl.querySelectorAll('.sec[data-secidx]').forEach(function(h){ h.id=side+'sec-'+h.dataset.secidx; });
    paneEl.querySelectorAll('.para[data-idx]').forEach(function(p){ p.dataset.pid=side+p.dataset.idx; });
    var jsel=paneEl.querySelector('.jumpSelect');
    var opts=['<option value="">跳转到…</option>'];
    doc.toc.forEach(function(t){
      var indent=t.level==='h3'?'　':'';
      opts.push('<option value="'+side+'sec-'+t.idx+'">'+indent+escHtml(t.en)+'</option>');
    });
    jsel.innerHTML=opts.join('');
    currentDoc[side]=docId;
    var topSub=document.querySelector('.topbar .sub');
    if(currentDoc.A && currentDoc.B){
      topSub.textContent=docLabel(currentDoc.A)+' × '+docLabel(currentDoc.B)
        +' · 文献库共 '+DOC_ORDER.length+' 篇';
    }
    try{ if(currentDoc.A && currentDoc.B) localStorage.setItem('crLastPair', currentDoc.A+','+currentDoc.B); }catch(e){}
    paintLinks();
    paintOwnAnnotations();
    refreshPanel();
  }
  window.__crRenderPane=renderPane; /* exposed for tests */

  document.querySelectorAll('.paneDocSelect').forEach(function(sel){
    var side=sel.dataset.side;
    sel.innerHTML=DOC_ORDER.map(function(id){
      return '<option value="'+id+'">'+escHtml(CR_DOCS[id].meta.crumb)+'</option>';
    }).join('');
    sel.addEventListener('change', function(){ renderPane(side, sel.value); });
  });

  var savedPair=[];
  try{ savedPair=(localStorage.getItem('crLastPair')||'').split(','); }catch(e){}
  var initA = (savedPair[0] && CR_DOCS[savedPair[0]]) ? savedPair[0] : DOC_ORDER[0];
  var initB;
  if(savedPair[1] && CR_DOCS[savedPair[1]] && savedPair[1]!==initA){
    initB=savedPair[1];
  } else {
    initB = (DOC_ORDER[1] && DOC_ORDER[1]!==initA) ? DOC_ORDER[1] : DOC_ORDER[0];
  }
  document.querySelector('.paneDocSelect[data-side="A"]').value=initA;
  document.querySelector('.paneDocSelect[data-side="B"]').value=initB;
  renderPane('A', initA);
  renderPane('B', initB);
})();
"""


def render_doc_chunk(spec, doc_id):
    """Returns (html_chunk, toc) for ONE document. `doc_id`/`nid` are baked
    in statically (they're properties of the content, not of whichever pane
    happens to display it); positional ids (`data-idx`, heading `id`) are
    NOT baked in here -- they're assigned by JS at render time, prefixed
    with whichever pane ('A'/'B') the reader currently has this document
    open in, since the same chunk can end up in either pane."""
    out = []
    a = out.append
    toc = []
    for i, it in enumerate(spec.get("items", [])):
        k = it.get("kind")
        en, zh = it.get("en", ""), it.get("zh", "")
        if k in ("h2", "h3"):
            a(f'<{k} class="sec" data-secidx="{i}"><span class="en">{esc(en)}</span>'
              f'<span class="zh">{esc(zh)}</span></{k}>')
            toc.append({"idx": i, "level": k, "en": en, "zh": zh})
        elif k == "quote":
            a(f'<div class="para quote" data-idx="{i}" data-doc="{esc(doc_id)}" data-nid="{nid(doc_id, en)}">')
            a(f'<p class="en">{esc(en)}</p>')
            a(f'<p class="zh">{zh}</p>')
            if it.get("attrib"):
                a(f'<span class="attrib">{esc(it["attrib"])}</span>')
            a("</div>")
        elif k == "p":
            a(f'<div class="para" data-idx="{i}" data-doc="{esc(doc_id)}" data-nid="{nid(doc_id, en)}">')
            a(f'<p class="en">{esc(en)}</p>')
            a(f'<p class="zh">{zh}</p>')
            a("</div>")
    return "".join(out), toc


def render(specs):
    doc_order = []
    docs_entry = {}
    for i, spec in enumerate(specs):
        m = spec.get("meta", {})
        doc_id = m.get("doc_id") or m.get("title_en") or f"doc{i}"
        chunk, toc = render_doc_chunk(spec, doc_id)
        docs_entry[doc_id] = {
            "meta": {
                "title_en": m.get("title_en", ""),
                "title_zh": m.get("title_zh", ""),
                "crumb": m.get("crumb") or m.get("title_en") or doc_id,
            },
            "html": chunk,
            "toc": toc,
        }
        doc_order.append(doc_id)

    out = []
    a = out.append
    a("<!doctype html><html><head><meta charset='utf-8'>")
    a('<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
    a(f"<title>交叉对照阅读 · 文献库（{len(doc_order)} 篇）</title>")
    a(f"<style>{CSS}</style></head><body>")

    a('<div class="topbar"><h1>交叉对照阅读<span class="sub">'
      f'从下面两个下拉菜单里任选两篇对照阅读 · 文献库共 {len(doc_order)} 篇</span></h1>')
    a('<div class="modes">'
      '<button data-mode="bilingual" type="button">双语</button>'
      '<button data-mode="en-only" type="button">EN</button>'
      '<button data-mode="zh-only" type="button">中文</button>'
      '</div>')
    a('<button id="xrefOpenBtn" class="xrefCountBtn" type="button">跨文献批注 (0)</button>')
    a("</div>")
    a('<div id="ownNoteBanner" style="display:none">'
      '未读取到这两篇文献各自的批注——如果你已经在单篇页面上写过批注，'
      '请从 GitHub Pages 打开这个对照页面（而不是这个 Artifact 链接），两边才是同一个域名，才能读到。'
      '</div>')

    a('<div class="panes">')
    for side in ("A", "B"):
        a(f'<div class="pane" data-side="{side}">'
          '<div class="pane-head">'
          f'<select class="paneDocSelect" data-side="{side}"></select>'
          '<span class="t-en"></span><span class="t-zh"></span>'
          '<select class="jumpSelect"></select>'
          "</div>"
          '<div class="pane-scroll"></div>'
          "</div>")
    a("</div>")

    a('<div id="selPill" style="display:none">+ 关联</div>')
    a('<div id="xrefHint" style="display:none">'
      '<span id="xrefHintText"></span>'
      '<button id="xrefHintCancel" type="button">取消</button></div>')
    a('<div id="xrefBackdrop"></div>')
    a('<div id="xrefCard" style="display:none">'
      '<div class="hl-head">跨文献批注</div>'
      '<div class="xq" id="xrefCardA"><span class="side-lbl"></span><span class="q"></span></div>'
      '<div class="xq" id="xrefCardB"><span class="side-lbl"></span><span class="q"></span></div>'
      '<textarea id="xrefCardNote" placeholder="这两段之间是什么关系？写下你的批注…"></textarea>'
      '<div class="actions">'
      '<button id="xrefCardDelete" class="danger" type="button" style="display:none">删除</button>'
      '<button id="xrefCardCancel" type="button">取消</button>'
      '<button id="xrefCardSave" class="primary" type="button">保存</button>'
      '</div></div>')

    a('<div id="xrefPanel">')
    a('<div class="ph"><b>跨文献批注</b><button id="xrefCloseBtn" type="button">&times;</button></div>')
    a('<div id="xrefList"></div>')
    a('<div id="xrefTools">'
      '<button id="xrefExportMd" type="button">导出 Markdown</button>'
      '<button id="xrefExportJson" type="button">备份 .json</button>'
      '<button id="xrefImportBtn" type="button">导入备份</button>'
      '<input type="file" id="xrefImportFile" accept="application/json" style="display:none">'
      '<button id="xrefClear" type="button" style="color:var(--danger)">清空</button>'
      "</div>")
    a("</div>")

    a(f"<script>window.__CR_DOCS={json.dumps(docs_entry, ensure_ascii=False)};"
      f"window.__CR_DOC_ORDER={json.dumps(doc_order, ensure_ascii=False)};</script>")
    a(f"<script>{JS}</script>")
    a("</body></html>")
    return "".join(out)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    spec_paths = sys.argv[1:-1]
    output_path = sys.argv[-1]
    specs = [json.load(open(p, encoding="utf-8")) for p in spec_paths]
    html_out = render(specs)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {output_path} ({len(html_out)} bytes) -- library of {len(specs)} documents")


if __name__ == "__main__":
    main()
