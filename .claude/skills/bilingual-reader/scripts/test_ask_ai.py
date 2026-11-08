from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context(permissions=["clipboard-read", "clipboard-write"], viewport={"width":1400, "height":900})
    pg = ctx.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    first = pg.locator(".note").first
    host = first.locator("xpath=ancestor::*[contains(@class,'bipara')]")
    en_text = host.locator("p.en").inner_text()
    zh_text = host.locator("p.zh").inner_text()
    first.locator(".note-add").click()
    first.locator(".note-edit").fill("这段真的是在反驳这个观点吗？")
    first.locator(".note-tags").fill("追问")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(300)

    # sidebar (compact icon) variant
    ask_btn = pg.locator("#nsList .ns-row .ns-ask").first
    ck("sidebar ns-row gets a compact AI-ask icon button", ask_btn.count() == 1)
    ask_btn.click()
    pg.wait_for_timeout(300)
    clip = pg.evaluate("navigator.clipboard.readText()")
    ck("clicking it copies a prompt treating the note as a question",
       "当作一个问题" in clip, clip[:200])
    ck("prompt includes the note's own text", "这段真的是在反驳这个观点吗？" in clip)
    ck("prompt includes the EN source passage", en_text[:30] in clip)
    ck("prompt includes the ZH translation", zh_text[:30] in clip)
    ck("prompt includes the note's tag", "追问" in clip)
    ck("icon button briefly flashes a checkmark", ask_btn.inner_text() in ("✓", "💬"))

    # nav 批注 tab (wide, labeled) variant — opening the nav panel, then
    # switching to its 批注 tab, where #notesList actually lives
    pg.locator("#navBtn").click()
    pg.wait_for_timeout(150)
    pg.locator('.navtab[data-tab="notes"]').click()
    pg.wait_for_timeout(150)
    nav_ask = pg.locator("#notesList .nrow .ask-ai-btn").first
    ck("nav 批注 tab row gets a labeled AI-ask button", nav_ask.count() == 1)
    ck("labeled button shows the full label, not just an icon",
       "AI 解读" in nav_ask.inner_text())
    nav_ask.click()
    pg.wait_for_timeout(300)
    clip2 = pg.evaluate("navigator.clipboard.readText()")
    ck("nav variant copies the same kind of per-note prompt",
       "当作一个问题" in clip2 and "这段真的是在反驳这个观点吗？" in clip2)
    ck("labeled button shows a confirmation then reverts",
       nav_ask.inner_text() in ("✓ 已复制", "💬 AI 解读"))

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
