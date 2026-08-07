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

    n1 = pg.locator(".bipara .note").first
    n1.locator(".note-add").click()
    n1.locator(".note-edit").fill("快捷路径测试批注")
    pg.wait_for_timeout(700); pg.locator("body").click(position={"x":5,"y":5}); pg.wait_for_timeout(200)

    # exactly two taps: open nav, click 批注 tab (default view already shows toc, need to switch)
    pg.locator("#navBtn").click(); pg.wait_for_timeout(150)
    pg.locator('.navtab[data-tab="notes"]').click(); pg.wait_for_timeout(150)

    ck("hint text visible in notes tab", "无法直接调用 AI" in pg.locator("#notesHint").inner_text())
    ck("AI review button reachable directly in notes tab", pg.locator("#navReview").is_visible())
    ck("copy-md button reachable directly in notes tab", pg.locator("#navCopyMd").is_visible())

    pg.locator("#navReview").click(); pg.wait_for_timeout(400)
    clip = pg.evaluate("navigator.clipboard.readText()")
    ck("fast-path review prompt contains the note", "快捷路径测试批注" in clip)
    ck("fast-path review prompt has 3-part instruction",
       all(k in clip for k in ["【1. 提炼】","【2. 评价】","【3. 建议】"]))
    ck("button shows copied feedback", "已复制" in pg.locator("#navReview").inner_text())

    pg.locator("#navCopyMd").click(); pg.wait_for_timeout(400)
    md = pg.evaluate("navigator.clipboard.readText()")
    ck("fast-path markdown export contains the note", "快捷路径测试批注" in md)

    # jump-to-overview link for the remaining tools (export file / clear) still works
    pg.locator("#notesJump").click(); pg.wait_for_timeout(1200)
    ck("jump-to-overview still works from notes tab", not pg.locator("#navPanel").is_visible())
    ck("landed near overview", pg.evaluate("Math.abs(document.getElementById('overview').getBoundingClientRect().top) < 400"))

    b.close()
print(); print("=== FAST-PATH:", fails if fails else "none", "===")
sys.exit(1 if fails else 0)
