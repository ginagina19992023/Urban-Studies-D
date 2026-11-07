from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

AI_ANSWER = "这段在论证社会混合政策的隐藏预设。这条批注没有误读，抓得很准。"

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context(permissions=["clipboard-read", "clipboard-write"], viewport={"width":1400, "height":900})
    pg = ctx.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    # ---- paragraph note ----
    first = pg.locator(".note").first
    first.locator(".note-add").click()
    first.locator(".note-edit").fill("这段是不是在暗示混合本身就有预设？")
    ck(".note-ai textarea is visible while editing", first.locator(".note-ai").is_visible())
    first.locator(".note-ai").fill(AI_ANSWER)
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(300)

    ck("note shows a distinct AI-note block after saving", first.locator(".ai-note").count() == 1)
    ck("AI-note block is labeled, not mixed into the reader's own text",
       "AI 备注" in first.locator(".ai-note-lbl").inner_text())
    ck("AI-note block contains the pasted answer", AI_ANSWER in first.locator(".ai-note").inner_text())
    ck("the reader's own note text is still shown separately",
       "这段是不是在暗示混合本身就有预设？" in first.locator(".note-body").inner_text())

    # editing again repopulates the AI-note textarea (not just the main one)
    first.locator(".note-body").click()
    pg.wait_for_timeout(200)
    ck("re-opening the editor repopulates the AI-note field",
       first.locator(".note-ai").input_value() == AI_ANSWER)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(300)

    # reload: persists through localStorage like the rest of the note
    pg.reload(); pg.wait_for_timeout(400)
    first2 = pg.locator(".note").first
    ck("AI-note survives reload", AI_ANSWER in first2.locator(".ai-note").inner_text())

    # exports include it
    pg.locator("#navBtn").click(); pg.wait_for_timeout(150)
    pg.locator('.navtab[data-tab="notes"]').click(); pg.wait_for_timeout(150)
    pg.locator("#navCopyMd").click(); pg.wait_for_timeout(300)
    md = pg.evaluate("navigator.clipboard.readText()")
    ck("markdown export includes an AI 备注 line", "AI 备注："+AI_ANSWER in md, md[:400])
    pg.locator("#navReview").click(); pg.wait_for_timeout(300)
    review = pg.evaluate("navigator.clipboard.readText()")
    ck("review prompt includes the AI 备注 under its own label",
       "【此前的 AI 备注】"+AI_ANSWER in review, review[:600])
    pg.locator("#navClose").click(); pg.wait_for_timeout(200)

    # ---- highlight ----
    en = pg.locator(".bipara").nth(5).locator("p.en")
    pg.evaluate("""(el) => {
        var range = document.createRange();
        range.selectNodeContents(el);
        var sel = window.getSelection();
        sel.removeAllRanges(); sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""", en.element_handle())
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click(); pg.wait_for_timeout(150)
    pg.locator("#hlNote").fill("这段高亮批注")
    ck("#hlAiNote textarea is visible in the card", pg.locator("#hlAiNote").is_visible())
    pg.locator("#hlAiNote").fill(AI_ANSWER)
    pg.locator("#hlSave").click(); pg.wait_for_timeout(300)

    sidebar_ai = pg.locator("#nsList .ns-row .ai-note").first
    ck("highlight also shows an AI-note block in the sidebar list", sidebar_ai.count() >= 1)

    # re-opening the same highlight (via sidebar edit) repopulates #hlAiNote
    pg.locator("#nsList .ns-row .ns-edit").last.click()
    pg.wait_for_timeout(200)
    ck("re-opening a highlight repopulates #hlAiNote", pg.locator("#hlAiNote").input_value() == AI_ANSWER)
    pg.keyboard.press("Escape")

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
