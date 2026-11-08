# Regenerate the fixture this test reads before running it (comparative-
# reading.html is gitignored, regenerable; third-spec.json is a small
# committed synthetic 3rd document so the library-switching assertions below
# have a real 3rd option to switch to, not just the usual two real papers):
#   python3 render_comparative_page.py \
#     ../../../../Reading-Pages/lees-2008-social-mixing.spec.json \
#     ../../../../Reading-Pages/yrjana-2026-helsinki.spec.json \
#     third-spec.json comparative-reading.html
from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("comparative-reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def select_text_in(pg, locator, max_chars=40):
    # Select a short, realistic phrase (not the whole paragraph): a long
    # multi-line selection wraps a <mark> whose bounding-box CENTER can fall
    # in the gap between wrapped lines, which Playwright's .click() targets
    # and misses the element entirely.
    return pg.evaluate("""([el, maxChars]) => {
        var tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        var node = tw.nextNode();
        var len = Math.min(maxChars, node.nodeValue.trim().length);
        var start = node.nodeValue.indexOf(node.nodeValue.trim());
        var range = document.createRange();
        range.setStart(node, start);
        range.setEnd(node, start + len);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        return node.nodeValue.slice(start, start + len);
    }""", [locator.element_handle(), max_chars])

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width":1400, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)
    ck("two panes rendered", pg.locator(".pane").count() == 2)
    ck("library has 3 documents", len(pg.evaluate("window.__CR_DOC_ORDER")) == 3)
    ck("each paper-picker lists all 3 documents",
       pg.locator('.paneDocSelect[data-side="A"] option').count() == 3)
    ck("defaults to the first two DISTINCT documents",
       pg.eval_on_selector('.paneDocSelect[data-side="A"]', 'el=>el.value') !=
       pg.eval_on_selector('.paneDocSelect[data-side="B"]', 'el=>el.value'))
    ck("xref panel starts closed", "open" not in (pg.locator("#xrefPanel").get_attribute("class") or ""))
    ck("count button starts at 0", "0" in pg.locator("#xrefOpenBtn").inner_text())

    # mode switch
    pg.locator('.modes button[data-mode="en-only"]').click()
    ck("en-only mode hides zh", not pg.locator(".pane").first.locator("p.zh").first.is_visible())
    pg.locator('.modes button[data-mode="bilingual"]').click()

    # pick first paragraph in each pane
    left_p = pg.locator(".pane").nth(0).locator(".para p.en").first
    right_p = pg.locator(".pane").nth(1).locator(".para p.en").first

    left_text = select_text_in(pg, left_p)
    pg.wait_for_timeout(150)
    ck("pill shows after left selection", pg.locator("#selPill").is_visible())
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    ck("hint shows asking for the other side", pg.locator("#xrefHint").is_visible())

    right_text = select_text_in(pg, right_p)
    pg.wait_for_timeout(150)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(200)
    ck("note card opens after both sides selected", pg.locator("#xrefCard").is_visible())
    ck("card shows left quote", left_text[:20] in pg.locator("#xrefCardA .q").inner_text())
    ck("card shows right quote", right_text[:20] in pg.locator("#xrefCardB .q").inner_text())
    ck("card shows the actual document label, not just A/B",
       pg.locator("#xrefCardA .side-lbl").inner_text().strip() != "")

    pg.locator("#xrefCardNote").fill("这两段都在讨论社会混合政策的失败。")
    pg.locator("#xrefCardSave").click()
    pg.wait_for_timeout(200)
    ck("card closes after save", not pg.locator("#xrefCard").is_visible())
    ck("both sides now marked with mark.xref", pg.locator("mark.xref").count() == 2)

    pg.locator("#xrefOpenBtn").click()
    pg.wait_for_timeout(150)
    ck("panel opens and shows count 1", "1" in pg.locator("#xrefOpenBtn").inner_text())
    ck("panel lists the new cross-link", "社会混合政策的失败" in pg.locator("#xrefList").inner_text())

    # click the mark to reopen/edit
    pg.locator("#xrefCloseBtn").click()
    pg.wait_for_timeout(150)
    pg.locator("mark.xref").first.click()
    pg.wait_for_timeout(150)
    ck("clicking the mark reopens the card for edit", pg.locator("#xrefCard").is_visible())
    ck("delete button visible when editing", pg.locator("#xrefCardDelete").is_visible())
    pg.locator("#xrefCardCancel").click()

    # reload -> persistence (shared, library-wide store, not a per-pair key)
    pg.reload()
    pg.wait_for_timeout(300)
    ck("link persists after reload", pg.locator("mark.xref").count() == 2)
    ck("count persists after reload", "1" in pg.locator("#xrefOpenBtn").inner_text())

    # --- switch pane A to the THIRD document: the link (which is between
    # the original two) must disappear from view, since it isn't relevant
    # to this new pair, but must NOT be deleted from the shared store ---
    pg.locator('.paneDocSelect[data-side="A"]').select_option(label="Third (test)")
    pg.wait_for_timeout(200)
    ck("switching pane A away from the link's pair hides the mark",
       pg.locator("mark.xref").count() == 0)
    ck("count button reflects the new (irrelevant) pair", "0" in pg.locator("#xrefOpenBtn").inner_text())
    ck("third paper's own paragraph now shows in pane A",
       "third test paper" in pg.locator(".pane").nth(0).inner_text())

    # switch back -> the original link reappears untouched
    first_label = pg.eval_on_selector('.paneDocSelect[data-side="A"] option', 'el=>el.textContent')
    pg.locator('.paneDocSelect[data-side="A"]').select_option(index=0)
    pg.wait_for_timeout(200)
    ck("switching back restores the link", pg.locator("mark.xref").count() == 2)
    ck("count button restored too", "1" in pg.locator("#xrefOpenBtn").inner_text())

    # same-side rejection, then recover the way a real reader would: Escape
    left_p2 = pg.locator(".pane").nth(0).locator(".para p.en").nth(1)
    select_text_in(pg, left_p2)
    pg.wait_for_timeout(150)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    left_p3 = pg.locator(".pane").nth(0).locator(".para p.en").nth(2)
    select_text_in(pg, left_p3)
    pg.wait_for_timeout(150)
    pg.on("dialog", lambda d: d.accept())
    pg.locator("#selPill").click()
    pg.wait_for_timeout(200)
    ck("picking the same side twice does not open a card", not pg.locator("#xrefCard").is_visible())
    pg.keyboard.press("Escape")
    pg.evaluate("window.getSelection().removeAllRanges()")
    pg.wait_for_timeout(150)
    ck("hint cleared after Escape", not pg.locator("#xrefHint").is_visible())

    # delete flow
    pg.locator("mark.xref").first.click()
    pg.wait_for_timeout(150)
    pg.locator("#xrefCardDelete").click()
    pg.wait_for_timeout(200)
    ck("delete removes the marks", pg.locator("mark.xref").count() == 0)
    ck("count back to 0", "0" in pg.locator("#xrefOpenBtn").inner_text())

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
