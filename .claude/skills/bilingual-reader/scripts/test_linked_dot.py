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

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    block = pg.locator(".bipara").nth(2)
    en = block.locator("p.en")
    zh = block.locator("p.zh")

    # highlight a phrase on the EN side
    select_text_in(pg, en)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("英文侧批注，测试中文侧回显点")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)

    ck("exact mark lands in the EN paragraph (the language actually selected)",
       en.locator("mark.hl-anno").count() == 1)
    ck("EN paragraph itself gets no echo dot (it already has the real mark)",
       en.locator(".linked-note-dot").count() == 0)
    ck("ZH sibling paragraph's block gets an echo dot",
       block.locator(".linked-note-dot").count() == 1)
    ck("ZH sibling paragraph itself gets the visible tint class (not just the small dot)",
       "has-linked-note" in (zh.get_attribute("class") or ""))
    ck("tint is actually rendered (non-'none' box-shadow applied)",
       pg.eval_on_selector(".has-linked-note", "el => getComputedStyle(el).boxShadow") != "none")

    # the dot must survive switching to 中文-only mode, where the EN
    # paragraph (and its real <mark>) gets display:none
    pg.locator(".modes button").nth(2).click()  # 中文 button
    pg.wait_for_timeout(150)
    ck("EN paragraph (and its mark) hidden in zh-only mode", not en.is_visible())
    ck("echo dot still visible in zh-only mode", block.locator(".linked-note-dot").first.is_visible())

    # clicking the dot opens the same note, without requiring a mode switch back
    block.locator(".linked-note-dot").first.click()
    pg.wait_for_timeout(200)
    ck("clicking the dot opens the note card", pg.locator("#selCard").is_visible())
    ck("card shows the right note text", "英文侧批注" in pg.locator("#hlNote").input_value())
    pg.locator("#hlCancel").click(); pg.wait_for_timeout(150)

    # back to bilingual, dot still correct, no duplicates after a repaint cycle
    pg.locator(".modes button").nth(0).click()
    pg.wait_for_timeout(150)
    ck("back in bilingual mode: still exactly one dot", block.locator(".linked-note-dot").count() == 1)

    # editing the SAME note (not creating a new one) shouldn't accumulate dots
    block.locator(".linked-note-dot").first.click()
    pg.wait_for_timeout(200)
    pg.locator("#hlNote").fill("英文侧批注，测试中文侧回显点（已编辑）")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("editing the same highlight doesn't duplicate the dot",
       block.locator(".linked-note-dot").count() == 1)
    ck("still exactly one real mark after edit", en.locator("mark.hl-anno").count() == 1)

    # now highlight a phrase on the ZH side of a DIFFERENT block -> EN side gets the dot
    block2 = pg.locator(".bipara").nth(4)
    zh2 = block2.locator("p.zh")
    en2 = block2.locator("p.en")
    select_text_in(pg, zh2)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("中文侧批注，测试英文侧回显点")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("exact mark lands in the ZH paragraph this time", zh2.locator("mark.hl-anno").count() == 1)
    ck("EN sibling (not ZH) gets the echo dot this time", en2.locator(".linked-note-dot").count() == 0)
    ck("dot is a sibling of the EN paragraph, inside block2",
       block2.locator(".linked-note-dot").count() == 1)

    pg.locator(".modes button").nth(1).click()  # EN-only button
    pg.wait_for_timeout(150)
    ck("ZH paragraph (with the real mark) hidden in en-only mode", not zh2.is_visible())
    ck("echo dot still visible in en-only mode",
       block2.locator(".linked-note-dot").first.is_visible())

    # persistence across reload: both marks and both dots should come back
    pg.locator(".modes button").nth(0).click(); pg.wait_for_timeout(150)
    pg.reload(); pg.wait_for_timeout(500)
    ck("no JS errors after reload", not errs, errs)
    ck("first block's dot survives reload", block.locator(".linked-note-dot").count() == 1)
    ck("second block's dot survives reload", block2.locator(".linked-note-dot").count() == 1)
    ck("both exact marks survive reload",
       en.locator("mark.hl-anno").count() == 1 and zh2.locator("mark.hl-anno").count() == 1)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
