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
    ck("own-note banner shows when nothing is seeded", pg.locator("#ownNoteBanner").is_visible())
    ck("no .own-note blocks when nothing is seeded", pg.locator(".own-note").count() == 0)
    doc_a = pg.eval_on_selector('.paneDocSelect[data-side="A"]', 'el=>el.value')
    doc_b = pg.eval_on_selector('.paneDocSelect[data-side="B"]', 'el=>el.value')
    first_nid_a = pg.eval_on_selector('.pane[data-side="A"] .para[data-nid]', 'el=>el.dataset.nid')
    first_nid_b = pg.eval_on_selector('.pane[data-side="B"] .para[data-nid]', 'el=>el.dataset.nid')
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

    ck("banner gone once annotations are found", not pg.locator("#ownNoteBanner").is_visible())
    left_notes = pg.locator('.pane[data-side="A"] .own-note')
    right_notes = pg.locator('.pane[data-side="B"] .own-note')
    ck("left pane shows its own note", left_notes.count() == 1 and "这是左侧文献已有的批注" in left_notes.inner_text())
    ck("right pane shows its own highlight note", right_notes.count() == 1 and "这是右侧文献已有的高亮批注" in right_notes.inner_text())
    ck("own-note is labeled so it isn't confused with a cross-link", "已有批注" in left_notes.inner_text())

    # 3) switch pane A to the third paper (no seeded data for it) -> its own
    #    notes disappear from pane A, right pane's stay untouched, and the
    #    banner comes back (since A now has nothing to show).
    pg.locator('.paneDocSelect[data-side="A"]').select_option(label="Third (test)")
    pg.wait_for_timeout(200)
    ck("switching pane A clears its own-note display", pg.locator('.pane[data-side="A"] .own-note').count() == 0)
    ck("pane B's own-note is unaffected by pane A switching",
       pg.locator('.pane[data-side="B"] .own-note').count() == 1)

    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
