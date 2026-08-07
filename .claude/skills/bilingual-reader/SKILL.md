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

Below 1040px there usually isn't room for a 13rem sidebar next to a 46rem
article column without cramping either one, so it hides entirely and the
floating navigator's 目录 tab is what's left to serve narrower and mobile
viewports — don't try to also cram a shrunk sidebar into medium widths, that
navigator tab already covers it.

### File export (optional, needs a capability)

`下载 .md` and `备份 .json` stay hidden unless `window.claude.downloads` is
present, so the page degrades cleanly when opened as a local file. To enable
them, publish with `capabilities: {downloads: true}`. The `.json` backup is
worth offering because `localStorage` is genuinely fragile — it is the only
thing standing between a reader and losing a paper's worth of annotations to a
cleared cache. Saves are viewer-confirmed and can be declined; the button
handles `declined`, `rate_limited`, `too_large`, and hides itself on the
lifecycle codes.

Two things to be aware of, and to tell the user when it matters:

- **Notes are per browser, per device.** `localStorage` is not synced. Someone
  who annotates on a laptop will not see those notes on their phone, and
  clearing site data erases them. Suggest exporting anything they care about.
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
