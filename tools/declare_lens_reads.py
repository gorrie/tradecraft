#!/usr/bin/env python3
"""One-shot: give every taxonomy an explicit `reads:` and `cue_matching:` declaration.

WHY
---
`eval/gold_check.py` carries this comment above a hardcoded set:

    # This list is derived by reading structural.py. It belongs in each taxonomy as a "reads"
    # field; until that exists, it lives here where the check can see it.

It existed in three places, not one: `gold_check.py` and `tools/harvest_gold.py` each hold
their own `STRUCTURAL = {...}`, and `tools/export_web.py` holds `LLM_ONLY = {...}`. Three
files deciding what a lens can do, none of them the lens.

That is not a tidiness complaint. **The parity blind spot found on 2026-09-01 had `LLM_ONLY` as
its root cause**: cue exclusions were added to `detect.py` and not to `engine.js`, and
`test_engine_parity` stayed green because the only lens carrying an `excludes` entry happened
to be in `LLM_ONLY`, so no exported fixture exercised the feature. A capability list living
away from the thing it describes silently decided what got tested.

WHAT IT WRITES
--------------
Two top-level fields per taxonomy, inserted textually after `id:` so the hand-written comments
and formatting in these files are not touched. yaml.dump would have reflowed all sixteen and
dropped every comment in them.

    reads: text | graph          -- prose, or the career/funding graph via structural.py
    cue_matching: supported | unsupported
                                 -- whether literal cue matching can judge these markers at all

Values are taken from the CURRENT behaviour of the three lists, deliberately unchanged. This
script moves the facts; it does not revise them.

    python tools/declare_lens_reads.py --check    # report, write nothing
    python tools/declare_lens_reads.py
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Verbatim from the three lists this replaces, at the moment of replacement.
GRAPH = {"revolving_door", "network_brokerage"}
CUE_UNSUPPORTED = {"cognitive_capture", "legibility", "counterproductivity",
                   "distributed_accountability", "inevitability_framing"}

NOTE = {
    "graph": "reads the career/funding graph via structural.py, not prose",
    "text": "reads prose",
    "unsupported": ("literal cue matching cannot judge these markers; the UI greys the lens "
                    "out rather than reporting a misleading 0"),
    "supported": "cue matching is a valid floor backend for these markers",
}


def declare(path, lens_id, check):
    text = io.open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    body = text.replace("\r\n", "\n")
    if "\nreads:" in body or body.startswith("reads:"):
        return "already declared"

    reads = "graph" if lens_id in GRAPH else "text"
    cue = "unsupported" if lens_id in CUE_UNSUPPORTED else "supported"
    block = (
        "# Capability declaration. Moved here 2026-09-01 from three hardcoded sets in\n"
        "# eval/gold_check.py, tools/harvest_gold.py and tools/export_web.py -- one of which\n"
        "# silently decided which engine features got parity-tested. A lens declares what it\n"
        "# can do; tools ask the lens.\n"
        "reads: %s               # %s\n"
        "cue_matching: %s        # %s\n"
    ) % (reads, NOTE[reads], cue, NOTE[cue])

    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("id:"):
            out = "\n".join(lines[:i + 1]) + "\n" + block + "\n".join(lines[i + 1:])
            break
    else:
        return "NO id: LINE -- skipped"

    if not check:
        io.open(path, "w", encoding="utf-8", newline="").write(out.replace("\n", nl))
    return "reads=%s cue_matching=%s" % (reads, cue)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    paths = sorted(glob.glob(os.path.join(ROOT, "detectors", "*", "taxonomy.yaml")))
    missing = 0
    for path in paths:
        lens_id = os.path.basename(os.path.dirname(path))
        status = declare(path, lens_id, args.check)
        if status != "already declared":
            missing += 1
        print("%-30s %s" % (lens_id, status))
    print()
    print("%d taxonomy file(s); %d %s" %
          (len(paths), missing, "would change" if args.check else "changed"))
    if args.check and missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
