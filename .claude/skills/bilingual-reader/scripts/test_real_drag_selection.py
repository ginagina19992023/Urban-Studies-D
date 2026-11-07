from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def drag_select(pg, x1, y1, x2, y2):
    pg.mouse.move(x1, y1)
    pg.mouse.down()
    pg.mouse.move(x2, y2, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(300)

def force_cross_paragraph_selection(pg, start_el, end_el):
    """Deterministically reproduces the overshoot bug: a Range that starts in
    one paragraph's text and ends in a DIFFERENT (sibling) paragraph's text —
    precisely what a real mouse drag produces when it spills a few pixels
    past the end of a line. Built directly via the Range API instead of
    relying on exact font-metrics/pixel geometry, which real mouse drags
    depend on and which isn't reliably reproducible from one environment or
    font-rendering pass to the next."""
    pg.evaluate("""([a, b]) => {
        var range = document.createRange();
        var startNode = a.firstChild;
        while (startNode && startNode.nodeType !== 3) startNode = startNode.firstChild;
        var endNode = b.firstChild;
        while (endNode && endNode.nodeType !== 3) endNode = endNode.firstChild;
        range.setStart(startNode, 2);
        range.setEnd(endNode, Math.min(10, endNode.nodeValue.length));
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""", [start_el, end_el])

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width":1400, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    # This reproduces the real bug report deterministically: a selection
    # whose raw Range starts in p.en's text and ends in the sibling p.zh's
    # text (exactly what a real mouse drag produces when it spills a few
    # pixels past the end of a wrapped line — p.en and p.zh sit close
    # together). That used to make validSelection() reject the WHOLE
    # selection outright, so the "+ 批注" pill never appeared at all.
    block = pg.locator(".bipara").nth(2)
    en = block.locator("p.en")
    zh = block.locator("p.zh")
    force_cross_paragraph_selection(pg, en.element_handle(), zh.element_handle())
    pg.wait_for_timeout(250)

    raw_sel = pg.evaluate("window.getSelection().toString()")
    ck("sanity: the raw selection actually spans into ZH (reproduces the bug precondition)",
       any("一" <= ch <= "鿿" for ch in raw_sel), raw_sel)

    ck("pill appears despite the raw selection overshooting into ZH", pg.locator("#selPill").is_visible())
    pg.locator("#selPill").click()
    pg.wait_for_timeout(150)
    ck("card opens", pg.locator("#selCard").is_visible())
    frag_text = pg.locator("#hlFrags").inner_text()
    ck("clipped fragment text contains no Chinese characters",
       not any("一" <= ch <= "鿿" for ch in frag_text), frag_text)
    ck("clipped fragment text is non-trivial (actually captured the EN text)", len(frag_text.strip()) > 10)

    pg.locator("#hlNote").fill("真实鼠标拖拽选区测试")
    pg.locator("#hlSave").click()
    pg.wait_for_timeout(300)
    ck("mark lands only in the EN paragraph", en.locator("mark.hl-anno").count() == 1)
    ck("ZH sibling paragraph got no stray mark from the overshoot",
       block.locator("p.zh mark.hl-anno").count() == 0)
    ck("ZH sibling got the cross-language underline instead (correct indicator)",
       "has-linked-note" in (block.locator("p.zh").get_attribute("class") or ""))

    # genuine mouse-drag smoke test (not a synthetic Range) over a fresh
    # paragraph, scrolled into view first so the drag coordinates are real
    # on-screen viewport coordinates — using an off-screen bounding_box()
    # coordinate for a raw mouse drag makes Chromium auto-scroll mid-drag to
    # follow the cursor, which is a real browser behavior but corrupts any
    # coordinates computed before the drag for unrelated reasons; it isn't
    # something this feature's logic needs to special-case.
    block2 = pg.locator(".bipara").nth(6)
    en2 = block2.locator("p.en")
    en2.scroll_into_view_if_needed()
    box2 = en2.bounding_box()
    drag_select(pg, box2["x"]+10, box2["y"]+10, box2["x"]+box2["width"]-10, box2["y"]+10)
    sel2 = pg.evaluate("window.getSelection().toString()")
    ck("genuine mouse drag on a fresh paragraph shows the pill",
       pg.locator("#selPill").is_visible(), sel2)

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
