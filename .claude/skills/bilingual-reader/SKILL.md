---
name: bilingual-reader
description: Turn an academic article, book chapter, or paper (PDF, .docx, or URL) into a bilingual English–Chinese deep-reading HTML page — paragraph-aligned EN/ZH, block quotes annotated with whose position they represent, and a glossary explaining key theoretical terms and named scholars. Use this whenever the user wants to "deep read" / 精读 / 深度阅读 a paper, asks for a 中英对照 or bilingual version of an article, uploads a PDF of a journal article and wants help understanding it, says they want a reading page or reading aid for a text, or asks for terms and citations in a paper to be explained. Trigger it even when the user only says something like "帮我读一下这篇" or "make this readable" about an academic source — that is what this skill is for.
---

# Bilingual deep-reading page

Produces a self-contained HTML page that lets someone read a difficult academic
text in English while keeping a Chinese rendering directly beneath each
paragraph, with the machinery of the argument made visible.

The reason this is worth more than a translation: in a dense theory paper, the
hardest part is not vocabulary. It is tracking **whose position is being stated
at any moment.** Academic prose quotes an opponent at length, then demolishes
them two paragraphs later. A reader working in a second language routinely
mistakes the quoted opponent for the author. Everything below is built to
prevent that specific failure.

## Workflow

### 1. Get the text out

| Source | Approach |
|---|---|
| PDF | `pdftotext -layout file.pdf out.txt`, or the `pdf` skill for scanned/OCR files |
| .docx | unzip and read `word/document.xml`, or the `docx` skill |
| URL | WebFetch; if the publisher blocks it, say so and ask for the file |

Scanned PDFs come back with OCR damage — `§` for `S`, `,` for `.`, mangled
journal names in the references. Fix errors you are confident about silently.
Where OCR has genuinely destroyed meaning, keep the text and flag it in the
page's reading note rather than inventing a plausible sentence.

### 2. Segment

One source paragraph becomes one block. Resist merging short paragraphs or
splitting long ones: the alignment is the product. A reader glancing between
columns needs the two sides to correspond exactly.

Block kinds:
- `h2` — numbered sections (`15.3 A THEORY OF NEW-BUILD GENTRIFICATION?`)
- `h3` — subsections
- `p` — body paragraph
- `quote` — indented block quotation

### 3. Translate

Write for someone who is reading the English alongside, not instead. That
changes the target: the Chinese should let them re-enter the English sentence,
not replace it.

- **Keep the English term on first use inside the Chinese**: `租隙(rent gap)`,
  `置换(displacement)`, `政策流动性(policy mobility)`. The user is learning
  the term as much as the sentence, and will meet it again in English.
- **Never transliterate scholar names.** `Smith(1979)` stays `Smith(1979)`.
  Chinese renderings of Western surnames make citations impossible to look up.
- **Preserve page references**: `(1170页)`, `(2423页)`.
- **Translate hedges exactly.** `tends to be`, `arguably`, `it remains unclear`
  carry the author's confidence level. Flattening them into assertions is the
  most damaging error available here, because it turns a careful claim into an
  overclaim the reader may then cite.
- Long English sentences may split into two Chinese sentences where the syntax
  demands it — but not so far that the paragraph stops aligning.

### 4. Annotate every block quote — the part that matters most

Each `quote` gets an `attrib` string. It must answer: **whose words, reaching us
through whom, and does the framing author agree?**

Compare a bare attribution with a useful one:

- Weak: `Lambert & Boddy (2002)`
- Strong: `Lambert & Boddy (2002) 原话,经 Davidson 转引——注意这是被 Davidson 接下来反驳的观点,不是他本人立场`

The second sentence is the whole point. Without it the reader may absorb
"gentrification is a misnomer here" as the chapter's conclusion when the chapter
exists to refute exactly that.

Patterns that recur:
- `X (year) 原话,经 [框架作者] 转引` — plain relay, author neutral or agreeing
- `...——注意这是被 [作者] 接下来反驳的观点,不是他本人立场` — quoted to be rebutted
- `...——这是与 [作者] 立场相左的观点` — a live opposing position
- `...——[作者] 本人的核心主张` — the author's own thesis, stated in their words

If you cannot tell from the surrounding text whose side a quote is on, read
further before writing the attribution. Guessing here defeats the purpose.

### 5. Build the glossary

An entry earns its place if not knowing it would make a paragraph unreadable —
not merely unfamiliar. Aim for roughly 15–30 entries on a full article.

Categories that work: `理论/思潮`, `人物`, `概念`, `政策/机构`, `地名`.

