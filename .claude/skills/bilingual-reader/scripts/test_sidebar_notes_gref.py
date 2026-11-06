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

    # ---- annotations sidebar: same >=1040px breakpoint as the TOC sidebar ----
    pg = b.new_page(viewport={"width":1000, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors (1000px)", not errs, errs)
    ck("both sidebars hidden below 1040px",
       not pg.locator("#noteSidebar").is_visible() and not pg.locator("#tocSidebar").is_visible())
    pg.close()

    pg = b.new_page(viewport={"width":1040, "height":900})
    errs1b=[]; pg.on("pageerror", lambda e: errs1b.append(str(e)))
    pg.goto(url)
    ck("no JS errors (1040px)", not errs1b, errs1b)
    ck("both sidebars visible at exactly 1040px",
       pg.locator("#noteSidebar").is_visible() and pg.locator("#tocSidebar").is_visible())
    ck("no horizontal overflow at 1040px with both sidebars",
       pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    main_w = pg.eval_on_selector("main", "el => el.getBoundingClientRect().width")
    ck("main column still a reasonable reading width at 1040px", main_w >= 480, main_w)
    pg.close()

    pg = b.new_page(viewport={"width":1400, "height":900})
    errs2=[]; pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.goto(url)
    ck("no JS errors (1400px)", not errs2, errs2)
    ck("note sidebar visible at 1400px", pg.locator("#noteSidebar").is_visible())
    ck("note sidebar empty-state shown initially", "还没有批注" in pg.locator("#nsList").inner_text())

    # write a plain paragraph note, confirm it shows up in the sidebar
    first = pg.locator(".note").first
    first.locator(".note-add").click()
    first.locator(".note-edit").fill("侧栏联动测试批注")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5,"y":5})
    pg.wait_for_timeout(300)
    ck("sidebar lists the paragraph note", "侧栏联动测试批注" in pg.locator("#nsList").inner_text())

    # add a selection-anchored highlight note too, confirm it also shows up
    p_en = pg.locator(".bipara p.en").nth(3)
    select_text_in(pg, p_en)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("侧栏联动测试选段批注")
    pg.locator("#hlSave").click()
    pg.wait_for_timeout(300)
    ck("sidebar lists the highlight note too", "侧栏联动测试选段批注" in pg.locator("#nsList").inner_text())
    ck("sidebar has 2 rows", pg.locator(".ns-row").count() == 2, pg.locator(".ns-row").count())

    # the highlight row's edit button opens the floating card WITHOUT scrolling
    before_scroll = pg.evaluate("window.scrollY")
    hl_row = pg.locator(".ns-row", has_text="侧栏联动测试选段批注")
    hl_row.locator(".ns-edit").click()
    pg.wait_for_timeout(200)
    after_scroll = pg.evaluate("window.scrollY")
    ck("edit button opens card", pg.locator("#selCard").is_visible())
    ck("edit button does not scroll the page", before_scroll == after_scroll,
       (before_scroll, after_scroll))
    pg.locator("#hlCancel").click(); pg.wait_for_timeout(150)

    # the quote line (not the edit button) scrolls to the paragraph instead
    hl_row.locator(".ns-q").click()
    pg.wait_for_timeout(1000)
    moved = pg.evaluate("window.scrollY") != before_scroll
    ck("clicking the quote jumps (scrolls) instead", moved)
    ck("card not opened by a quote-line jump", not pg.locator("#selCard").is_visible())

    ck("no JS errors overall (sidebar page)", not errs2, errs2)
    pg.close()

    # ---- glossary term popover (a.gref) ----
    pg2 = b.new_page(viewport={"width":1000, "height":900})
    errs3=[]; pg2.on("pageerror", lambda e: errs3.append(str(e)))
    pg2.goto(url)
    gref = pg2.locator("a.gref").first
    gref_term_href = gref.get_attribute("href")
    before_scroll2 = pg2.evaluate("window.scrollY")
    gref.click()
    pg2.wait_for_timeout(200)
    ck("popover opens on gref click", pg2.locator("#grefPop").is_visible())
    ck("page does not jump/scroll on gref click",
       pg2.evaluate("window.scrollY") == before_scroll2)
    ck("popover shows a term", pg2.locator("#grefPop .gp-term").inner_text().strip() != "")
    ck("popover has a definition body", pg2.locator("#grefPop .gp-def").inner_text().strip() != "")
    ck("popover offers a jump-to-glossary escape hatch", pg2.locator("#grefPop .gp-jump").count() == 1)

    # Escape closes it
    pg2.keyboard.press("Escape")
    pg2.wait_for_timeout(150)
    ck("Escape closes the popover", not pg2.locator("#grefPop").is_visible())

    # the escape-hatch link still does the old jump-to-glossary-and-flash behavior
    gref.click(); pg2.wait_for_timeout(200)
    pg2.locator("#grefPop .gp-jump").click()
    pg2.wait_for_timeout(1800)
    target_id = gref_term_href.lstrip("#")
    ck("jump link scrolls to the glossary entry",
       abs(pg2.eval_on_selector(f"#{target_id}", "el => el.getBoundingClientRect().top")) < 400)
    ck("popover closed after using the jump link", not pg2.locator("#grefPop").is_visible())

    # clicking outside closes an open popover without following any link
    gref.click(); pg2.wait_for_timeout(200)
    pg2.locator("body").click(position={"x":5, "y":5})
    pg2.wait_for_timeout(150)
    ck("clicking elsewhere closes the popover", not pg2.locator("#grefPop").is_visible())

    ck("no JS errors overall (gref page)", not errs3, errs3)
    pg2.close()

    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
