from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def select_text_in(pg, locator):
    """Select the full text content of a <p> via a JS Range + dispatched
    selectionchange, mirroring what a real mouse-drag selection produces."""
    pg.evaluate("""(el) => {
        var range = document.createRange();
        range.selectNodeContents(el);
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

    paras = pg.locator(".bipara p.en")
    first_p = paras.nth(0)
    first_text = first_p.inner_text()

    select_text_in(pg, first_p)
    pg.wait_for_timeout(250)
    ck("pill appears on valid selection", pg.locator("#selPill").is_visible())

    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    ck("card opens after pill click", pg.locator("#selCard").is_visible())
    ck("card shows the selected fragment", first_text[:30] in pg.locator("#hlFrags").inner_text())
    ck("delete button hidden for a new annotation", not pg.locator("#hlDelete").is_visible())

    pg.locator("#hlNote").fill("这句是选中片段批注的测试内容")
    pg.locator("#hlSave").click()
    pg.wait_for_timeout(300)
    ck("card closes after save", not pg.locator("#selCard").is_visible())
    ck("inline mark rendered", pg.locator("mark.hl-anno").count() >= 1)
    ck("nav badge counts the highlight note", pg.locator("#navBtn .n").inner_text() == "1",
       pg.locator("#navBtn .n").inner_text())
    ck("overview lists the highlight row", "选中片段批注的测试内容" in pg.locator("#ovList").inner_text())
    ck("overview row tagged as a selection row", "［选段］" in pg.locator("#ovList").inner_text())

    # persistence across reload, including the inline mark
    pg.reload(); pg.wait_for_timeout(400)
    ck("no JS errors after reload", not errs, errs)
    ck("mark survives reload", pg.locator("mark.hl-anno").count() >= 1)
    ck("note text survives reload", "选中片段批注的测试内容" in pg.locator("#ovList").inner_text())

    # click the persisted mark -> reopens the card with delete available
    pg.locator("mark.hl-anno").first.click()
    pg.wait_for_timeout(150)
    ck("clicking existing mark reopens card", pg.locator("#selCard").is_visible())
    ck("delete button shown when editing", pg.locator("#hlDelete").is_visible())
    pg.locator("#hlCancel").click()
    pg.wait_for_timeout(150)
    ck("card closes on cancel", not pg.locator("#selCard").is_visible())

    # ---- link-two-fragments flow ----
    select_text_in(pg, first_p)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("关联批注草稿")
    pg.locator("#hlLink").click()
    pg.wait_for_timeout(150)
    ck("card hides while waiting for second selection", not pg.locator("#selCard").is_visible())
    ck("link hint shown", pg.locator("#hlHint").is_visible())

    second_p = paras.nth(5)
    second_text = second_p.inner_text()
    select_text_in(pg, second_p)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    ck("hint hides once second fragment picked", not pg.locator("#hlHint").is_visible())
    ck("card reopens with both fragments", pg.locator("#hlFrags .hl-frag").count() == 2)
    ck("draft note text preserved across the link step",
       pg.locator("#hlNote").input_value() == "关联批注草稿")

    pg.locator("#hlSave").click()
    pg.wait_for_timeout(300)
    ck("nav badge now counts 2 highlight notes", pg.locator("#navBtn .n").inner_text() == "2",
       pg.locator("#navBtn .n").inner_text())
    ck("two marks total after linked save", pg.locator("mark.hl-anno").count() >= 2)

    # markdown / AI-review exports should carry the linked fragments
    ctx_ok = True
    try:
        pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    except Exception:
        ctx_ok = False
    if ctx_ok:
        pg.locator("#ovReview").click(); pg.wait_for_timeout(400)
        clip = pg.evaluate("navigator.clipboard.readText()")
        ck("review prompt tags the linked entry", "关联 2 段" in clip, clip[:400])
        ck("review prompt includes both linked fragments",
           first_text[:30] in clip and second_text[:30] in clip)
        ck("review prompt includes the highlight note text", "关联批注草稿" in clip)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
