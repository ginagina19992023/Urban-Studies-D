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
    pg.locator("#hlNote").fill("英文侧批注，测试中文侧对应划线")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)

    ck("exact mark lands in the EN paragraph (the language actually selected)",
       en.locator("mark.hl-anno").count() == 1)
    ck("EN paragraph itself does not get the cross-language underline (it already has the real mark)",
       "has-linked-note" not in (en.get_attribute("class") or ""))
    ck("ZH sibling paragraph gets the has-linked-note class",
       "has-linked-note" in (zh.get_attribute("class") or ""))
    ck("underline is actually rendered on the ZH paragraph",
       pg.eval_on_selector(".has-linked-note", "el => getComputedStyle(el).textDecorationLine") == "underline")
    ck("no separate marker element is added (visual cue only, via CSS class)",
       pg.locator(".linked-note-dot").count() == 0)

    # the underline must survive switching to 中文-only mode, where the EN
    # paragraph (and its real <mark>) gets display:none
    pg.locator(".modes button").nth(2).click()  # 中文 button
    pg.wait_for_timeout(150)
    ck("EN paragraph (and its mark) hidden in zh-only mode", not en.is_visible())
    ck("ZH underline still applied in zh-only mode",
       "has-linked-note" in (zh.get_attribute("class") or ""))
    ck("ZH underline still visible in zh-only mode", zh.is_visible())

    # back to bilingual, class still correct, no duplicate marks after a repaint cycle
    pg.locator(".modes button").nth(0).click()
    pg.wait_for_timeout(150)
    ck("back in bilingual mode: ZH still has the class, exactly once",
       zh.evaluate("el => el.classList.contains('has-linked-note')"))
    ck("still exactly one real mark in EN", en.locator("mark.hl-anno").count() == 1)

    # editing the SAME highlight (via the sidebar, since there's no longer a
    # click target on the paragraph itself) shouldn't duplicate anything
    pg.locator(".ns-row .ns-edit").first.click()
    pg.wait_for_timeout(200)
    ck("sidebar edit button still opens the card", pg.locator("#selCard").is_visible())
    pg.locator("#hlNote").fill("英文侧批注，测试中文侧对应划线（已编辑）")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("editing the same highlight keeps exactly one ZH underline",
       zh.evaluate("el => el.classList.contains('has-linked-note')")
       and en.locator("mark.hl-anno").count() == 1)

    # now highlight a phrase on the ZH side of a DIFFERENT block -> EN side gets underlined
    block2 = pg.locator(".bipara").nth(4)
    zh2 = block2.locator("p.zh")
    en2 = block2.locator("p.en")
    select_text_in(pg, zh2)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("中文侧批注，测试英文侧对应划线")
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)
    ck("exact mark lands in the ZH paragraph this time", zh2.locator("mark.hl-anno").count() == 1)
    ck("EN sibling (not ZH) gets the underline this time",
       "has-linked-note" in (en2.get_attribute("class") or "")
       and "has-linked-note" not in (zh2.get_attribute("class") or ""))

    pg.locator(".modes button").nth(1).click()  # EN-only button
    pg.wait_for_timeout(150)
    ck("ZH paragraph (with the real mark) hidden in en-only mode", not zh2.is_visible())
    ck("EN underline still visible in en-only mode",
       en2.is_visible() and "has-linked-note" in (en2.get_attribute("class") or ""))

    # persistence across reload: both marks and both underlines should come back
    pg.locator(".modes button").nth(0).click(); pg.wait_for_timeout(150)
    pg.reload(); pg.wait_for_timeout(500)
    ck("no JS errors after reload", not errs, errs)
    ck("first block's ZH underline survives reload",
       "has-linked-note" in (zh.get_attribute("class") or ""))
    ck("second block's EN underline survives reload",
       "has-linked-note" in (en2.get_attribute("class") or ""))
    ck("both exact marks survive reload",
       en.locator("mark.hl-anno").count() == 1 and zh2.locator("mark.hl-anno").count() == 1)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
