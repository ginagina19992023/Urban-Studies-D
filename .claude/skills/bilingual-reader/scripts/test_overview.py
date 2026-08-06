from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx=b.new_context(permissions=["clipboard-read","clipboard-write"])
    pg=ctx.new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors", not errs, errs)

    ov=pg.locator("#overview")
    ck("overview exists at end of doc", ov.count()==1)
    ck("overview empty-state shown", "还没有批注" in pg.locator("#ovList").inner_text())
    ck("download buttons hidden (no capability in file://)",
       not pg.locator("#ovSaveMd").is_visible())

    # write two notes
    n1=pg.locator(".bipara .note").first
    n1.locator(".note-add").click()
    n1.locator(".note-edit").fill("空间邻近≠社会混合，这是全篇最可迁移的一句。")
    pg.wait_for_timeout(700); pg.locator("body").click(position={"x":5,"y":5}); pg.wait_for_timeout(200)

    q=pg.locator("blockquote.cited .note").first
    q.locator(".note-add").click()
    q.locator(".note-edit").fill("水蛭退烧——Waterloo 可直接引")
    pg.wait_for_timeout(700); pg.locator("body").click(position={"x":5,"y":5}); pg.wait_for_timeout(300)

    ck("overview lists 2 rows", pg.locator("#ovList .nrow").count()==2,
       pg.locator("#ovList .nrow").count())
    ck("overview marks quote row", "［引文］" in pg.locator("#ovList").inner_text())
    ck("overview shows note text", "水蛭退烧" in pg.locator("#ovList").inner_text())

    # AI review prompt
    pg.locator("#ovReview").click(); pg.wait_for_timeout(500)
    clip=pg.evaluate("navigator.clipboard.readText()")
    ck("prompt has 3 instructions",
       all(k in clip for k in ["【1. 提炼】","【2. 评价】","【3. 建议】"]))
    ck("prompt warns about misreading rebutted views", "误当成了作者本人立场" in clip)
    ck("prompt includes both notes",
       "空间邻近" in clip and "水蛭退烧" in clip)
    ck("prompt includes source EN", "Social mix policies fail" in clip)
    ck("prompt includes ZH translation", "【译文】" in clip)
    ck("prompt includes citation", "Urban Studies" in clip)
    ck("prompt marks quote entry", "（针对引文）" in clip)
    ck("prompt states note count", "批注条数：2" in clip)
    ck("button feedback shown", "已复制" in pg.locator("#ovReview").inner_text(),
       pg.locator("#ovReview").inner_text())

    # markdown export
    pg.locator("#ovCopy").click(); pg.wait_for_timeout(400)
    md=pg.evaluate("navigator.clipboard.readText()")
    ck("markdown has blockquote form", md.count("> ")>=2, md[:120])
    ck("markdown has separators", md.count("---")>=2)

    # drawer jump
    pg.locator("#notesBtn").click(); pg.wait_for_timeout(200)
    ck("drawer lists 2 rows", pg.locator("#notesList .nrow").count()==2)
    pg.locator("#notesJump").click(); pg.wait_for_timeout(600)
    ck("drawer closed after jump", not pg.locator("#notesPanel").is_visible())
    ck("scrolled to overview",
       pg.evaluate("Math.abs(document.getElementById('overview').getBoundingClientRect().top) < 250"))

    # empty guard
    pg.on("dialog", lambda d: d.accept())
    pg.locator("#ovClear").click(); pg.wait_for_timeout(400)
    ck("cleared -> empty state", "还没有批注" in pg.locator("#ovList").inner_text())
    ck("badge back to 0", pg.locator("#notesBtn .n").inner_text()=="0")
    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
