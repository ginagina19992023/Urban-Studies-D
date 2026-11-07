from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # ---- below the 1320px breakpoint: the column is an enhancement, not a
    # dependency -- it should simply not appear, with no JS errors. ----
    pg_narrow = b.new_page(viewport={"width":1200, "height":900})
    errs_narrow=[]; pg_narrow.on("pageerror", lambda e: errs_narrow.append(str(e)))
    pg_narrow.goto(url)
    ck("no JS errors on load (narrow)", not errs_narrow, errs_narrow)
    ck("AI summary column hidden below 1320px", not pg_narrow.locator("#aiSidebar").is_visible())
    pg_narrow.close()

    # ---- wide viewport: the real behavior ----
    pg = b.new_page(viewport={"width":1500, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load (wide)", not errs, errs)
    ck("AI summary column visible at >=1320px", pg.locator("#aiSidebar").is_visible())

    blocks = pg.locator(".ai-sum-block")
    ck("at least one AI-summary block is rendered", blocks.count() > 0, blocks.count())
    first_block = blocks.first
    ck("each block carries a distinct label", "AI 总结" in first_block.locator(".ai-sum-lbl").inner_text())

    # ---- flow (default) mode: tracks the paragraph's own position ----
    ck("snap toggle starts off", pg.locator("#aiSnapToggle").get_attribute("aria-pressed") == "false")
    first_nid = first_block.get_attribute("data-nid")
    host = pg.locator(f'.note[data-nid="{first_nid}"]').locator(
        "xpath=ancestor::*[contains(@class,'bipara') or self::blockquote][1]")
    host_top = host.bounding_box()["y"]
    block_top = first_block.bounding_box()["y"]
    ck("in flow mode the summary block sits near its paragraph's own vertical position",
       abs(host_top - block_top) < 40, (host_top, block_top))

    # scroll the page and confirm the block follows (non-sticky, moves with page)
    pg.mouse.wheel(0, 800)
    pg.wait_for_timeout(300)
    host_top2 = host.bounding_box()["y"]
    block_top2 = first_block.bounding_box()["y"]
    ck("after scrolling, the summary block still tracks its paragraph (not sticky)",
       abs(host_top2 - block_top2) < 40, (host_top2, block_top2))
    pg.mouse.wheel(0, -800)
    pg.wait_for_timeout(200)

    # ---- snap mode: aligns to the matching #nsList row's span ----
    first = pg.locator(".note").first
    first.locator(".note-add").click()
    first.locator(".note-edit").fill("第一条批注，用于测试吸附对齐")
    pg.wait_for_timeout(700)
    pg.locator("body").click(position={"x":5, "y":5})
    pg.wait_for_timeout(300)

    first_note_nid = pg.locator(".note").first.get_attribute("data-nid")
    has_summary_for_first_note = first_note_nid in [blocks.nth(i).get_attribute("data-nid") for i in range(blocks.count())]

    pg.locator("#aiSnapToggle").click()
    pg.wait_for_timeout(300)
    ck("snap toggle shows pressed state", pg.locator("#aiSnapToggle").get_attribute("aria-pressed") == "true")

    if has_summary_for_first_note:
        matching_block = pg.locator(f'.ai-sum-block[data-nid="{first_note_nid}"]')
        matching_row = pg.locator(f'#nsList .ns-row[data-nid="{first_note_nid}"]')
        ck("in snap mode, the matching summary block is visible", matching_block.is_visible())
        block_box = matching_block.bounding_box()
        row_box = matching_row.bounding_box()
        ck("snapped block's top aligns with its ns-row's top",
           abs(block_box["y"] - row_box["y"]) < 3, (block_box["y"], row_box["y"]))
        ck("snapped block's height covers at least the ns-row's own height",
           block_box["height"] >= row_box["height"] - 1, (block_box["height"], row_box["height"]))
    else:
        print("  (skip: the first paragraph's own block has no AI summary in this fixture)")

    # a paragraph with a summary but NO annotation should be hidden in snap mode
    unannotated = None
    for i in range(blocks.count()):
        nidv = blocks.nth(i).get_attribute("data-nid")
        if pg.locator(f'#nsList .ns-row[data-nid="{nidv}"]').count() == 0:
            unannotated = nidv
            break
    if unannotated:
        ck("a summary block with no matching annotation is hidden in snap mode",
           not pg.locator(f'.ai-sum-block[data-nid="{unannotated}"]').is_visible())

    # toggle back off: reverts to flow positioning
    pg.locator("#aiSnapToggle").click()
    pg.wait_for_timeout(300)
    ck("toggling off reverts to flow mode (block tracks paragraph again)",
       abs(host.bounding_box()["y"] - first_block.bounding_box()["y"]) < 40)

    # persistence across reload
    pg.locator("#aiSnapToggle").click()
    pg.wait_for_timeout(200)
    pg.reload(); pg.wait_for_timeout(500)
    ck("snap choice persists across reload", pg.locator("#aiSnapToggle").get_attribute("aria-pressed") == "true")

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
