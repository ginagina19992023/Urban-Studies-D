from playwright.sync_api import sync_playwright
import pathlib, sys
url = "file://" + str(pathlib.Path("lees_reading.html").resolve())
fails=[]
def ck(n,c,x=""):
    print(("  PASS " if c else "  FAIL ")+n+((" :: "+str(x)) if x and not c else ""))
    if not c: fails.append(n)

def select_phrase_in(pg, locator, phrase):
    full = locator.inner_text()
    idx = full.find(phrase)
    assert idx != -1, "phrase not found in paragraph: " + phrase
    return pg.evaluate("""([el, idx, len]) => {
        var tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        var node, total=0, startNode, startOff;
        while(node = tw.nextNode()){
          var l = node.nodeValue.length;
          if(total + l > idx){ startNode = node; startOff = idx - total; break; }
          total += l;
        }
        var range = document.createRange();
        range.setStart(startNode, startOff);
        range.setEnd(startNode, startOff + len);
        var sel = window.getSelection();
        sel.removeAllRanges(); sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
        return range.toString();
    }""", [locator.element_handle(), idx, len(phrase)])

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width":1000, "height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    ck("no JS errors on load", not errs, errs)

    # Real report: selecting the EN phrase that the translator independently
    # marked with quotes in ZH ("poverty deconcentration" <-> “贫困去集中化”)
    # used to produce a ZH underline straddling the CLOSING quote mark
    # instead ("化”命题所设想"), because the fraction-based sentence-position
    # estimate just missed the translator-reordered term. The quote marks
    # the translator already placed are a better anchor than the guess.
    bq = pg.locator("blockquote.cited", has_text="poverty deconcentration")
    en_p = bq.locator("p.en")
    sel = select_phrase_in(pg, en_p, "poverty deconcentration")
    ck("selected the exact EN phrase", sel == "poverty deconcentration", sel)
    pg.wait_for_timeout(250)
    pg.locator("#selPill").click()
    pg.wait_for_timeout(250)
    pg.locator("#hlNote").fill("quote-snap regression test")
    pg.locator("#hlSave").click()
    pg.wait_for_timeout(250)

    zh_p = bq.locator("p.zh")
    underline = zh_p.locator("span.linked-underline")
    ck("exactly one linked-underline span", underline.count() == 1, underline.count())
    ck("underline lands exactly on the quoted term, not neighbouring text",
       underline.inner_text() == "贫困去集中化", underline.inner_text())
    ck("underline does not bleed past the closing quote into 命题所设想",
       "命题" not in underline.inner_text())
    ck("underline does not start inside the preceding word (承诺/集中)",
       "集中" not in underline.inner_text() or underline.inner_text()=="贫困去集中化")

    ck("no JS errors overall", not errs, errs)
    b.close()
print(); print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
