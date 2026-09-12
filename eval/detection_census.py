#!/usr/bin/env python3
"""A census of which DETECTIONS actually work, measured against human annotation.

WHY THIS EXISTS
---------------
The author asked the right question: can we make a census of actually effective detections,
so we start from what demonstrably works rather than from a taxonomy of what we hoped would.

`ptc_precision.py` answers it at LENS level and the answer is already uncomfortable — four
lenses beat chance, one fires materially BELOW chance, ten are near-silent. But a lens is not
the unit you keep or cut. A lens is 3–27 detections and 18–171 cues, and a lens at 1.19x
chance is not uniformly mediocre: it is some detections carrying signal and others firing on
ordinary prose. Cutting or keeping a whole lens on an aggregate is the same net-aggregate
error this project keeps finding elsewhere.

So this reports per DETECTION: how often it fires across 371 annotated articles, how often
that firing lands inside a span six professional annotators independently marked as
propaganda, and the LIFT — precision divided by the corpus's own annotated-character rate.

READ THE LIFT, NOT THE PRECISION. 13.2% of the corpus's characters sit inside some
annotation, so a detection landing there 13.2% of the time is firing at chance. Lift near 1.0
means it is finding nothing a human found; lift below 1.0 means it is anti-predictive, which
is worse than silence because it looks like evidence.

WHAT THIS IS NOT
----------------
Not a mandate to cut. PTC annotates *propaganda techniques in news articles*; this taxonomy
names *institutional tradecraft*, and the two overlap without being the same construct. A
detection can be correct and score zero here because the corpus contains no instance of what
it detects — `costly_signal` and `adept_speech` are not about news register at all. So a low
lift on a detection that FIRES is evidence; a zero on a detection that never fires is a
statement about the corpus, and the census reports the two differently.

WHICH TECHNIQUE, NOT JUST WHETHER
---------------------------------
2026-09-03. PTC ships a second label set nothing here read: task-2 technique classification,
which types every span with one of fourteen human-named techniques (Loaded_Language,
Appeal_to_Authority, Causal_Oversimplification, …) rather than merely marking it as
propaganda. 6,129 typed spans against task-1's 5,468, because task-1 merges spans that carry
overlapping techniques.

Reading it turns "our detection landed in some annotated span" into "our detection catches
*this* technique six professional annotators named," which is the difference between a
coincidence and a claim. It also answers the question the lens-level census could not ask:
which named techniques can this detector catch AT ALL. A detection can have respectable lift
and still be catching one narrow technique; a technique with zero coverage across 140
detections is a documented gap rather than an unknown.

Both directions are reported: `--techniques` gives per-technique coverage (how many of that
technique's spans any detection reaches, and which detection reaches most), and every
detection row carries the distribution of techniques it lands on.

    python eval/detection_census.py                 # full census, ranked
    python eval/detection_census.py --min-hits 5    # only detections with enough firings to judge
    python eval/detection_census.py --markdown      # table for a results doc
    python eval/detection_census.py --techniques    # per-technique coverage, both directions
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERIES = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

from tradecraft.detect import detect_cues                     # noqa: E402
from tradecraft.loader import load_lenses                      # noqa: E402

PTC = os.path.join(SERIES, "research", "external", "ptc")
ARTICLES = os.path.join(PTC, "train-articles")
LABELS = os.path.join(PTC, "train-labels-task1-span-identification")
TECH_LABELS = os.path.join(PTC, "train-task2-TC.labels")
TECH_LABELS_DIR = os.path.join(PTC, "train-labels-task2-technique-classification")
OUT = os.path.join(HERE, "detection-census.json")

#: Detections with fewer firings than this cannot be judged on lift; reported separately.
JUDGEABLE_HITS = 5


def load_corpus():
    if not os.path.isdir(ARTICLES):
        sys.exit("missing %s -- the PTC corpus is not vendored here. See "
                 "eval/RESULTS-2026-08-26-ptc-precision.md for provenance." % ARTICLES)
    out = []
    for name in sorted(os.listdir(ARTICLES)):
        if not (name.startswith("article") and name.endswith(".txt")):
            continue
        aid = name[len("article"):-len(".txt")]
        text = io.open(os.path.join(ARTICLES, name), encoding="utf-8",
                       errors="replace").read()
        spans = []
        lab = os.path.join(LABELS, "article%s.task1-SI.labels" % aid)
        if os.path.exists(lab):
            for line in io.open(lab, encoding="utf-8"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        spans.append((int(parts[1]), int(parts[2])))
                    except ValueError:
                        continue
        out.append({"id": aid, "text": text, "spans": spans})
    return out


def load_techniques():
    """article id -> [(technique, start, end)] from PTC's task-2 label set.

    Prefers the single aggregate file and falls back to the per-article directory, so a
    checkout with only one of the two still measures. Returns {} when neither is present:
    the technique view then reports itself unavailable rather than silently reporting zeros,
    which would read as "we catch no techniques".
    """
    out = {}
    if os.path.exists(TECH_LABELS):
        sources = [TECH_LABELS]
    elif os.path.isdir(TECH_LABELS_DIR):
        sources = [os.path.join(TECH_LABELS_DIR, n)
                   for n in sorted(os.listdir(TECH_LABELS_DIR))
                   if n.endswith(".labels")]
    else:
        return out
    for path in sources:
        for line in io.open(path, encoding="utf-8", errors="replace"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            aid, technique, start, end = parts[0], parts[1], parts[2], parts[3]
            try:
                span = (technique, int(start), int(end))
            except ValueError:
                continue
            out.setdefault(aid.strip(), []).append(span)
    return out


def covered(spans, a, b):
    """True when [a,b) overlaps any annotated span."""
    return any(a < end and b > start for start, end in spans)


def techniques_at(tech_spans, a, b):
    """Every human-named technique whose span overlaps [a,b). Usually one, sometimes several."""
    return sorted({t for t, start, end in tech_spans if a < end and b > start})


def wilson(k, n, z=1.96):
    """95% Wilson interval for a proportion. Returns (lo, hi).

    A lift of 6.29 computed from SIX firings is a ratio with an enormous interval, and this
    project does not publish a ratio without its uncertainty -- that is the whole complaint
    the paper makes about the bias literature. Wilson rather than normal-approximation
    because it behaves at the small n this census actually has, and does not produce bounds
    below 0 or above 1.
    """
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-hits", type=int, default=JUDGEABLE_HITS)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--techniques", action="store_true",
                    help="per-technique coverage: which human-named techniques we catch")
    args = ap.parse_args(argv)

    corpus = load_corpus()
    tech = load_techniques()
    annotated = sum(e - s for d in corpus for s, e in d["spans"])
    total = sum(len(d["text"]) for d in corpus)
    chance = (annotated / total) if total else 0.0

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    tech_total = {}      # technique -> annotated spans of it in the corpus
    tech_caught = {}     # technique -> spans of it any detection overlapped
    by_technique = {}    # technique -> {lens/detection: spans caught}
    stats = {}
    for lens_id, tax in sorted(lenses.items()):
        for marker in tax.markers:
            for det in marker.detections:
                stats[(lens_id, det.id)] = {"hits": 0, "in_span": 0,
                                            "marker": marker.id,
                                            "n_cues": len(det.cues)}

    for doc in corpus:
        tech_spans = tech.get(doc["id"], [])
        doc_hits = []
        for lens_id, tax in sorted(lenses.items()):
            if tax.is_structural:
                continue
            for hit in detect_cues(doc["text"], tax):
                key = (lens_id, hit.detection_id)
                if key not in stats:
                    continue
                stats[key]["hits"] += 1
                if covered(doc["spans"], hit.char_start, hit.char_end):
                    stats[key]["in_span"] += 1
                doc_hits.append((hit.char_start, hit.char_end, lens_id, hit.detection_id))
                for name in techniques_at(tech_spans, hit.char_start, hit.char_end):
                    stats[key].setdefault("techniques", {})
                    stats[key]["techniques"][name] = stats[key]["techniques"].get(name, 0) + 1

        # The reverse direction, and it must be counted over SPANS rather than over hits: two
        # detections landing on one span is one technique instance caught, not two. Counting
        # hits here would report coverage above 100% for a heavily-cued technique.
        for name, start, end in tech_spans:
            tech_total[name] = tech_total.get(name, 0) + 1
            catchers = {"%s/%s" % (lid, did) for hs, he, lid, did in doc_hits
                        if start < he and end > hs}
            if catchers:
                tech_caught[name] = tech_caught.get(name, 0) + 1
                for label in catchers:
                    by_technique.setdefault(name, {})
                    by_technique[name][label] = by_technique[name].get(label, 0) + 1

    rows = []
    for (lens_id, det_id), s in stats.items():
        prec = (s["in_span"] / s["hits"]) if s["hits"] else None
        techs = s.get("techniques", {})
        ranked = sorted(techs.items(), key=lambda kv: -kv[1])
        rows.append({
            "lens": lens_id, "detection": det_id, "marker": s["marker"],
            "n_cues": s["n_cues"], "hits": s["hits"], "in_span": s["in_span"],
            "precision": None if prec is None else round(prec, 3),
            "techniques": dict(ranked),
            "technique_top": ranked[0][0] if ranked else None,
            # What share of this detection's in-span landings sit on its single commonest
            # technique. Near 1.0 means the detection is really a detector for that one
            # technique, whatever the marker calls it -- worth knowing before keeping it.
            "technique_concentration": (round(ranked[0][1] / sum(techs.values()), 2)
                                        if techs else None),
            "lift": None if prec is None or not chance else round(prec / chance, 2),
            "lift_ci": None if not s["hits"] or not chance else [
                round(wilson(s["in_span"], s["hits"])[0] / chance, 2),
                round(wilson(s["in_span"], s["hits"])[1] / chance, 2)],
        })

    # THE CI RULE, applied here as it is everywhere else in this project: a lift is a finding
    # only if its interval excludes chance. A point estimate of 6.29 from six firings is not a
    # result on its own, and neither is a 0.00 from eleven.
    #
    # 2026-09-03: this lived only in the summary while the table flagged on the point estimate
    # at 1.5x, so `sourcing_asymmetry/unsourced-assertion` printed "<== works" on a lift of
    # 1.51 whose interval is [0.27, 4.71] -- and the summary, three lines below, correctly
    # counted it undecided. One fact, two copies, disagreeing in the same output. The rule now
    # has a single implementation and both readers call it.
    def ci_excludes_chance(r, above):
        ci = r.get("lift_ci")
        if not ci:
            return False
        return ci[0] > 1.0 if above else ci[1] < 1.0

    judgeable = [r for r in rows if r["hits"] >= args.min_hits]
    thin = [r for r in rows if 0 < r["hits"] < args.min_hits]
    silent = [r for r in rows if r["hits"] == 0]
    judgeable.sort(key=lambda r: -(r["lift"] or 0))

    print("DETECTION CENSUS -- %d articles, %d annotated span(s), chance precision %.4f"
          % (len(corpus), sum(len(d["spans"]) for d in corpus), chance))
    print("lift = precision / chance. Below 1.0 is anti-predictive: worse than silence,")
    print("because it looks like evidence.")
    print()

    if args.techniques:
        if not tech:
            print("PTC task-2 technique labels not found at either")
            print("  %s" % os.path.relpath(TECH_LABELS, SERIES))
            print("  %s" % os.path.relpath(TECH_LABELS_DIR, SERIES))
            print("Reporting nothing rather than zeros, which would read as 'we catch none'.")
            return 1
        print("TECHNIQUE COVERAGE -- which human-named techniques any detection reaches")
        print("Counted over SPANS: two detections on one span is one instance caught.")
        print("%-34s %7s %8s %7s  %s" % ("technique", "spans", "caught", "cover", "best detection"))
        for name in sorted(tech_total, key=lambda n: -tech_total[n]):
            total_n = tech_total[name]
            caught = tech_caught.get(name, 0)
            best = ""
            if by_technique.get(name):
                label, n = max(by_technique[name].items(), key=lambda kv: kv[1])
                best = "%s (%d)" % (label, n)
            print("%-34s %7d %8d %6.1f%%  %s"
                  % (name, total_n, caught, 100.0 * caught / total_n if total_n else 0.0, best))
        gaps = [n for n in tech_total if not tech_caught.get(n)]
        print()
        print("%d of %d techniques have ZERO coverage across all %d detections: %s"
              % (len(gaps), len(tech_total), len(rows),
                 ", ".join(sorted(gaps)) if gaps else "none"))
        print("A zero here is a documented gap, not an unknown -- which is the point of")
        print("measuring against a corpus somebody else annotated.")
        return 0

    if args.markdown:
        print("| lens | detection | cues | hits | in-span | lift |")
        print("|---|---|---:|---:|---:|---:|")
        for r in judgeable:
            print("| `%s` | `%s` | %d | %d | %d | **%.2f** |"
                  % (r["lens"], r["detection"], r["n_cues"], r["hits"], r["in_span"],
                     r["lift"]))
    else:
        print("JUDGEABLE -- fired at least %d times, so lift means something" % args.min_hits)
        print("%-24s %-28s %5s %6s %6s %14s" % ("lens", "detection", "hits",
                                                 "in-sp", "lift", "lift 95% CI"))
        for r in judgeable:
            flag = ""
            if ci_excludes_chance(r, True):
                flag = "  <== works"
            elif ci_excludes_chance(r, False):
                flag = "  <== anti-predictive"
            ci = r.get("lift_ci") or [0, 0]
            print("%-24s %-28s %5d %6d %6.2f  [%4.2f, %5.2f]%s"
                  % (r["lens"][:24], r["detection"][:28], r["hits"],
                     r["in_span"], r["lift"], ci[0], ci[1], flag))

    print()
    print("SUMMARY")
    works = [r for r in judgeable if ci_excludes_chance(r, True)]
    anti = [r for r in judgeable if ci_excludes_chance(r, False)]
    unproven = [r for r in judgeable if r not in works and r not in anti]
    print("  %3d detections ABOVE chance with the interval to prove it -- build on these"
          % len(works))
    print("  %3d detections BELOW chance with the interval to prove it -- actively harmful"
          % len(anti))
    print("  %3d fired enough to judge but the interval spans chance   -- undecided, not"
          % len(unproven))
    print("      supported and not refuted; more firings would settle each one")
    print("  %3d fired 1-%d times                          -- too thin to judge"
          % (len(thin), args.min_hits - 1))
    print("  %3d never fired                               -- a fact about this corpus, not"
          % len(silent))
    print("      necessarily about the detection: PTC is news propaganda, this taxonomy is")
    print("      institutional tradecraft, and they overlap without being the same thing.")

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"articles": len(corpus), "chance_precision": round(chance, 4),
                   "min_hits_to_judge": args.min_hits,
                   "technique_coverage": {
                       name: {"spans": tech_total[name],
                              "caught": tech_caught.get(name, 0),
                              "coverage": round(tech_caught.get(name, 0) / tech_total[name], 3),
                              # Tie-break on the name. Sorting by count alone left equal-count
                              # entries in dict insertion order, which varies run to run: two
                              # 1-hit detections swapped places between two runs of unchanged
                              # data on 2026-09-11, producing a 4-line diff that said nothing.
                              # A derived artifact that cannot reproduce itself byte-for-byte
                              # cannot be gated, and every other export here can.
                              "by_detection": dict(sorted(by_technique.get(name, {}).items(),
                                                          key=lambda kv: (-kv[1], kv[0])))}
                       for name in sorted(tech_total, key=lambda n: -tech_total[n])},
                   "detections": rows},
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print()
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