For **people**, say what they are known for and which of their works the text is
leaning on — that is what lets the reader chase a citation.

For **theory terms**, give the definition and then, crucially, **what work the
term is doing in this particular text**. A generic dictionary gloss of "第三条
道路" is available anywhere; what the reader needs is that Davidson invokes it
because its progressive vocabulary is precisely what let state-led gentrification
be described as social improvement.

Entries are `{"id","cat","term","def"}`. Give each a stable `id` like
`g-rentgap`; body text can then link to it with
`<a class="gref" href="#g-rentgap">租隙</a>` in the `zh` field, since `zh` is
rendered as HTML rather than escaped. Use links sparingly — once per term, at
first substantive use.

### 6. Render

Write the spec to JSON and run the bundled script, which owns all styling
(responsive, light/dark, mode toggle, reading progress, collapsible glossary and
references):

```bash
python .claude/skills/bilingual-reader/scripts/render_reading_page.py spec.json out.html
```

Spec shape:

```json
{
  "meta": {
    "doc_id": "lees-2008-social-mixing",
    "eyebrow": "Book chapter · Gentrification",
    "title_en": "New-build gentrification",
    "title_zh": "新建式绅士化",
    "byline": "Mark Davidson · Handbook of Gentrification Studies, ch. 15, pp. 247–261",
    "crumb": "Davidson · New-build gentrification",
    "citation": "Davidson, M. (2018). New-build gentrification. In ...",
    "note": "OCR 扫描件,个别字符有识别错误,已尽量修正。",
    "footer": "翻译供阅读辅助之用;正式引用请以原文为准。"
  },
  "items": [
    {"kind":"h2","en":"15.1 INTRODUCTION","zh":"15.1 引言"},
    {"kind":"p","en":"...","zh":"..."},
    {"kind":"quote","en":"...","zh":"...","attrib":"..."}
  ],
  "glossary": [{"id":"g-rentgap","cat":"概念","term":"租隙(rent gap)","def":"..."}],
  "references": "optional raw reference list, HTML allowed"
}
```

`en` is HTML-escaped; `zh`, `def`, and `references` are not, so they can carry
glossary links and light markup.

### Annotations (built in — nothing to configure)

Every paragraph and block quote gets a `＋ 批注` control. Notes auto-save to
`localStorage` about half a second after typing stops, and again on blur; the
saved note then displays in place, directly beneath the paragraph it belongs to.

Two views onto the same set: a floating drawer for jumping around mid-read, and
a permanent **「我的批注 · 总览」 section at the end of the document** listing
every note beside the sentence it was written against. Both rebuild whenever a
note is saved — a note written mid-read has to appear in the overview without
the reader going looking for it.

The overview carries the export tools, and export is the point. Annotations
that stay locked inside a reading page are inert; this workflow is reading
*toward* an essay, so notes have to come out in a form that pastes into a
draft.

### Selection-anchored annotations (highlight-and-note on any phrase)

The `＋ 批注` control above is paragraph-level — one note per block. A second,
complementary mode lets the reader select *any* phrase or sentence inside a
paragraph and attach a note to exactly that selection, Medium/Hypothesis-style:

- Selecting text inside an `.en`/`.zh` paragraph shows a small floating `＋ 批注`
  pill near the selection. Clicking it opens a card — docked to the right edge
  on desktop, a bottom sheet on narrow/mobile viewports — with the quoted
  selection, a textarea, and Save/Cancel/Delete.
- `validSelection()` anchors on the paragraph the selection **starts** in and
  clips the end back to that paragraph's own boundary — it does not require
  the whole raw Range to already live inside one `<p>`. This matters because
  `p.en` and `p.zh` sit close together: a real mouse drag very easily
  overshoots the end of a wrapped line by a few pixels, which resolves the
  browser's own selection Range into the *next* paragraph (sometimes the
  other language, sometimes the following block entirely). An earlier version
  demanded the whole selection stay inside one `<p>` and silently rejected
  the entire selection the moment it overshot — which is what made "select a
  phrase to annotate" effectively not work for ordinary mouse drags (it only
  worked for drag distances/line lengths lucky enough to never overshoot). If
  you touch this function, test it with a genuine `page.mouse` drag across a
  wrapped line in Playwright, scrolled into view first — not just a
  synthetic `Range`+`selectionchange` dispatch, which won't reproduce this.
- Saving wraps the selected substring in `<mark class="hl-anno">` inline, so the
  reader sees at a glance which phrases carry a note; clicking an existing mark
  reopens the card to edit or delete it.
