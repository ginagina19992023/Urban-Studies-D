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

    ck("tag layer switch starts off", pg.locator('#tagLayerToggle').get_attribute("aria-pressed") == "false")
    ck("TOC tree visible by default", pg.locator('.sb-tree').is_visible())
    ck("tag overlay hidden by default", not pg.locator('#sbTagOverlay').is_visible())
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

    # flip the tag-layer switch: it overlays on top of the tree, doesn't replace it
    pg.locator('#tagLayerToggle').click()
    pg.wait_for_timeout(150)
    ck("switch shows pressed state once on", pg.locator('#tagLayerToggle').get_attribute("aria-pressed") == "true")
    ck("TOC tree stays in the DOM underneath (a layer, not a swap)", pg.locator('.sb-tree').count() == 1)
    ck("tag overlay now visible on top of the tree", pg.locator('#sbTagOverlay').is_visible())
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

    # the switch choice persists across reload (it's already on from above)
    pg.reload(); pg.wait_for_timeout(400)
    ck("tag layer choice persists across reload",
       pg.locator('#tagLayerToggle').get_attribute("aria-pressed") == "true"
       and pg.locator('#sbTagOverlay').is_visible())
    ck("tag directory still correct after reload", pg.locator("#sbTagList .sb-tag-row").count() == 2)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
