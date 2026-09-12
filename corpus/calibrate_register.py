#!/usr/bin/env python
"""Measure the detector's firing rate on its TARGET register, before building a corpus.

WHY THIS RUNS FIRST

The corpus plan proposes 200 labelled documents (pilot 50) split `method` vs `control`, and
compares how hard each lens fires across the two classes. That design is only interpretable
if the lens fires often enough for a difference to be visible, and the one measured base
rate says it may not: `institutional_permeation` produces 16 cue hits across 371 PTC news
articles -- about 0.043 hits per document. At that rate the pilot's 25-document cells yield
roughly ONE hit each, and a 1-vs-3 table cannot separate "the lens does not discriminate"
from "there was never enough data". The whole fetch would buy an uninterpretable null.

The rate on the target register is a different number, and it is free: no labels, no model
calls, no judgement about any organisation. Federal Register rulemaking is public domain,
reachable without auth, and is the plan's own primary `control` source. So measure it, then
size the corpus from the measurement instead of from a round number.

WHAT IT REPORTS

  1. lambda per lens -- cue hits per document, at several window sizes. This is the number
     the corpus is sized from.
  2. CUE LIVENESS in-register -- how many of the taxonomy's 621 cues fire at least once.
     On PTC news only 58 do; 563 are silent. If they stay silent HERE, on the register
     these lenses were written for, then the vocabulary is inert rather than off-register,
     and the corpus question is moot until the taxonomy is repaired. That is a finding
     worth having for 25 documents rather than 200.
  3. The projected control-cell hit count at n=100, against a stated floor.

THE CALIBRATION SET IS BURNED ON PURPOSE

Every document fetched here is recorded in `calibration-set.json` and is EXCLUDED from the
eventual labelled corpus. Sizing a study on the same documents you then test with is how a
power calculation becomes a fishing licence. Committing the exclusion list before the
labelled fetch is what makes that checkable rather than asserted.

    python tradecraft/corpus/calibrate_register.py --fetch 20     # paced; writes cache
    python tradecraft/corpus/calibrate_register.py                # measure what is cached
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

CACHE = HERE / "_calibration-cache"
SETFILE = HERE / "calibration-set.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
API = ("https://www.federalregister.gov/api/v1/documents.json"
       "?per_page={n}&order=newest&fields[]=document_number&fields[]=title"
       "&fields[]=raw_text_url&fields[]=publication_date&conditions[type][]=RULE")

#: Seconds between requests. The plan's internet discipline: paced, serial, never blasting.
DELAY = 3.0

#: Window sizes to report lambda at, in words. The plan fixes 400; that choice predates any
#: measurement of the hit rate and is reported here beside the alternatives so the decision
#: is made on numbers. Density-per-1k noise is worst at SHORT windows, not long ones.
WINDOWS = (400, 1000, 2000)

#: Expected hits in the SMALLER cell for a rate-ratio contrast to have usable power. Below
#: this the study reports UNDERPOWERED rather than a null -- they are different findings and
#: conflating them is how a corpus gets blamed for an instrument's silence.
CONTROL_CELL_FLOOR = 10


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def strip_boilerplate(raw: str) -> str:
    """Federal Register .txt is an HTML-wrapped <pre> with a fixed masthead.

    The plan says "first 400 words after boilerplate" without defining boilerplate, which
    is not a procedure. This is: drop the HTML wrapper, drop the bracketed masthead lines
    ([Federal Register Volume ...], [Pages ...], [FR Doc No: ...]), and start at the first
    substantive line. Identical for every document, so it cannot differ between classes.
    """
    t = re.sub(r"(?is)<[^>]+>", "", raw)
    lines = t.split("\n")
    out, started = [], False
    for ln in lines:
        s = ln.strip()
        if not started:
            if not s or s.startswith("[") or s.startswith("From the Federal Register"):
                continue
            started = True
        out.append(ln)
    return "\n".join(out).strip()


def fetch(n: int) -> None:
    CACHE.mkdir(exist_ok=True)
    meta = json.loads(get(API.format(n=n)).decode("utf-8"))
    got = []
    for i, r in enumerate(meta.get("results", []), 1):
        num = r["document_number"]
        dest = CACHE / f"{num}.txt"
        if not dest.exists():
            time.sleep(DELAY)
            body = strip_boilerplate(get(r["raw_text_url"]).decode("utf-8", "replace"))
            dest.write_text(body, encoding="utf-8")
        got.append({"document_number": num, "title": r.get("title"),
                    "publication_date": r.get("publication_date"),
                    "raw_text_url": r.get("raw_text_url"),
                    "words": len(dest.read_text(encoding="utf-8").split())})
        print(f"  {i}/{n} {num} {got[-1]['words']:>6}w  {(r.get('title') or '')[:56]}")
    SETFILE.write_text(json.dumps({
        "purpose": ("Documents used to ESTIMATE hit rates and cue liveness before the "
                    "labelled corpus is built. Every document_number here is EXCLUDED from "
                    "the labelled corpus: sizing a study on the documents you then test "
                    "with turns a power calculation into a fishing licence. Committed "
                    "before the labelled fetch so the exclusion is checkable."),
        "source": "US Federal Register API, type=RULE, public domain, no auth",
        "documents": got,
    }, indent=1), encoding="utf-8", newline="\n")
    print(f"\nwrote {SETFILE.name} -- {len(got)} documents, EXCLUDED from the labelled corpus")


def measure() -> int:
    from tradecraft.detect import detect_cues
    from tradecraft.loader import load_lenses

    docs = sorted(CACHE.glob("*.txt")) if CACHE.is_dir() else []
    if not docs:
        print("no calibration documents cached -- run with --fetch N", file=sys.stderr)
        return 2
    texts = [p.read_text(encoding="utf-8", errors="replace") for p in docs]
    lenses = load_lenses(str(ROOT / "detectors"))

    all_cues = {(lid, c.lower()) for lid, t in lenses.items()
                for m in t.markers for d in m.detections for c in d.cues}
    live, rows = set(), []
    for lid, tax in sorted(lenses.items()):
        per_window = {}
        for w in WINDOWS:
            hits = 0
            for t in texts:
                seg = " ".join(t.split()[:w])
                try:
                    hs = detect_cues(seg, tax)
                except Exception:
                    hs = []
                hits += len(hs)
                for h in hs:
                    live.add((lid, h.span.lower()))
            per_window[w] = hits
        rows.append((lid, per_window))

    print(f"calibration: {len(docs)} Federal Register RULE documents "
          f"(median {sorted(len(t.split()) for t in texts)[len(texts)//2]:,} words)")
    print(f"floor for a usable contrast: {CONTROL_CELL_FLOOR} hits in the control cell "
          f"at n=100\n")
    hdr = "  ".join(f"{w}w".rjust(9) for w in WINDOWS)
    print(f"  {'lens':<28}{hdr}   {'proj. n=100 @' + str(WINDOWS[-1]) + 'w':>22}")
    for lid, pw in sorted(rows, key=lambda r: -r[1][WINDOWS[-1]]):
        cells = "  ".join(f"{pw[w]:>9}" for w in WINDOWS)
        lam = pw[WINDOWS[-1]] / len(docs)
        proj = lam * 100
        flag = "OK" if proj >= CONTROL_CELL_FLOOR else "UNDERPOWERED"
        print(f"  {lid:<28}{cells}   {proj:>10.0f} hits  {flag}")

    print(f"\ncue liveness on this register: {len(live)} of {len(all_cues)} cues fire "
          f"({len(live)/len(all_cues):.0%})")
    print("  PTC news, for comparison: 58 of 621 (9%)")
    print("  If liveness is no better HERE -- the register these lenses were written for --")
    print("  the vocabulary is inert rather than off-register, and taxonomy repair comes")
    print("  before any corpus verdict on whether a lens works.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", type=int, default=0, help="fetch N Federal Register RULEs")
    a = ap.parse_args(argv)
    if a.fetch:
        fetch(a.fetch)
    return measure()


if __name__ == "__main__":
    sys.exit(main())
