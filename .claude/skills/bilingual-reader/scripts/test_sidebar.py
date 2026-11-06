from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    pg=b.new_page(viewport={"width":1600,"height":1000})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors (wide)", not errs, errs)
    ck("sidebar visible at 1600px", pg.locator("#tocSidebar").is_visible())
    n_nodes = pg.locator(".sb-node").count()
    n_headings = pg.locator("article h2, article h3").count()
    ck("sidebar node count matches h2/h3 count", n_nodes == n_headings, (n_nodes, n_headings))

    href = pg.locator(".sb-node").nth(3).get_attribute("href")
    target_id = href.lstrip("#")
    pg.locator(".sb-node").nth(3).click()
    pg.wait_for_timeout(1200)
    top = pg.eval_on_selector(f"#{target_id}", "el => el.getBoundingClientRect().top")
    ck("clicking sidebar node scrolls target to top of viewport", abs(top) < 150, top)

    pg.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4)")
    pg.wait_for_timeout(600)
    active_count = pg.locator(".sb-node.active").count()
    ck("scroll-spy marks exactly one active node", active_count == 1, active_count)

    zh_weight = pg.eval_on_selector(".bipara p.zh", "el => getComputedStyle(el).fontWeight")
    zh_color = pg.eval_on_selector(".bipara p.zh", "el => getComputedStyle(el).color")
    en_color = pg.eval_on_selector(".bipara p.en", "el => getComputedStyle(el).color")
    ck("zh paragraph font-weight is bold (600/700)", zh_weight in ("600","700"), zh_weight)
    ck("zh paragraph color darker/different than en color", zh_color != en_color, (zh_color, en_color))
    zh_font = pg.eval_on_selector(".bipara p.zh", "el => getComputedStyle(el).fontFamily")
    ck("zh font-family leads with a sans (heiti-style) font", "Songti" not in zh_font.split(",")[0], zh_font)
    pg.close()

    pg2 = b.new_page(viewport={"width":900,"height":900})
    errs2=[]; pg2.on("pageerror", lambda e: errs2.append(str(e)))
    pg2.goto(url)
    ck("no JS errors (narrow desktop)", not errs2, errs2)
    ck("sidebar hidden below the 1040px breakpoint", not pg2.locator("#tocSidebar").is_visible())
    pg2.locator("#navBtn").click(); pg2.wait_for_timeout(150)
    ck("nav panel still opens on narrow viewport", pg2.locator("#navPanel").is_visible())
    ck("nav panel toc tab still has matching rows",
       pg2.locator(".tocrow").count() == n_headings, pg2.locator(".tocrow").count())
    pg2.close()

    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
