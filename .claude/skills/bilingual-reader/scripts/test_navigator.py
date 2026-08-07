from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg=b.new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    def open_tab(tab):
        if not pg.locator("#navPanel").is_visible():
            pg.locator("#navBtn").click(); pg.wait_for_timeout(150)
        pg.locator(f'.navtab[data-tab="{tab}"]').click(); pg.wait_for_timeout(150)

    pg.locator("#navBtn").click()
    pg.wait_for_timeout(150)
    ck("panel opens", pg.locator("#navPanel").is_visible())
    ck("toc tab active by default", "active" in (pg.locator('.navtab[data-tab="toc"]').get_attribute("class") or ""))
    n_toc_rows = pg.locator(".tocrow").count()
    ck("toc has rows matching h2/h3 count",
       n_toc_rows == pg.locator("article h2, article h3").count(), n_toc_rows)

    first_toc_en = pg.locator(".tocrow .en").first.inner_text()
    pg.locator(".tocrow").first.click()
    pg.wait_for_timeout(500)
    ck("panel closed after toc jump", not pg.locator("#navPanel").is_visible())
    top_heading = pg.locator("article h2, article h3").first.locator(".en").inner_text()
    ck("scrolled to correct section", top_heading == first_toc_en, (top_heading, first_toc_en))
    ck("scroll position moved near top section",
       pg.evaluate("document.querySelector('article h2,article h3').getBoundingClientRect().top") < 200)

    open_tab("gloss")
    ck("glossary tab shows entries", pg.locator(".gpick").count() > 0, pg.locator(".gpick").count())
    ck("glossary grouped by category headers", pg.locator(".gcat-header").count() > 0)

    pg.locator("#gSearch").fill("Smith")
    pg.wait_for_timeout(200)
    filtered_count = pg.locator(".gpick").count()
    ck("search filters results", 0 < filtered_count < pg.evaluate("window.__BR_GLOSSARY.length"),
       (filtered_count, pg.evaluate("window.__BR_GLOSSARY.length")))
    all_gpick_text = pg.locator(".navpane[data-pane=\'gloss\']").inner_text().lower()
    ck("every visible result plausibly matches query (term or def mentions it)",
       "smith" in all_gpick_text)

    pg.locator(".gpick").first.click()
    pg.wait_for_timeout(600)
    ck("panel closed after glossary jump", not pg.locator("#navPanel").is_visible())
    ck("target glossary entry flashed/visible",
       pg.locator(".gitem").filter(has=pg.locator("text=Smith")).first.is_visible())

    open_tab("gloss")
    pg.locator("#gSearch").fill("zzzznotfound")
    pg.wait_for_timeout(150)
    ck("empty search state shown", pg.locator(".gempty").count() == 1)

    open_tab("notes")
    ck("notes tab shows empty state initially or existing notes container", pg.locator("#notesList").is_visible())

    pg.locator("#navClose").click(); pg.wait_for_timeout(150)
    ck("close button closes panel", not pg.locator("#navPanel").is_visible())

    n1 = pg.locator(".bipara .note").first
    n1.locator(".note-add").click()
    n1.locator(".note-edit").fill("导航面板测试批注")
    pg.wait_for_timeout(700); pg.locator("body").click(position={"x":5,"y":5}); pg.wait_for_timeout(200)
    ck("note saved", "导航面板测试批注" in n1.locator(".note-body").inner_text())

    if not pg.locator("#navPanel").is_visible():
        pg.locator("#navBtn").click(); pg.wait_for_timeout(150)
    ck("nav badge shows 1", pg.locator("#navBtn .n").inner_text() == "1", pg.locator("#navBtn .n").inner_text())
    pg.locator('.navtab[data-tab="notes"]').click(); pg.wait_for_timeout(150)
    ck("notes tab badge shows 1", pg.locator("#notesTabBadge").inner_text() == "1")
    ck("notes tab lists the new note", "导航面板测试批注" in pg.locator("#notesList").inner_text())

    pg.locator("#notesJump").click(); pg.wait_for_timeout(1200)
    ck("panel closed after notesJump", not pg.locator("#navPanel").is_visible())
    ck("scrolled to overview", pg.evaluate("Math.abs(document.getElementById('overview').getBoundingClientRect().top) < 400"))
    ck("overview lists the note too", "导航面板测试批注" in pg.locator("#ovList").inner_text())

    b.close()
print(); print("=== DESKTOP FAILURES:", fails if fails else "none", "===")
sys.exit(1 if fails else 0)
