"""CI gate: the browser engine must reproduce the Python detector exactly.

Runs the exported fixtures through engine.js under node and compares against the
values Python computed. This is the check that makes the no-hand-copied-vocabulary
design real rather than aspirational -- without it, "engine.js mirrors detect.py" is
just a comment.
"""
import json, os, subprocess, sys
from pathlib import Path

SERIES = Path(os.environ.get("SERIES_ROOT") or Path(__file__).resolve().parents[2])
D = SERIES / "website" / "static" / "tech" / "instrument"


def test_engine_parity():
    payload = D / "instrument.json"
    engine = D / "engine.js"
    assert payload.exists(), "run tradecraft/tools/export_web.py first"
    script = (
        "global.window=undefined;"
        f"require({json.dumps(str(engine))});"
        f"const p=JSON.parse(require('fs').readFileSync({json.dumps(str(payload))},'utf8'));"
        "const r=globalThis.Instrument.selfTest(p);"
        "process.stdout.write(JSON.stringify({pass:r.pass,total:r.total,"
        "fails:r.fails.slice(0,5)}));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr[:400]
    r = json.loads(out.stdout)
    assert r["total"] > 0, "no fixtures exported"
    assert r["pass"] == r["total"], f"engine drift: {r['pass']}/{r['total']}; {r['fails']}"


def test_engine_mechanism_parity():
    """Engine SEMANTICS parity, on synthetic taxonomies rather than real lenses.

    This exists because the lens-fixture gate above passed over a real divergence. Cue
    exclusions went into detect.py and not into engine.js, and no exported fixture exercised
    them -- the only lens with an `excludes` entry was in LLM_ONLY, which the web engine does
    not run. Word boundaries, suffix absorption and exclusion windows belong to the engine, so
    they get fixtures that do not depend on which lenses happen to be cues-capable.
    """
    payload = D / "instrument.json"
    engine = D / "engine.js"
    assert payload.exists(), "run tradecraft/tools/export_web.py first"
    script = (
        "global.window=undefined;"
        f"require({json.dumps(str(engine))});"
        f"const p=JSON.parse(require('fs').readFileSync({json.dumps(str(payload))},'utf8'));"
        "const r=globalThis.Instrument.mechanismTest(p);"
        "process.stdout.write(JSON.stringify({pass:r.pass,total:r.total,"
        "fails:r.fails.slice(0,5)}));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr[:400]
    r = json.loads(out.stdout)
    assert r["total"] >= 5, ("no mechanism fixtures exported -- re-run export_web.py; without "
                             "them an engine feature can be added on one side only and this "
                             "gate stays green")
    assert r["pass"] == r["total"], f"mechanism drift: {r['pass']}/{r['total']}; {r['fails']}"


TRADECRAFT_WEB = SERIES / "tradecraft" / "web"
SITE_JS = SERIES / "website" / "static" / "tech" / "tradecraft" / "tradecraft.js"
SITE_LAYOUT = SERIES / "website" / "layouts" / "tech" / "tradecraft.html"


def test_tradecraft_page_uses_the_engine():
    """The second front-end must not carry a second grader.

    Until 2026-09-07 /tech/tradecraft/ shipped its own grade() over its own inline LENSES
    snapshot, extracted by a second exporter -- outside this gate, skipping word boundaries
    and cue exclusions, and scoring five lenses their taxonomies declare not cue-matchable.
    Two browser graders is the README's named bug. This asserts the page's JS has no grading
    of its own and calls window.Instrument, and that the layout loads engine.js before it.
    """
    js = SITE_JS.read_text(encoding="utf-8")
    assert "function grade" not in js, "tradecraft.js carries its own grader"
    assert "LENSES =" not in js and "const LENSES" not in js, "tradecraft.js carries a vocabulary snapshot"
    assert "Instrument.runAll" in js and "Instrument.selfTest" in js, "tradecraft.js does not call the engine"
    layout = SITE_LAYOUT.read_text(encoding="utf-8")
    e = layout.find("/tech/instrument/engine.js")
    t = layout.find("/tech/tradecraft/tradecraft.js")
    assert e >= 0 and t >= 0 and e < t, "layout must load engine.js before tradecraft.js"
    assert "crosstab.json" in layout, "the 'Method, not ideology -- checked' cross-tab is missing again"


def test_standalone_demo_embeds_the_same_engine_and_payload():
    """web/demo.html inlines engine.js and instrument.json so it runs offline. Both must be
    byte-identical to what the site serves, or the standalone demo becomes the drifted copy."""
    demo = (TRADECRAFT_WEB / "demo.html").read_text(encoding="utf-8")
    engine = (D / "engine.js").read_text(encoding="utf-8").rstrip("\n")
    assert engine in demo, "demo.html does not embed engine.js verbatim"
    ui = (TRADECRAFT_WEB / "ui.js").read_text(encoding="utf-8").rstrip("\n")
    assert ui in demo, "demo.html does not embed web/ui.js verbatim"
    assert SITE_JS.read_text(encoding="utf-8").rstrip("\n") == ui, "site tradecraft.js is not web/ui.js"
    m = __import__("re").search(r"window\.TRADECRAFT_PAYLOAD = (\{.*?\});\n</script>", demo, __import__("re").S)
    assert m, "demo.html has no inline payload"
    embedded = json.loads(m.group(1).replace("<\\/", "</"))
    shipped = json.loads((D / "instrument.json").read_text(encoding="utf-8"))
    assert embedded == shipped, "demo.html's inline payload differs from instrument.json"


def test_generated_front_end_is_current():
    """build-demo.py --check: every generated file (demo.html, tradecraft.js/css, the layout)
    matches a fresh render from its sources. A hand edit to any of them fails here."""
    r = subprocess.run([sys.executable, str(TRADECRAFT_WEB / "build-demo.py"), "--check"],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, (r.stdout + r.stderr)[:600]


if __name__ == "__main__":
    test_engine_parity()
    test_engine_mechanism_parity()
    test_tradecraft_page_uses_the_engine()
    test_standalone_demo_embeds_the_same_engine_and_payload()
    test_generated_front_end_is_current()
    print("engine parity OK (lens fixtures + mechanism + tradecraft page on the same engine)")
