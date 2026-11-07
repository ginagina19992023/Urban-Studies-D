from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("comparative-reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

    # 1) nothing seeded -> the "couldn't read" banner should show
    pg = b.new_page(viewport={"width":1400, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors", not errs, errs)
    # (checking the rendered DOM via a locator, not pg.content(): the raw
    # page source also contains this Chinese string as a JS literal inside
    # the <script> tag, so a content()-substring check would always pass)
    ck("own-note banner shows when nothing is seeded",
       pg.locator("div:has-text('未读取到')").count() > 0)
    ck("no .own-note blocks when nothing is seeded", pg.locator(".own-note").count() == 0)
    doc_a = pg.evaluate("window.__CR_DOC_A")
    doc_b = pg.evaluate("window.__CR_DOC_B")
    first_nid_a = pg.eval_on_selector('.pane >> nth=0 >> .para[data-nid]', 'el=>el.dataset.nid')
    first_nid_b = pg.eval_on_selector('.pane >> nth=1 >> .para[data-nid]', 'el=>el.dataset.nid')
    pg.close()

    # 2) seed br-notes / br-highlights exactly as the single-document pages
    #    would, for a paragraph on EACH side, then reload -> both show up,
    #    attached to the correct side's correct paragraph, and the "can't
    #    read" banner is gone.
    pg = b.new_page(viewport={"width":1400, "height":900})
    pg.goto(url)
    pg.evaluate("""([docA, docB, nidA, nidB]) => {
        localStorage.setItem('br-notes:'+docA, JSON.stringify({[nidA]: {text:'这是左侧文献已有的批注', tags:[], aiNote:''}}));
        localStorage.setItem('br-highlights:'+docB, JSON.stringify([
          {id:'h1', frags:[{nid:nidB, lang:'en', text:'x'}], note:'这是右侧文献已有的高亮批注'}
        ]));
    }""", [doc_a, doc_b, first_nid_a, first_nid_b])
    pg.reload()
    pg.wait_for_timeout(200)

    ck("banner gone once annotations are found",
       pg.locator("div:has-text('未读取到')").count() == 0)
    left_notes = pg.locator(".pane").nth(0).locator(".own-note")
    right_notes = pg.locator(".pane").nth(1).locator(".own-note")
    ck("left pane shows its own note", left_notes.count() == 1 and "这是左侧文献已有的批注" in left_notes.inner_text())
    ck("right pane shows its own highlight note", right_notes.count() == 1 and "这是右侧文献已有的高亮批注" in right_notes.inner_text())
    ck("own-note is labeled so it isn't confused with a cross-link", "已有批注" in left_notes.inner_text())

    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
