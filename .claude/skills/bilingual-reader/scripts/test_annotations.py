from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ")+name+(" :: "+str(extra) if extra and not cond else ""))
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS runtime errors on load", not errs, errs)

    first = pg.locator(".note").first
    ck("edit box hidden initially", not first.locator(".note-edit").is_visible())
    ck("add button visible", first.locator(".note-add").is_visible())

    first.locator(".note-add").click()
    ck("edit box shown after click", first.locator(".note-edit").is_visible())

    first.locator(".note-edit").fill("这段是社会混合的核心预设——空间邻近≠社会混合。")
    pg.wait_for_timeout(800)
    ck("status flashed 已保存", "已保存" in first.locator(".note-status").inner_text(),
       first.locator(".note-status").inner_text())

    pg.locator("body").click(position={"x":5,"y":5})
    pg.wait_for_timeout(200)
    ck("note-body visible after blur", first.locator(".note-body").is_visible())
    ck("note-body shows text", "空间邻近" in first.locator(".note-body").inner_text())
    ck("has 我的批注 label", "我的批注" in first.locator(".note-body").inner_text())
    ck("badge count = 1", pg.locator("#notesBtn .n").inner_text()=="1",
       pg.locator("#notesBtn .n").inner_text())

    # second note on a quote block
    q = pg.locator("blockquote.cited .note").first
    q.locator(".note-add").click()
    q.locator(".note-edit").fill("水蛭退烧——可直接引用")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5,"y":5})
    pg.wait_for_timeout(200)
    ck("badge count = 2", pg.locator("#notesBtn .n").inner_text()=="2",
       pg.locator("#notesBtn .n").inner_text())

    # drawer
    pg.locator("#notesBtn").click()
    pg.wait_for_timeout(250)
    ck("panel opens", pg.locator("#notesPanel").is_visible())
    ck("panel lists 2 rows", pg.locator("#notesList .nrow").count()==2, pg.locator("#notesList .nrow").count())
    ck("panel shows note text", "空间邻近" in pg.locator("#notesList").inner_text())
    ck("panel shows source quote", "Social mix policies fail" in pg.locator("#notesList").inner_text())

    pg.locator("#notesClose").click(); pg.wait_for_timeout(200)
    ck("panel closes", not pg.locator("#notesPanel").is_visible())

    # persistence across reload
    pg.reload(); pg.wait_for_timeout(400)
    ck("no JS errors after reload", not errs, errs)
    ck("note survives reload", "空间邻近" in pg.locator(".note").first.locator(".note-body").inner_text())
    ck("badge survives reload", pg.locator("#notesBtn .n").inner_text()=="2")

    # mode toggle still works with notes present
    pg.locator(".modes button").nth(2).click(); pg.wait_for_timeout(150)
    ck("zh-only mode hides EN", not pg.locator(".bipara p.en").first.is_visible())
    ck("notes stay visible in zh-only", pg.locator(".note").first.locator(".note-body").is_visible())

    b.close()
print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
