from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def select_text_in(pg, locator):
    pg.evaluate("""(el) => {
        var range = document.createRange();
        range.selectNodeContents(el);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""", locator.element_handle())

def select_middle_of(pg, locator):
    """Selects roughly the middle third of a paragraph's text, so the
    resulting startFrac/endFrac land away from 0 and 1 — a more realistic
    exercise of the proportional-range mapping than selecting the whole
    paragraph (which trivially maps to the whole sibling too)."""
    pg.evaluate("""(el) => {
        var full = el.textContent;
        var a = Math.floor(full.length * 0.33), b = Math.floor(full.length * 0.66);
        var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        var total = 0, node, startNode, startOff, endNode, endOff;
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
    }""", locator.element_handle())

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    block = pg.locator(".bipara").nth(2)
    en = block.locator("p.en")
    zh = block.locator("p.zh")

    # highlight the middle third of the EN paragraph
    select_middle_of(pg, en)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("英文侧批注，测试中文侧对应划线")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)

    ck("exact mark lands in the EN paragraph (the language actually selected)",
       en.locator("mark.hl-anno").count() == 1)
    ck("EN paragraph itself gets no linked-underline span (it already has the real mark)",
       en.locator("span.linked-underline").count() == 0)
    ck("ZH sibling paragraph gets exactly one linked-underline span (not the whole paragraph)",
       zh.locator("span.linked-underline").count() == 1)

    zh_full_len = len(zh.inner_text())
    zh_span_len = len(zh.locator("span.linked-underline").inner_text())
    ck("the underlined span is a PARTIAL substring of the ZH paragraph, not the whole thing",
       0 < zh_span_len < zh_full_len, (zh_span_len, zh_full_len))
    ck("underline is actually rendered on that span",
       pg.eval_on_selector("span.linked-underline", "el => getComputedStyle(el).textDecorationLine") == "underline")

    # the underline must survive switching to 中文-only mode, where the EN
    # paragraph (and its real <mark>) gets display:none
    pg.locator(".modes button").nth(2).click()  # 中文 button
    pg.wait_for_timeout(150)
    ck("EN paragraph (and its mark) hidden in zh-only mode", not en.is_visible())
    ck("ZH underlined span still present in zh-only mode", zh.locator("span.linked-underline").count() == 1)
    ck("ZH underlined span still visible in zh-only mode",
       zh.locator("span.linked-underline").first.is_visible())

    # back to bilingual, span still correct, no duplicates after a repaint cycle
    pg.locator(".modes button").nth(0).click()
    pg.wait_for_timeout(150)
    ck("back in bilingual mode: still exactly one underlined span",
       zh.locator("span.linked-underline").count() == 1)
    ck("still exactly one real mark in EN", en.locator("mark.hl-anno").count() == 1)

    # editing the SAME highlight (via the sidebar's ✎ button, since the
    # underline itself has no click target) shouldn't duplicate anything
    pg.locator(".ns-row .ns-edit").first.click()
    pg.wait_for_timeout(200)
    ck("sidebar edit button still opens the card", pg.locator("#selCard").is_visible())
    pg.locator("#hlNote").fill("英文侧批注，测试中文侧对应划线（已编辑）")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("editing the same highlight keeps exactly one ZH underlined span",
       zh.locator("span.linked-underline").count() == 1 and en.locator("mark.hl-anno").count() == 1)

    # now highlight the middle third of a ZH paragraph in a DIFFERENT block
    # -> EN side gets the partial underline this time
    block2 = pg.locator(".bipara").nth(4)
    zh2 = block2.locator("p.zh")
    en2 = block2.locator("p.en")
    select_middle_of(pg, zh2)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("中文侧批注，测试英文侧对应划线")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("exact mark lands in the ZH paragraph this time", zh2.locator("mark.hl-anno").count() == 1)
    ck("EN sibling (not ZH) gets the partial underline this time",
       en2.locator("span.linked-underline").count() == 1
       and zh2.locator("span.linked-underline").count() == 0)
    en2_full_len = len(en2.inner_text())
    en2_span_len = len(en2.locator("span.linked-underline").inner_text())
    ck("that underlined span is also partial, not the whole EN paragraph",
       0 < en2_span_len < en2_full_len, (en2_span_len, en2_full_len))

    pg.locator(".modes button").nth(1).click()  # EN-only button
    pg.wait_for_timeout(150)
    ck("ZH paragraph (with the real mark) hidden in en-only mode", not zh2.is_visible())
    ck("EN underlined span still visible in en-only mode",
       en2.locator("span.linked-underline").first.is_visible())

    # persistence across reload: both marks and both underlined spans should come back
    pg.locator(".modes button").nth(0).click(); pg.wait_for_timeout(150)
    pg.reload(); pg.wait_for_timeout(500)
    ck("no JS errors after reload", not errs, errs)
    ck("first block's ZH underlined span survives reload", zh.locator("span.linked-underline").count() == 1)
    ck("second block's EN underlined span survives reload", en2.locator("span.linked-underline").count() == 1)
    ck("both exact marks survive reload",
       en.locator("mark.hl-anno").count() == 1 and zh2.locator("mark.hl-anno").count() == 1)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
