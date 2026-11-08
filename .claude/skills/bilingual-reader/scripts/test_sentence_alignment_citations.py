from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("yrjana_bilingual.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def select_exact(pg, locator, substring):
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

    # This is the exact real-world paragraph the user screenshotted as still
    # misaligned: it has THREE "(Author, Year, p. ###)" page citations, which
    # the old naive sentence-splitter mis-read as extra sentence ends (EN got
    # 7 "sentences" against ZH's real 4), breaking the index-based mapping.
    block = pg.locator(".bipara", has_text="false choice urbanism").first
    en = block.locator("p.en")
    zh = block.locator("p.zh")
    en_full = en.inner_text()
    zh_full = zh.inner_text()

    fourth_en_sentence = ("An important aspect of gentrification is the idea that the retrieval of a "
                           "place is accomplished by civilizing it, which in the policy lingo tends to "
                           "be described in terms of “upgrading”, “sustainability” and "
                           "“safety” (Thörn & Holgersson, 2016, p. 671).")
    ck("fixture sanity: the 4th EN sentence (with its page citation) is present verbatim",
       fourth_en_sentence in en_full, en_full)

    select_exact(pg, en, fourth_en_sentence)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("引文密集段落的句子对齐测试")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)

    ck("exact mark lands in EN", en.locator("mark.hl-anno").count() == 1)
    underline = zh.locator("span.linked-underline")
    ck("ZH sibling gets exactly one linked-underline span", underline.count() == 1)
    underline_text = underline.inner_text()

    # the full corresponding ZH sentence, including its OPENING words -- this
    # is exactly the part that was missing ("An"/"绅士化的一个重要面向" was
    # getting clipped off the front) before the citation-period fix
    ck("underline starts at the sentence's own opening, not one word short",
       underline_text.strip().startswith("绅士化的一个重要面向"), underline_text)
    ck("underline covers the sentence's distinctive closing wording",
       "第671页" in underline_text or "可持续性" in underline_text, underline_text)
    ck("underline does NOT bleed into the PRECEDING sentence (about moral legitimacy/道德上的正当性)",
       "道德上的正当性" not in underline_text, underline_text)
    ck("underline is a proper partial substring, not the whole ZH paragraph",
       0 < len(underline_text) < len(zh_full), (len(underline_text), len(zh_full)))

    # sanity check on the earlier sentences too, so a regression on sentence
    # 1/2/3 (not just the last one) would also be caught
    second_en_sentence = ("By utilizing the history of failed area-based initiatives in neighborhoods "
                           "with social housing estates, the city can legitimize gentrification as the "
                           "‘only hope’ in its anti-segregation work.")
    select_exact(pg, en, second_en_sentence)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("第二句测试")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("exactly two linked-underline spans now present (one per highlight made)",
       zh.locator("span.linked-underline").count() == 2)
    underline2 = zh.locator("span.linked-underline", has_text="唯一希望")
    u2_text = underline2.inner_text()
    ck("second sentence also aligns to its own ZH sentence, not spilling into neighbors",
       "唯一希望" in u2_text and "虚假选择" not in u2_text and "无可挽救" not in u2_text, u2_text)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
