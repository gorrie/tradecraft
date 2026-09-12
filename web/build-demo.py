#!/usr/bin/env python
"""Assemble the standalone Tradecraft demo (web/demo.html) from ONE engine, ONE payload, ONE UI.

What it assembles, and where each piece comes from
--------------------------------------------------
    web/demo.template.html   page chrome with {{CSS}} {{ENGINE}} {{PAYLOAD}} {{UI}} slots
    web/demo.css             the demo's stylesheet
    web/ui.js                the UI -- renders results, grades nothing
    website/static/tech/instrument/engine.js      the browser detector (mirrors detect.py / grader.py)
    website/static/tech/instrument/instrument.json the taxonomy payload export_web.py emits

demo.html is therefore a GENERATED file, and so are the site's copies
(website/static/tech/tradecraft/{tradecraft.js,tradecraft.css}, layouts/tech/tradecraft.html),
which web/split_for_site.py writes from the same sources. `--check` regenerates everything in
memory and exits 1 if any on-disk copy differs; tools/freshness_gate.py runs it.

Why it changed on 2026-09-07
----------------------------
Until then this script re-extracted the cues from detectors/*/taxonomy.yaml into an inline
`const LENSES = [...]` snapshot, and demo.html carried its own `grade()`. That was a SECOND
browser grader beside instrument/engine.js, with a second exporter feeding it: it skipped word
boundaries, ignored cue exclusions, scored the five lenses whose taxonomies declare
`cue_matching` unusable, and sat outside `tools/test_engine_parity.py`. README.md's "The bug
that made the parity check non-negotiable" describes exactly that shape. The demo also shipped
an unterminated string literal from 2026-07-04 to 2026-09-06 because nothing parsed it.

Now there is nothing here to drift. The payload is the one export_web.py produces (gated by
`instrument-export`), the engine is the one the parity test executes, and the UI is one file
used verbatim by both the standalone demo and the site page.

    python web/build-demo.py            # write demo.html + the site split
    python web/build-demo.py --check    # exit 1 if any generated file is stale
"""
from __future__ import annotations

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                        # tradecraft/
SERIES = os.path.dirname(ROOT)                      # series-workspace/
INSTRUMENT = os.path.join(SERIES, "website", "static", "tech", "instrument")

TEMPLATE = os.path.join(HERE, "demo.template.html")
CSS = os.path.join(HERE, "demo.css")
UI = os.path.join(HERE, "ui.js")
ENGINE = os.path.join(INSTRUMENT, "engine.js")
PAYLOAD = os.path.join(INSTRUMENT, "instrument.json")
DEMO = os.path.join(HERE, "demo.html")


def read(path):
    if not os.path.isfile(path):
        sys.exit("missing %s%s" % (os.path.relpath(path, SERIES),
                 " -- run tradecraft/tools/export_web.py first" if path == PAYLOAD else ""))
    return io.open(path, encoding="utf-8").read()


def render_demo():
    """Return demo.html's content as a string. Pure: reads sources, writes nothing."""
    payload = json.loads(read(PAYLOAD))
    # Compact, and `</` escaped so a taxonomy string can never close the <script> tag. In
    # JSON `<\/` is a legal escape for `/`, so the browser parses the identical object.
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = read(TEMPLATE)
    for slot, text in (("{{CSS}}", read(CSS).rstrip("\n")),
                       ("{{ENGINE}}", read(ENGINE).rstrip("\n")),
                       ("{{PAYLOAD}}", data),
                       ("{{UI}}", read(UI).rstrip("\n"))):
        if slot not in out:
            sys.exit("demo.template.html has no %s slot" % slot)
        # str.replace, never re.sub: a regex replacement string processes backslash escapes,
        # which is how `\n` inside JSON strings became real newlines and broke the old demo.
        out = out.replace(slot, text, 1)
    for slot in ("{{CSS}}", "{{ENGINE}}", "{{PAYLOAD}}", "{{UI}}"):
        if slot in out:
            sys.exit("slot %s still present after rendering" % slot)
    return out


def stale(path, want):
    have = io.open(path, encoding="utf-8").read() if os.path.isfile(path) else None
    return have != want


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv

    sys.path.insert(0, HERE)
    import split_for_site  # noqa: E402  (sibling module)

    demo = render_demo()
    site = split_for_site.render()      # {abs_path: content}

    if check:
        bad = [os.path.relpath(p, SERIES) for p, want in [(DEMO, demo)] + sorted(site.items())
               if stale(p, want)]
        if bad:
            print("STALE -- re-run tradecraft/web/build-demo.py:\n  " + "\n  ".join(bad))
            return 1
        print("demo.html and the site split are current (%d files)" % (1 + len(site)))
        return 0

    io.open(DEMO, "w", encoding="utf-8", newline="\n").write(demo)
    n_tax = len(json.loads(read(PAYLOAD))["taxonomies"])
    print("wrote %s (%d bytes, %d lenses in payload)" % (os.path.relpath(DEMO, SERIES), len(demo), n_tax))
    split_for_site.write(site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
