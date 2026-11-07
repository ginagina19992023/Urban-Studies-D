from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width":1400, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    ck("目录/标签 switch starts on 目录", pg.locator('.sb-switch-btn[data-pane="toc"]').evaluate(
        "el => el.classList.contains('active')"))
    ck("TOC pane visible by default", pg.locator('.sb-pane[data-pane="toc"]').is_visible())
    ck("tags pane hidden by default", not pg.locator('.sb-pane[data-pane="tags"]').is_visible())
    ck("tag directory starts with the empty state",
       "还没有标签" in pg.locator("#sbTagList").inner_text())

    # write a note with two tags
    first = pg.locator(".note").first
    first.locator(".note-add").click()
    first.locator(".note-edit").fill("第一条批注")
    first.locator(".note-tags").fill("重要 待查")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(300)

    # switch to the 标签 pane
    pg.locator('.sb-switch-btn[data-pane="tags"]').click()
    pg.wait_for_timeout(150)
    ck("switching tabs activates 标签 and deactivates 目录",
       pg.locator('.sb-switch-btn[data-pane="tags"]').evaluate("el => el.classList.contains('active')")
       and not pg.locator('.sb-switch-btn[data-pane="toc"]').evaluate("el => el.classList.contains('active')"))
    ck("TOC pane now hidden", not pg.locator('.sb-pane[data-pane="toc"]').is_visible())
    ck("tags pane now visible", pg.locator('.sb-pane[data-pane="tags"]').is_visible())
    ck("tag directory lists both tags", pg.locator("#sbTagList .sb-tag-row").count() == 2)
    ck("each tag row shows a count", "1" in pg.locator("#sbTagList").inner_text())

    # add a SECOND note reusing one of the same tags, to check counts aggregate
    q = pg.locator("blockquote.cited .note").first
    q.locator(".note-add").click()
    q.locator(".note-edit").fill("第二条批注")
    q.locator(".note-tags").fill("重要")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(300)
    ck("tag directory still lists exactly 2 distinct tags (no duplicates)",
       pg.locator("#sbTagList .sb-tag-row").count() == 2)
    important_row = pg.locator("#sbTagList .sb-tag-row", has_text="#重要")
    ck("the shared tag's count reflects both notes", important_row.locator(".count").inner_text() == "2")

    # clicking a tag row in the directory toggles the SAME shared filter as
    # the tag chips elsewhere (sidebar/nav/overview)
    important_row.click()
    pg.wait_for_timeout(200)
    ck("clicking a tag-directory row marks it active", important_row.evaluate(
        "el => el.classList.contains('active')"))
    ck("the shared filter narrows the annotations sidebar too",
       pg.locator("#nsList .ns-row").count() == 2)
    important_row.click()
    pg.wait_for_timeout(200)
    ck("clicking it again clears the filter", pg.locator("#nsList .ns-row").count() == 2
       and not important_row.evaluate("el => el.classList.contains('active')"))

    # tag autocomplete: previously-used tags are offered via the shared datalist
    datalist_values = pg.eval_on_selector_all("#tagOptions option", "els => els.map(e => e.value)")
    ck("datalist is populated with every distinct tag used so far",
       set(datalist_values) == {"重要", "待查"}, datalist_values)
    ck(".note-tags inputs are wired to the shared datalist",
       pg.locator(".note-tags").first.get_attribute("list") == "tagOptions")
    ck("#hlTags is wired to the same shared datalist",
       pg.locator("#hlTags").get_attribute("list") == "tagOptions")

    # the switch choice persists across reload
    pg.locator('.sb-switch-btn[data-pane="tags"]').click()
    pg.wait_for_timeout(100)
    pg.reload(); pg.wait_for_timeout(400)
    ck("标签 pane choice persists across reload",
       pg.locator('.sb-pane[data-pane="tags"]').is_visible())
    ck("tag directory still correct after reload", pg.locator("#sbTagList .sb-tag-row").count() == 2)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
