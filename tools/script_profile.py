#!/usr/bin/env python3
"""CLI for the script/charset profile. The analysis lives in tradecraft/script_profile.py.

Moved into the package 2026-09-03 so `grade_text` and `grade_subject` can attach a script
profile to every document and subject they score (T3.5). A package importing from tools/ would
be backwards, and this profiler is now part of the read rather than a side utility.

    python tools/script_profile.py FILE [FILE ...]
    python tools/script_profile.py --text "some text to profile"
    python tools/script_profile.py FILE --json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.script_profile import profile  # noqa: E402


def render(name, p):
    print("== %s" % name)
    print("   letters %d, %d script(s), dominant %s"
          % (p["letters"], p["script_count"], p["dominant_script"]))
    for s, share in list(p["scripts"].items())[:6]:
        print("      %-12s %5.1f%%" % (s, 100 * share))
    if p["diacritic_rate"]:
        print("   diacritic rate %.3f" % p["diacritic_rate"])
    if p["mixed_script_total"]:
        print("   MIXED SCRIPT: %d word(s) -- receipts:" % p["mixed_script_total"])
        for e in p["mixed_script_words"][:6]:
            print("      %r at %d  %s" % (e["word"], e["offset"], "+".join(e["scripts"])))
    if p["confusable_total"]:
        print("   CONFUSABLES (Latin look-alikes): %d word(s)" % p["confusable_total"])
        for e in p["confusable_words"][:6]:
            print("      %r at %d  %s" % (e["word"], e["offset"],
                                          ", ".join(e["latin_lookalikes"])))
    if p["invisibles"]:
        print("   INVISIBLE/BIDI CHARACTERS:")
        for k, v in sorted(p["invisibles"].items()):
            print("      %-38s %d" % (k, v))
    if not (p["mixed_script_total"] or p["invisibles"]):
        print("   no mixed-script or invisible-character findings")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", help="files or globs to profile")
    ap.add_argument("--text", help="profile this string instead of files")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    items = []
    if args.text:
        items.append(("--text", args.text))
    for pat in args.paths:
        for path in sorted(glob.glob(pat)) or ([pat] if os.path.exists(pat) else []):
            with open(path, encoding="utf-8", errors="replace") as fh:
                items.append((os.path.basename(path), fh.read()))
    if not items:
        print("nothing to profile: pass a file, a glob, or --text")
        return 1

    out = {name: profile(text) for name, text in items}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    for name, p in out.items():
        render(name, p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
