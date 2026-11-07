from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def select_exact(pg, locator, substring):
    """Selects exactly `substring` within `locator`'s text (must occur once),
    via the Range API — a deterministic stand-in for a reader dragging the
    mouse over precisely that sentence."""
    pg.evaluate("""([el, needle]) => {
        var full = el.textContent;
        var idx = full.indexOf(needle);
        if (idx === -1) throw new Error('substring not found: ' + needle);
        var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        var total = 0, node, startNode, startOff, endNode, endOff;
        var a = idx, b = idx + needle.length;
        while (node = walker.nextNode()) {
            var len = node.nodeValue.length;
            if (startNode === undefined && total + len >= a) { startNode = node; startOff = a - total; }
            if (startNode !== undefined && total + len >= b) { endNode = node; endOff = b - total; break; }
            total += len;
        }
        var range = document.createRange();
        range.setStart(startNode, Math.max(0, startOff));
        range.setEnd(endNode, Math.max(0, endOff));
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""", [locator.element_handle(), substring])

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    # Block 21 of the Lees reading has exactly 3 sentences on both the EN and
    # ZH side — a case the sentence-aware mapping should align tightly,
    # unlike the old flat whole-paragraph proportional guess.
    block = pg.locator(".bipara").nth(21)
    en = block.locator("p.en")
    zh = block.locator("p.zh")

    en_full = en.inner_text()
    zh_full = zh.inner_text()
    middle_en = "The current trend in US housing redevelopment is to replace existing high-density social housing ‘projects’ with new lower-density mixed-income communities."
    first_zh_only = "开出的药方"      # unique to ZH sentence 1
    third_zh_only = "核心主旨"        # unique to ZH sentence 3
    ck("fixture sanity: middle EN sentence is present verbatim", middle_en in en_full, en_full)

    select_exact(pg, en, middle_en)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("句子级对齐测试：选中英文中间那句")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)

    ck("exact mark lands in EN (the language actually selected)", en.locator("mark.hl-anno").count() == 1)
    underline = zh.locator("span.linked-underline")
    ck("ZH sibling gets exactly one linked-underline span", underline.count() == 1)
    underline_text = underline.inner_text()

    ck("underline covers the middle ZH sentence's distinctive wording",
       "低密度混合收入社区" in underline_text or "住房再开发" in underline_text, underline_text)
    ck("underline does NOT bleed into ZH sentence 1 (sentence-level, not whole-paragraph)",
       first_zh_only not in underline_text, underline_text)
    ck("underline does NOT bleed into ZH sentence 3 (sentence-level, not whole-paragraph)",
       third_zh_only not in underline_text, underline_text)
    ck("underline is still a proper partial substring of the ZH paragraph",
       0 < len(underline_text) < len(zh_full), (len(underline_text), len(zh_full)))

    # a mismatched-sentence-count paragraph should still fall back gracefully
    # (no crash, still produces SOME partial underline) rather than erroring
    block2 = pg.locator(".bipara").nth(7)  # EN has 8 sentences, ZH splits differently
    en2 = block2.locator("p.en")
    zh2 = block2.locator("p.zh")
    en2_full = en2.inner_text()
    first_sentence_en2 = en2_full.split(". ")[0] + "."
    select_exact(pg, en2, first_sentence_en2)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("句子数不一致时的回退测试")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("no JS errors from the fallback path", not errs, errs)
    underline2 = zh2.locator("span.linked-underline")
    ck("mismatched sentence counts still produce a (fallback) partial underline, not a crash",
       underline2.count() == 1)
    u2_text = underline2.inner_text()
    ck("fallback underline is still partial, not the whole ZH paragraph",
       0 < len(u2_text) < len(zh2.inner_text()))

    # persistence: the new per-fragment sentence fields round-trip through
    # localStorage and still paint correctly after reload
    pg.reload(); pg.wait_for_timeout(500)
    ck("no JS errors after reload", not errs, errs)
    ck("sentence-aligned underline survives reload", zh.locator("span.linked-underline").count() == 1)
    ck("underlined text is unchanged after reload", zh.locator("span.linked-underline").inner_text() == underline_text)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
