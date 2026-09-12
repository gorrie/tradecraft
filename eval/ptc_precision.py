#!/usr/bin/env python
"""Measure the detector against human span annotation, with chance as the baseline.

WHY

The detector's own eval is 51 positives and 32 negatives. That is a smoke test: it tells
you the cues fire on text written to make them fire, and it cannot tell you whether they
fire all over ordinary prose. Adding cues without a benchmark is how a detector silently
gets worse, so the benchmark comes first.

The Propaganda Techniques Corpus gives one. 446 news articles, 18 propaganda techniques,
annotated at CHARACTER-SPAN level by six professional annotators. So for every hit this
detector makes, we can ask whether it lands inside a span a human independently marked as
propaganda -- and, crucially, compare that to what landing there by chance looks like.

THE BASELINE IS THE POINT

"62% of our hits land in an annotated span" means nothing on its own. If 60% of the
corpus's characters are inside some annotation, 62% is chance. So the script computes the
annotated-character fraction per article and reports LIFT: hit-precision divided by the
chance rate. Lift near 1.0 means the lens is firing on ordinary prose; lift well above 1.0
means it is finding what humans found.

This is the same lesson the DISARM comparison taught the hard way: a rate without its own
baseline is not evidence.

THE CHANCE RATE HERE IS ONLY VALID FOR SHORT HITS (added 2026-08-27)

`chance` below is the fraction of corpus CHARACTERS inside some annotation. That is the
right baseline when every hit is a literal cue a few characters wide, which was true of
every stage this script has ever scored. It is BADLY WRONG for any stage whose hits are
long: a 350-character window overlaps an annotation by luck far more often than an
8-character keyword does, so scoring both against one character-level rate hands the
long-span stage a large free lift.

Measured: an embedding find stage scored 5.13 "lift" here and 1.22 against a length-matched
null -- essentially chance. The entire apparent advantage was span length.

So: do not use this script to compare stages with different hit lengths. Use
`eval/compare_find_stages.py`, which drops a span of the SAME length at a random offset in
the SAME document and measures how often that hits an annotation.

WHAT IT IS NOT

PTC annotates *propaganda techniques in news articles*. This taxonomy names *institutional
and rhetorical method*, which is a different and broader thing. A lens scoring at chance
here is not thereby worthless -- it may be detecting something PTC does not annotate. What
low lift does establish is that the lens cannot claim support from this corpus, and that
its cues are not distinguishing propaganda-dense prose from ordinary reporting. Read it as
a floor, not a verdict.

    python tradecraft/eval/ptc_precision.py            # every lens
    python tradecraft/eval/ptc_precision.py --lens institutional_permeation
    python tradecraft/eval/ptc_precision.py --json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # tradecraft/
SERIES = ROOT.parent
sys.path.insert(0, str(ROOT))

PTC = SERIES / "research" / "external" / "ptc"
ARTICLES = PTC / "train-articles"
LABELS = PTC / "train-labels-task1-span-identification"
TC_LABELS = PTC / "train-labels-task2-technique-classification"


def load_corpus() -> list[dict]:
    if not ARTICLES.is_dir():
        sys.exit(f"missing {ARTICLES}\n"
                 f"PTC (CC-BY-4.0) is not vendored. See research/external/ptc/README-USE.md")
    out = []
    for art in sorted(ARTICLES.glob("article*.txt")):
        aid = art.stem.replace("article", "")
        lab = LABELS / f"article{aid}.task1-SI.labels"
        spans = []
        if lab.is_file():
            for line in lab.read_text(encoding="utf-8").splitlines():
                p = line.split("\t")
                if len(p) >= 3:
                    spans.append((int(p[1]), int(p[2])))
        text = art.read_text(encoding="utf-8", errors="replace")
        out.append({"id": aid, "text": text, "spans": spans})
    return out


def load_techniques() -> dict:
    """technique -> character count, for context on what PTC actually annotates."""
    tally = {}
    for f in sorted(TC_LABELS.glob("*.labels")):
        for line in f.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) >= 4:
                tally[p[1]] = tally.get(p[1], 0) + (int(p[3]) - int(p[2]))
    return tally


def covered(spans: list[tuple[int, int]], a: int, b: int) -> bool:
    """Does [a,b) overlap any annotated span at all?"""
    return any(a < e and b > s for s, e in spans)


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", action="append", help="restrict to these lenses")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-hits", type=int, default=10,
                    help="lenses with fewer hits than this are reported but not ranked")
    a = ap.parse_args(argv)

    from tradecraft.detect import detect
    from tradecraft.loader import load_lenses

    corpus = load_corpus()
    lenses = load_lenses(str(ROOT / "detectors"))
    if a.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(a.lens)}

    total_chars = sum(len(d["text"]) for d in corpus)
    annotated_chars = sum(e - s for d in corpus for s, e in d["spans"])
    chance = annotated_chars / total_chars

    rows = []
    for lid, tax in sorted(lenses.items()):
        hits = inside = 0
        per_article = []
        for d in corpus:
            try:
                hs = detect(d["text"], tax, backend="cues")
            except Exception as e:                      # a lens with no text cues
                hs = []
                if lid == "revolving_door":
                    pass
                elif "no cues" not in str(e).lower():
                    raise
            n_in = 0
            for h in hs:
                st = getattr(h, "char_start", None)
                sp = getattr(h, "span", "") or ""
                if st is None:
                    continue
                hits += 1
                if covered(d["spans"], st, st + len(sp)):
                    inside += 1
                    n_in += 1
            if hs:
                per_article.append(n_in / len(hs))
        prec = (inside / hits) if hits else None
        rows.append({
            "lens": lid, "hits": hits, "inside": inside,
            "precision": round(prec, 4) if prec is not None else None,
            "lift": round(prec / chance, 3) if prec is not None and chance else None,
            "articles_with_hits": len(per_article),
        })

    ranked = sorted((r for r in rows if r["hits"] >= a.min_hits),
                    key=lambda r: -(r["lift"] or 0))
    thin = [r for r in rows if r["hits"] < a.min_hits]

    result = {
        "corpus": {"articles": len(corpus), "chars": total_chars,
                   "annotated_chars": annotated_chars,
                   "chance_precision": round(chance, 4),
                   "annotated_spans": sum(len(d["spans"]) for d in corpus)},
        "how_to_read": (
            f"chance_precision is the fraction of all corpus characters that sit inside SOME "
            f"human propaganda annotation ({chance:.1%}). A lens whose hits land in an "
            f"annotation at that rate is firing at chance. LIFT is precision / chance: 1.0 is "
            f"chance, and only well above 1.0 is evidence the lens finds what annotators found. "
            f"A low lift is a floor, not a verdict -- PTC annotates propaganda techniques in "
            f"news, this taxonomy names institutional and rhetorical method, and the second is "
            f"broader than the first."),
        "ranked": ranked,
        "too_few_hits": thin,
    }
    if a.json:
        print(json.dumps(result, indent=1))
        return 0

    c = result["corpus"]
    print(f"PTC: {c['articles']} articles, {c['annotated_spans']} annotated spans, "
          f"{c['annotated_chars']:,} of {c['chars']:,} chars annotated")
    print(f"chance precision = {chance:.4f}  ({chance:.1%} of characters are inside some annotation)")
    print()
    print(f"  {'lens':<28} {'hits':>6} {'in-span':>8} {'precision':>10} {'lift':>7}")
    for r in ranked:
        print(f"  {r['lens']:<28} {r['hits']:>6} {r['inside']:>8} "
              f"{r['precision']:>10.4f} {r['lift']:>7.2f}")
    if thin:
        print()
        print(f"  fewer than {a.min_hits} hits across {len(corpus)} articles "
              f"(not ranked -- too little signal to read):")
        for r in thin:
            print(f"    {r['lens']:<28} {r['hits']:>4} hits")
    if ranked:
        lifts = [r["lift"] for r in ranked if r["lift"]]
        print()
        print(f"  median lift {statistics.median(lifts):.2f} over {len(ranked)} ranked lenses; "
              f"{sum(1 for x in lifts if x > 1.5)} above 1.5, "
              f"{sum(1 for x in lifts if x < 1.1)} at or below chance")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
