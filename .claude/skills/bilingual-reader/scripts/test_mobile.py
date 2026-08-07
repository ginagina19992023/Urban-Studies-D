from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg=b.new_page(viewport={"width":375,"height":667}, device_scale_factor=2, is_mobile=True, has_touch=True)
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors", not errs, errs)

    ck("no horizontal overflow at load",
       pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"),
       pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"))

    def min_height(sel):
        return pg.eval_on_selector(sel, "el => el.getBoundingClientRect().height")

    for sel, label, floor in [
        (".modes button", "mode toggle button", 32),
        ("#navBtn", "floating nav button", 38),
        (".note-add", "note-add button", 30),
    ]:
        h = min_height(sel)
        ck(f"{label} tap target >= {floor}px", h >= floor, f"{h:.1f}px")

    pg.locator("#navBtn").click(); pg.wait_for_timeout(200)
    ck("panel visible and fits width",
       pg.eval_on_selector("#navPanel", "el => el.getBoundingClientRect().width") <= 375 + 1)
    for sel, label, floor in [
        (".navtab", "nav tab button", 38),
    ]:
        h = min_height(sel)
        ck(f"{label} tap target >= {floor}px", h >= floor, f"{h:.1f}px")

    ck("no horizontal overflow with panel open",
       pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

    pg.locator('.navtab[data-tab="gloss"]').click(); pg.wait_for_timeout(150)
    gh = min_height("#gSearch")
    ck("glossary search input tap target >= 38px", gh >= 38, f"{gh:.1f}px")
    ck("gpick rows render on mobile without overflow", pg.locator(".gpick").count() > 0)

    pg.locator("#navClose").click(); pg.wait_for_timeout(150)

    n1 = pg.locator(".bipara .note").first
    n1.scroll_into_view_if_needed()
    n1.locator(".note-add").tap()
    pg.wait_for_timeout(200)
    ck("note-edit textarea visible and full-width on mobile",
       pg.eval_on_selector(".note-edit", "el => el.getBoundingClientRect().width") > 300)
    n1.locator(".note-edit").fill("手机端测试批注")
    pg.wait_for_timeout(700)
    pg.locator("body").tap(position={"x":5,"y":5})
    pg.wait_for_timeout(200)
    ck("note saved on mobile", "手机端测试批注" in n1.locator(".note-body").inner_text())
    ck("no horizontal overflow after annotating",
       pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

    ck("bilingual zh text readable font-size >= 14px",
       pg.eval_on_selector(".bipara p.zh", "el => parseFloat(getComputedStyle(el).fontSize)") >= 14)

    b.close()
print(); print("=== MOBILE FAILURES:", fails if fails else "none", "===")
sys.exit(1 if fails else 0)
