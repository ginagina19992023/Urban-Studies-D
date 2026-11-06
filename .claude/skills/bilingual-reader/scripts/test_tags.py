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
    ctx = b.new_context(permissions=["clipboard-read", "clipboard-write"], viewport={"width":1400, "height":900})
    pg = ctx.new_page()
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    # ---- paragraph note with tags ----
    first = pg.locator(".note").first
    first.locator(".note-add").click()
    active_is_textarea = pg.evaluate("document.activeElement === document.querySelector('.note.editing .note-edit')")
    ck("cursor lands directly in the textarea after clicking ＋批注 (no extra click needed)",
       active_is_textarea)
    first.locator(".note-edit").fill("关于空间邻近的核心论点")
    first.locator(".note-tags").fill("核心论点 可引用")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(200)
    ck("tag chips render in the note body", first.locator(".note-body .tag-chip").count() == 2)
    ck("chip text uses # prefix", "#核心论点" in first.locator(".note-body").inner_text())

    # tabbing from textarea to the tag field shouldn't collapse the editing UI
    first.locator(".note-add").count()  # no-op, button hidden once has note; re-open via body click
    first.locator(".note-body").click()
    pg.wait_for_timeout(150)
    ck("re-opening for edit shows both fields", first.locator(".note-edit").is_visible() and first.locator(".note-tags").is_visible())
    first.locator(".note-edit").focus()
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(50)
    ck("tabbing into the tag field keeps the editing UI open (no premature collapse)",
       first.locator(".note-tags").is_visible())
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(200)

    # ---- highlight note with tags ----
    p_en = pg.locator(".bipara p.en").nth(4)
    select_text_in(pg, p_en)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    active_is_hlnote = pg.evaluate("document.activeElement === document.getElementById('hlNote')")
    ck("cursor lands directly in the highlight card's textarea", active_is_hlnote)
    pg.locator("#hlNote").fill("选段也要能打标签")
    pg.locator("#hlTags").fill("待查")
    pg.locator("#hlSave").click()
    pg.wait_for_timeout(300)
    ck("sidebar row for the highlight shows its tag chip",
       pg.locator(".ns-row", has_text="选段也要能打标签").locator(".tag-chip").count() == 1)

    # ---- click-to-filter ----
    pg.locator(".ns-row .tag-chip", has_text="#待查").first.click()
    pg.wait_for_timeout(200)
    ck("sidebar shows the filter bar", pg.locator("#nsList .tag-filter-bar").count() == 1)
    ck("filtered sidebar shows only the matching row", pg.locator("#nsList .ns-row").count() == 1)
    ck("filtered row is the highlight note, not the unrelated paragraph note",
       "选段也要能打标签" in pg.locator("#nsList").inner_text()
       and "核心论点" not in pg.locator("#nsList").inner_text())

    # the nav panel's 批注 tab and the overview should also respect the same filter
    pg.locator("#navBtn").click(); pg.wait_for_timeout(200)
    pg.locator('.navtab[data-tab="notes"]').click(); pg.wait_for_timeout(150)
    ck("nav 批注 tab also shows the filter bar", pg.locator("#notesList .tag-filter-bar").count() == 1)
    ck("nav 批注 tab filtered to 1 row too", pg.locator("#notesList .nrow").count() == 1)
    pg.locator("#navClose").click(); pg.wait_for_timeout(150)

    # clearing the filter restores both rows everywhere
    pg.locator("#nsList .tag-filter-clear").click()
    pg.wait_for_timeout(200)
    ck("clearing the filter restores both rows in the sidebar", pg.locator("#nsList .ns-row").count() == 2)

    # ---- exports include tags, and respect an active filter ----
    pg.locator(".ns-row .tag-chip", has_text="#核心论点").first.click()
    pg.wait_for_timeout(200)
    pg.locator("#navBtn").click(); pg.wait_for_timeout(200)
    pg.locator('.navtab[data-tab="notes"]').click(); pg.wait_for_timeout(150)
    pg.locator("#navReview").click()
    pg.wait_for_timeout(400)
    clip = pg.evaluate("navigator.clipboard.readText()")
    ck("review prompt mentions the active filter", "仅包含标签 #核心论点" in clip, clip[:300])
    ck("review prompt includes the tag line for the matching note", "【标签】#核心论点 #可引用" in clip, clip)
    ck("review prompt excludes the non-matching highlight note when filtered",
       "选段也要能打标签" not in clip)

    # clear filter again, then check markdown export carries tags too
    pg.locator("#notesList .tag-filter-clear").click()
    pg.wait_for_timeout(200)
    pg.locator("#navCopyMd").click()
    pg.wait_for_timeout(400)
    md = pg.evaluate("navigator.clipboard.readText()")
    ck("markdown export includes a 标签 line", "标签：#核心论点 #可引用" in md, md[:400])

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