- **「+ 关联另一段」** lets one note span two passages that aren't adjacent: click
  it, the card hides with a hint to go select elsewhere, and the next selection
  gets appended to the same draft before the card reopens with both quoted
  fragments and the note text you'd already typed preserved. Use this for "these
  two claims contradict" or "this is the same move as that" style notes.
- These live in their own `localStorage` key (`br-highlights:{doc}`, separate
  from `br-notes:{doc}`) but feed into the *same* `entries()`/`markdown()`/
  `reviewPrompt()` pipeline as paragraph notes — so the overview, the 批注 nav
  tab, the badge count, and the AI-review-prompt export all include both kinds
  without any extra reader-facing distinction beyond a `［选段］` tag.
- A linked (multi-fragment) note never collapses into one flattened line in
  any of those lists — `renderSrcInto()` (shared by `buildList()` and the
  sidebar) gives it a `🔗 关联 N 处` badge plus one independently clickable
  `↳` row per fragment, each jumping to *that* fragment's own passage. This
  was a real bug, not a style choice: the first version joined every
  fragment's text into a single string whose one click target only ever
  scrolled to the first fragment, silently stranding the others.
- Highlighting is best-effort: it only wraps a selection that sits intact
  inside a single text node (not split across an inline tag like a glossary
  link). When a selection crosses such a boundary, the note still saves and
  still shows up in every list/export — it just doesn't also get the inline
  `<mark>`. This is a deliberate scope boundary, not a bug to chase.
