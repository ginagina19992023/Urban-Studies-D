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
A floating button opens a drawer listing every note with the sentence it was
written against, and **copies the whole set as Markdown** — that export is the
point of the feature. Annotations that stay locked in a reading page are
inert; the workflow this serves is reading toward an essay, so notes have to
come out in a form that can be pasted into a draft.

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