- Because the EN and ZH paragraphs are two independent translations, there's
  no reliable way to compute which substring of the *other* language
  corresponds to an arbitrary selected phrase — there's no true word/clause
  alignment data to work from, and building one would mean restructuring
  spec.json into per-sentence segment arrays and re-segmenting every already-
  translated block (218 across the two current readings) — rejected as too
  costly for the payoff (see below). What ships is a **two-tier heuristic**,
  tried after the flat whole-paragraph version was reported as "比例非常不准确"
  (noticeably off on longer paragraphs):
  1. **Sentence-level (preferred).** `sentenceRanges()` splits plain text on
     EN/ZH sentence-ending punctuation (`. ! ? 。！？…` plus trailing closing
     quotes/brackets) — a cheap regex heuristic, not real NLP, but needs no
     spec.json change and no manual re-segmentation, since it runs on
     whatever EN/ZH text is already on the page. The FIRST version of this
     treated every end-mark as a real sentence end, which badly over-split
     academic EN text full of page citations like "(Wacquant, 2010, p. 218)"
     — "p." alone reads as a sentence end to a naive regex, while the ZH
     side cites the same page as "第218页" (no period at all) — so the EN
     side ended up with noticeably MORE "sentences" than ZH on exactly the
     citation-heavy paragraphs this skill annotates most, breaking the
     index-mapping below and silently falling back to the coarser
     whole-paragraph guess. Reported by the user via a live screenshot
     (Yrjänä item 44, three "p. ###)" citations: naive splitting gave EN 7
     "sentences" against ZH's real 4). Fixed by peeking at what follows each
     candidate end-mark (skip whitespace, at most one opening bracket): real
     sentence ends are virtually always followed by a capital letter, an
     opening quote, or end of paragraph, while a citation abbreviation like
     "p."/"pp."/"et al." is virtually always followed by a lowercase letter
     or digit — so that signal decides whether to split there, rather than a
     fixed abbreviation list. `validSelection()` locates the selection's
     start/end as `{ssIdx/esIdx, ssFrac/esFrac, srcSentCount}` — which
     sentence, and a 0–1 fraction *within* that sentence — via
     `locateInSentences()`. If the sibling paragraph happens to split into
     the **same number of sentences**, `markLinkedRange()` maps sentence-to-
     sentence by index and applies the within-sentence fraction there — this
     narrows the guess from "a span of the whole paragraph" to "a span of one
     sentence," confirmed in `test_sentence_alignment.py` to not bleed into
     neighboring sentences on a real 3-sentence/3-sentence block.
  2. **Whole-paragraph fallback.** When the sibling's sentence count doesn't
     match, falls back to the original flat `startFrac`/`endFrac` (where the
     selection falls within its OWN paragraph's text length, via
     `textOffsetInAncestor()`) applied to the sibling paragraph's length —
     still an approximation, but keeps the feature from erroring or reverting
     to underlining the whole paragraph when sentence counts disagree.
  Either tier wraps the estimated span — not the whole paragraph — in
  `<span class="linked-underline">`, via `rangeFromGlobalOffsets()` plus
  `range.surroundContents()` (best-effort, same as `wrapTextInNode()`: skips
  silently if the estimated range straddles an inline tag boundary it can't
  wrap). Both tiers are still heuristic approximations, not guarantees — say
  so if the user asks how exact it is. `text-decoration` (not `border-bottom`)
  in `--hl`, matching `mark.hl-anno`'s own color so it reads as "corresponds
  to a highlight." Went through three rejected VISUAL designs in direct
  testing before settling on an underline at all: a bare 🔗 glyph (too
  subtle), a tinted box with a "🔗 关联批注" pill (read as a separate badge,
  not "对应划线"), then underlining the WHOLE sibling paragraph (explicitly
  rejected — "应该只有对应划线的那部分也有划线，而不应该是现在这样全段划上") —
  and then one rejected ACCURACY tier (the original flat whole-paragraph
  proportional guess alone, superseded by the sentence-level tier above once
  it was reported as too inaccurate). Deliberately **not interactive** — no
  click handler on the span — since the only way to add one without
  colliding with normal text selection elsewhere in that paragraph would be a
  separate click target, which is exactly what got rejected in the visual-
  design round; open the note from the sidebar/nav/overview instead.
- There is deliberately **no in-page voice input.** An earlier draft wired up
  the Web Speech API, but it's pointless complexity: any OS-level dictation
  (macOS dictation, Windows voice typing, etc.) already types into the note
  textarea like any other text field, with no iframe-permission uncertainty
  and no extra code to maintain.
- Opening a note for editing (`edit()` for paragraph notes, `openCard()` for
  highlights) calls `focusSoon()` — `el.focus()` immediately, then again on
  the next `requestAnimationFrame` — not a bare `.focus()`. A bare call
  worked in this skill's own `file://` Playwright tests but was reported as
  unreliable on the real published artifact; the double call is cheap
  insurance against whatever layout/paint timing difference causes that, and
  costs nothing when the first call already worked.

### Self-assigned tags (free-form, not a fixed taxonomy)

Both annotation kinds — paragraph notes and selection highlights — take an
optional space/comma-separated tag field (`.note-tags` inline under the
paragraph editor, `#hlTags` in the highlight card). Tags are read-your-own
labels like "可引用" or "待查", not a controlled vocabulary the skill defines.

- Paragraph notes predate tags and were plain strings in `localStorage`.
  `noteOf(id)` reads either the legacy string form or the new `{text,tags}`
  object form, so nothing needed migrating — an old saved note just has an
  empty tag list until edited. Don't "clean up" by forcing every entry to the
  new shape on load; the whole point of `noteOf()` is that both forms stay
  valid indefinitely.
- Tags render as small pill chips (`.tag-chip`) wherever a note's text shows:
  inline under the paragraph, in the sidebar, in the nav panel's 批注 tab, and
  in the end-of-document overview. **Clicking any chip, anywhere, toggles a
  tag filter** (`activeTagFilter`) that narrows all three list views to
  matching rows and scopes `markdown()`/`reviewPrompt()` to the same subset —
  one shared filter state, not a per-list control. A `.tag-filter-bar` with a
  clear button appears at the top of a filtered list; exports that are
  currently filtered say so in their own text (`（仅导出标签：#…）`) so a
  pasted export doesn't silently look like the reader's full set of notes.
  `ovClear`/"清空" always wipes everything regardless of the active filter —
  it's a full reset, not a scoped delete, and should stay that way.
- Tabbing from a note's textarea into its tag field blurs the textarea, but
  the editing UI must not collapse on that blur — `scheduleCollapseCheck()`
  defers the check one tick so the newly-focused field (if still inside the
  same `.note`) is already `document.activeElement` by the time it runs. Both
  the textarea's and the tag input's blur handlers go through this, not a
  bare `wrap.classList.remove('editing')`.
- Previously-used tags are **pickable**, not just freely retyped: every
  `.note-tags`/`#hlTags` input shares one `<datalist id="tagOptions">`
  (`list="tagOptions"`), rebuilt from `allDistinctTags()` inside `refreshAll()`
  so it's always current. A native datalist replaces the WHOLE input value
  when a suggestion is picked — it helps most for a field's first tag; a
  second tag after a space still has to be typed out. That's an accepted
  limit of using the plain HTML control instead of building a custom
  multi-chip tag-input widget, not a bug to fix later unless asked.
- `#tocSidebar` shows the tag directory as an **overlay layer on top of the
  TOC tree**, not a second swapped-in pane (`.sb-pane`/`.sb-switch-btn` — a
  pair of equal-weight buttons — was the first design; rejected: "左边目录标签
  不是这个意思 是说标签像是一层layer... 左侧只需要目录这个按钮不需要标签的大
  按钮，最多是一个开关" — the reader wants 目录 as the one real destination,
  with tags as an occasional small switch, not a second button implying two
  equally-likely panes). The tree (`.sb-tree`) always stays in the DOM inside
  `.sb-tree-wrap`; a single small toggle (`#tagLayerToggle`, styled as a
  tiny switch, not a button the size of "目录") shows/hides an absolutely
  positioned `#sbTagOverlay` (`position:absolute;inset:0` within
  `.sb-tree-wrap`, elevated with a border + shadow so it visibly reads as a
  layer sitting above the tree, not a replacement for it) containing
  `#sbTagList` (`buildTagDirectory()`). The directory lists every distinct
  tag across both annotation kinds with a count, sorted alphabetically;
  clicking a row calls the SAME `toggleTagFilter()` the chips elsewhere
  call, so filtering from the directory and filtering from a chip are one
  shared state, not two. The switch's on/off state persists across reloads
  via `localStorage['brTagLayer']`. This is independent of the floating nav
  panel's own `showTab()` (目录/术语/批注) — different component, same toggle
  idea, don't conflate them if you touch either.

### The 「AI 点评」 button — what it can and cannot be

A published artifact **cannot call a language model at runtime.** The only
runtime capabilities available are `downloads` and `mcp` (viewer-consented
claude.ai connectors) — there is no completion endpoint exposed to page code.
Do not write `window.claude.ai`/`.complete`/`.prompt` calls; they do not exist,
and a button that silently does nothing is worse than no button.

So the review button assembles the request instead of answering it: it copies
**the reader's notes + each note's source paragraph and translation + a written
review instruction** to the clipboard, ready to paste to Claude. The instruction
asks for three things, and the third is the one that earns its place:

1. **提炼** — what are these notes actually circling? Name 2–4 through-lines,
   including ones the reader may not have noticed they were tracking.
2. **评价** — judge each note: which caught the argument, which misread it, and
   in particular which mistook a position the author quotes *in order to rebut*
   for the author's own. That failure is the whole reason this skill annotates
   quotes, so the review prompt should hunt for it specifically.
3. **建议** — what to read next, and which notes could grow into an essay
   paragraph.

Pasting into a session that already has the source PDF gets a better review
than any in-page call could, since the reviewer can check the notes against
the full text rather than the excerpt. Say this plainly when handing the page
over — frame the button as what it is, so nobody waits for an answer that is
not coming.

### 「AI 解读」 — the same idea, scoped to ONE annotation as a question

"评价我全部的批注" (批评/点评, above) and "解读我这一条批注在问什么" are different
asks — the second shouldn't require copying every other note just to get one
question answered. `askPrompt(r)` is the per-row counterpart to
`reviewPrompt()`: it treats that single note/highlight's text AS A QUESTION
and copies it, plus its source passage (EN + ZH, or every linked fragment if
it's a multi-fragment highlight) and its tags, to the clipboard as a
ready-to-paste request. Same runtime constraint as 「AI 点评」 — no completion
endpoint on a published page, so this copies the request, it doesn't answer
it.

`buildAskBtn(r, compact)` renders one of two variants of the same action,
shared by `buildList()` (nav 批注 tab + end-of-document overview) and
`buildSidebarList()` (`#noteSidebar`):
- `compact=false` → `.ask-ai-btn`, a labeled pill ("💬 AI 解读") — there's
  room for a label in those wider rows.
- `compact=true` → `.ns-ask`, an icon-only button ("💬") positioned left of
  the existing `.ns-edit` (✎) icon in a `.ns-row` — that column is only
  14.5rem wide, no room for a text label next to a second icon. `.ns-row`'s
  right padding grew from `1.7rem` to `3.4rem` to fit both icons.
`copyText()` gained an optional 4th `opts` param (`{okText, failText}`) so
the icon-only variant can flash a bare `✓`/`✕` instead of the long "✓ 已复制"
label, which would overflow a 1.5rem-wide button.

### AI 备注 — closing the loop 「AI 解读」 opens

The user tried 「AI 解读」, pasted the copied prompt into a Claude conversation,
got a real answer back, then pasted THAT answer into the chat and said: "我
需要的恰恰是AI输出完可以直接加入到这个批注内容里并标注AI备注" — the missing
piece wasn't the answer, it was a place to put it back. A published page
still can't call a model itself, so this doesn't close the loop
automatically; it gives the reader somewhere to paste the result by hand.

Both annotation kinds get an optional `aiNote` field, alongside `text`/`tags`:
`.note-ai` (a plain `<textarea>`, shown only while a paragraph note is
`.editing`, right after `.note-tags`) and `#hlAiNote` (always visible in
`#selCard`, the highlight card). Deliberately a plain textarea, not a
"📋 粘贴" button wired to `navigator.clipboard.readText()` — clipboard
**write** already needed requesting permission for 「AI 解读」/「AI 点评」;
**read** is more sensitive and more likely to be refused outright in a
sandboxed context like a Claude Artifact's iframe. A textarea takes a native
Cmd/Ctrl+V paste with no permission prompt at all, so it sidesteps the
question entirely instead of risking a second clipboard feature that's
quietly broken in the one environment this skill ships to most.

`noteOf()`/highlight objects carry `aiNote` the same way they carry `tags` —
`paint()` (paragraph notes) and `entries()` → `buildList()`/
`buildSidebarList()` (both kinds) render it as a visually distinct
`<div class="ai-note">` block, labeled "🤖 AI 备注" (`.ai-note-lbl`), styled
with the `--hl` accent (same family as the cross-language underline and
`mark.hl-anno`) so it reads as "AI-sourced," not mixed into the reader's own
paragraph text. `markdown()`/`reviewPrompt()` both include it as its own
line (`AI 备注：…` / `【此前的 AI 备注】…`) so an existing AI note survives a
re-export instead of being silently dropped. `askPrompt()` also includes it
when present (`【此前已有的 AI 备注，这次请在此基础上继续回答，不要重复】`) so
asking a FOLLOW-UP question doesn't make the next answer repeat the first.

### Baking your own analysis into the page

When the user pastes their real annotations back into the conversation and asks
for review, evaluation, or writing guidance, do that analysis properly — this
is the actual point of the whole annotation system, and it deserves real
thinking, not a rushed pass. Once you've written it, offer to bake it into the
page itself as a permanent, dated section, rather than leaving it stranded in
the chat transcript. Add an entry to `spec["ai_commentary"]`:

```json
"ai_commentary": [
  {"date": "2026-08-07", "html": "<h3>提炼</h3><p>...</p><h3>评价</h3>..."}
]
```

`html` is rendered unescaped directly into the page (light markup — `h3`, `p`,
`ul`/`li`, `strong`, `em`, short `blockquote` — is fine; keep it consistent
with the CSS already defined for `.aic-body`). Append a new entry each time
rather than overwriting the old one — the page accumulates a dated history of
commentary the same way the user's own notes accumulate.

Be precise about what this is and is not: it is **not** the page generating
anything on its own. It's you, in this conversation, writing an analysis and
then choosing to publish it as static content by re-rendering and
republishing the artifact to the same URL. The user still has to bring you
their notes to get a new entry — nothing about this closes that loop
automatically. What it does change: once written, the analysis lives on the
page itself, so revisiting it later doesn't require digging through chat
history or re-running the copy/paste flow just to read something you already
wrote. Say this plainly when offering it, so it's clear what's actually
different from the copy-to-clipboard flow and what isn't.

Keep your own commentary free of long verbatim quotation from the source
article — a few words in quotes for precision is fine, reproducing whole
sentences repeatedly is not. The same convention as translating the article
in the first place: paraphrase and cite, don't dump text.

### Chinese typography

The Chinese translation is the primary reading text for this skill's actual
users, not a secondary gloss — so it renders heavier and higher-contrast than
the English: `--font-zh` leads with sans "黑体"-style stacks (PingFang SC /
Microsoft YaHei / Heiti SC / Noto Sans SC) rather than a serif like Songti SC,
and the paragraph-level `.bipara p.zh` / `blockquote.cited p.zh` rules carry
`font-weight:600` at full `--ink` contrast. This is a site-wide default, not
something to reconsider per page — don't dial it back to serif/regular-weight
for an individual spec unless the user asks for that page specifically.

### The persistent structure sidebar

On viewports ≥1040px a sidebar renders to the left of the article, listing
every h2/h3 as a small vertical tree — a spine line with a larger dot per h2
and smaller indented dots for h3, doubling as both the table of contents and
a lightweight visual of the paper's structure. It's generated straight from
the same heading data the floating navigator's 目录 tab uses, requires no
spec changes, and updates automatically as sections are added. An
`IntersectionObserver` highlights whichever section is currently in view as
the reader scrolls, so the sidebar also answers "where am I in this
argument" while reading, not just "where can I jump to."

This is a real two-column layout, not a sidebar floating in whatever margin
happens to be left outside an independently-centered article column. `main`
and `#tocSidebar` are flex siblings inside a shared `.layout` wrapper
(`max-width:61rem`, centered as a unit), and the sidebar itself is
`position:sticky` rather than `position:fixed`. That distinction is the
reason 1040px works as a breakpoint at all — a `fixed` sidebar positioned
relative to viewport width needs roughly double the room (enough for a fully
centered 46rem column *plus* clear margin on both sides for the sidebar), but
a flex layout only needs sidebar + gap + article side by side, which fits an
ordinary, non-maximized laptop window. If you're tempted to widen the sidebar
or lengthen node labels, remeasure against this breakpoint rather than
assuming there's slack — it was sized deliberately tight to catch ordinary
laptop widths, not just ultrawide monitors.

### The annotations sidebar (right column, ≥1040px) and glossary popover

Two more pieces of the same "don't make the reader lose their place" problem:

**Persistent 我的批注 sidebar.** A third flex column (`#noteSidebar`), sticky
like `#tocSidebar`, listing every saved annotation — both paragraph notes and
selection highlights, pulled from the same `entries()` used by the overview
and exports — with **two separate click targets per row**: the quoted text
jumps to the passage (`scrollIntoView`), a small `✎` button opens the note
for editing *without* scrolling. For a highlight annotation that's a real
distinction (its editor is the floating `#selCard`, which doesn't require
navigating anywhere); for a plain paragraph note it still has to scroll,
because that note's only editor is the inline textarea under the paragraph —
`✎` there scrolls and then auto-opens the textarea, saving a click rather
than skipping the scroll entirely. Don't conflate these into one click target
again; a reader checking "did I already annotate this" should not be forced
to jump away from where they're currently reading just to look.

It shares the same **≥1040px** breakpoint as `#tocSidebar` rather than a
separate, higher one. An earlier version gated it at 1280px on the theory
that a third column needed main to stay near its full 46rem to look right —
overcautious: both sidebars use `flex-shrink:0`, so `main` (`flex:1 1 auto`,
no shrink override) is what absorbs the squeeze, rendering as narrow as
~33.5rem right at 1040px and growing back to its full 46rem by ~1240px. That
narrower column still reads fine, so there was no real reason to hide the
sidebar on anyone whose window happened to be 1040–1279px wide — which is
exactly the range where it had silently failed to appear. `.layout`'s
max-width (`77.5rem` = 13 + 2 + 46 + 2 + 14.5) is sized for all three columns
at once; if you touch sidebar widths, recompute this sum rather than guessing.
Below 1040px, annotations are still fully reachable through the floating nav
panel's 批注 tab — nothing is lost, the sidebar is a progressive enhancement.

**Glossary term popover.** `a.gref` links used to be plain `href="#g-id"`
anchors — clicking one jumped straight to the glossary section, which for a
100+ block article can be most of a page-length scroll away, with no obvious
way back except the browser's Back button. They're now intercepted globally
(a single delegated `click` listener checking `.closest('a.gref')`) and
open a small floating popover with the term, category, and full definition
right next to where you clicked — no navigation, no lost scroll position.
The popover still carries a "在术语表中查看完整条目 →" link for anyone who
wants the full glossary with category grouping; that's the fallback, not the
default path. A modifier-click (⌘/Ctrl/Shift/Alt) still falls through to the
native anchor behavior, so opening the glossary entry in a new tab still
works for anyone who wants that.

Below 1040px there usually isn't room for a 13rem sidebar next to a 46rem
article column without cramping either one, so it hides entirely and the
floating navigator's 目录 tab is what's left to serve narrower and mobile
viewports — don't try to also cram a shrunk sidebar into medium widths, that
navigator tab already covers it.

### File export and import — works on any host, not just Claude artifacts

`下载 .md` and `备份 .json` always render (not gated behind a capability
check): `offer()` tries the Claude-artifact `downloads` capability
(`window.claude.downloads`) first when present — it gives the viewer a
save-location picker — and falls back to a universal `Blob` + `<a download>`
(`nativeDownload()`) otherwise. That fallback is what makes export work when
this exact rendered HTML is served as a plain web page (e.g. from GitHub
Pages) where `window.claude` doesn't exist at all, and it's also just a
better fallback on a Claude artifact than silently hiding the buttons when
the capability isn't granted. The `.json` backup is worth offering because
`localStorage` is genuinely fragile — it's the only thing standing between a
reader and losing a paper's worth of annotations to a cleared cache.

`导入备份 .json` is the other half: it reads a previously-exported backup file
(via a hidden `<input type="file">`) and **merges** it into the current
page's `notes`/`highlights` by key/id — an imported entry overwrites one with
the same id, but nothing already on the page gets discarded outright. This
exists specifically for moving notes between two different hosts of the same
reading (e.g. a Claude artifact a reader already annotated, and the same page
later republished to GitHub Pages): there is no live channel between two
pages' separate `localStorage`, so export-then-import is the whole
mechanism, not a stopgap for one. It warns (not blocks) on a `doc` mismatch
between the backup and the current page, in case the reader picks the wrong
file.

Two things to be aware of, and to tell the user when it matters:

- **Notes are per browser, per device, per origin.** `localStorage` is not
  synced, and two different hosts (a Claude artifact vs. GitHub Pages, or
  even two different GitHub Pages repos) are two different origins with
  completely separate storage, even for byte-identical HTML. Someone who
  annotates on a laptop will not see those notes on their phone; moving a
  page to a new host starts that host's copy empty until an import happens.
  Suggest exporting anything they care about before a host change.
- **Note identity is keyed to `meta.doc_id` plus a hash of each block's English
  text.** So re-rendering after adding new sections preserves existing notes,
  which is what makes incremental section-by-section delivery safe. But
  *editing* a paragraph's English orphans its note. If you revise translations
  or fix OCR in the `en` field of a block the user may already have annotated,
  say so rather than letting a note quietly vanish.

Always set an explicit, stable `meta.doc_id`. It defaults to `title_en`, which
means a later title tweak would silently detach every note on the page.

### The navigator (目录 / 术语 / 批注) — also built in, nothing to configure

A long article is unusable without a way to jump around it. The floating
`☰ 导航` button opens a bottom-sheet panel with three tabs, generated
automatically from the spec:

- **目录** — every `h2`/`h3` in the document, tap to jump straight to that
  section instead of scrolling.
- **术语** — the glossary, grouped by category and live-searchable by term or
  definition, so a 30+ entry glossary stays findable instead of forcing a
  scroll to the bottom of the page to scan a flat list. Tapping a result jumps
  to its full entry at the end of the article and briefly highlights it.
- **批注** — the same note list the end-of-document overview shows, reachable
  from anywhere mid-read rather than only after finishing. It links onward to
  the overview for the full toolset (copy / AI-review prompt / export / clear).

Tapping outside the panel (the dimmed backdrop) or the ✕ closes it — standard
bottom-sheet behavior. The floating button itself only ever *opens* the panel;
once open it sits underneath the sheet, so a second tap on that same screen
position lands on the backdrop instead and closes it. Don't reintroduce a
toggle-to-close branch on the button's own handler — it would be dead code,
since a real tap can never land back on a button that's visually covered by
what it opened.

This is the reason `h2`/`h3` blocks get an `id="sec-{index}"` at render time:
position-based, regenerated fresh on every render, with no persistence concern
like note ids have — nothing reads those ids back later, they only need to be
internally consistent within one render for the TOC links to resolve.

If you're extending the renderer, verify all three tabs with a live browser
rather than trusting that HTML structure alone: `node --check` catches syntax
errors but not tab-switching logic, search filtering, or scroll-jump timing —
on a long (100+ block) page, a `scrollIntoView({behavior:'smooth'})` can take
close to a second to settle, so a test asserting the resulting scroll position
needs to wait accordingly rather than checking immediately after the click.

### 7. Check before handing over

- Block count matches the source's paragraph count for the range you covered
- Every `quote` has an `attrib` that states a position, not just a name
- No scholar's name has been transliterated
- `meta.doc_id` is set explicitly
- All three modes (双语 / EN / 中文) render

The renderer emits a fair amount of interactive JavaScript, and a syntax error
there fails silently in a way that looks like the page merely "not working".
`node --check` on the extracted `<script>` blocks catches that in a second and
is worth doing after any change to the script itself. If Playwright is
available, driving one note end-to-end — type, blur, reload, confirm it
survived — is the check that actually matters, because the failure mode users
notice is losing their annotations.

Then publish with the Artifact tool if the user wants a link, or send the file.
Pass `capabilities: {downloads: true}` to switch on the file-export buttons.

## Scope

Full articles run 60–120 blocks and are a substantial amount of writing. If the
source is long, translating it in one pass risks degrading toward the end —
where conclusions and research agendas live, which is often the part the reader
most needs.

So: say up front roughly how many blocks the source will take. If it is large,
offer to go section by section, and build the JSON incrementally — the renderer
is cheap to re-run, so there is no penalty for regenerating the page after each
batch. Do not silently truncate a paper and present it as complete; a reader who
believes they have the whole chapter will cite a conclusion that is not there.
