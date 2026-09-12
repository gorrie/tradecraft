#!/usr/bin/env python3
"""Measure each lens's detection floor: how far its index moves when nothing substantive does.

WHY THIS EXISTS
---------------
Every lens produces an index from 0 to 100. The eval suite measures whether that index is
*right* — precision against labels, false-positive sweeps, mirror-pairs for direction
neutrality, cross-faction checks. Nothing measures whether an index *difference* is bigger
than what the grader produces by accident.

That distinction is not academic. A sibling project spent three days finding exactly this hole
in the published LLM-political-bias literature: ten studies, all reporting effects, none
reporting the resolution of the instrument producing them. The floors turned out to be the same
size as the effects. Four of that project's own null results were then found to sit below what
its instrument could detect, which converted four confident retractions into "undecided."

A leaderboard that grades named people and organisations needs to survive the same question.
If a subject scores 61 and another scores 54, is seven points a finding or is it the width of
the ruler? Right now nothing in this repository can answer that, and the honest answer is
currently unknown.

WHAT IT MEASURES
----------------
Four perturbations that change no method-content whatsoever. A lens that measures tradecraft
must be indifferent to all of them:

  sentence-order   the same sentences, permuted. A method-marker is a property of the
                   rhetorical move, not of where in the document it sits. This is the direct
                   analogue of the presentation-order floor that turned out to dominate the
                   political-instrument literature.
  chunk-boundary   the same text split at different offsets. Cue matching is bounded to a
                   window, so where a boundary falls can decide whether a marker is seen.
  whitespace       paragraph and line-break normalisation. Pure formatting.
  duplication      the passage repeated twice. Density is per-token, so a lens with a
                   correctly normalised density should not move; one that counts raw hits will.

Reported per lens, in index points: median, p90, max, and the minimum detectable effect at 80%
power — the smallest true index difference that would clear this floor often enough to be
called an effect.

The `cues` backend is deterministic and needs no API key, so this runs at zero cost and in CI.
An LLM-backend floor would be larger, not smaller: this is a lower bound on the lens's own
noise, and a claim that cannot clear the deterministic floor cannot clear the real one.

    python eval/lens_floor.py                      # every lens, cues backend
    python eval/lens_floor.py --lens legibility    # one lens
    python eval/lens_floor.py --markdown           # table for a results doc
    python eval/lens_floor.py --check              # exit 1 if any lens has no floor recorded
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import random
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.corpus_docs import documents, spread       # noqa: E402
from tradecraft.detect import detect                      # noqa: E402
from tradecraft.grader import grade_document_for_lens      # noqa: E402
from tradecraft.loader import load_lenses                  # noqa: E402

SEED = 20260901
FLOOR_FILE = os.path.join(HERE, "lens-floors.json")
#: Written by eval/background_rate.py -- the resolution object for a lens too rare to hold an
#: index floor. Read here only by --check, which gates on "a floor OR a rate", never neither.
RATE_FILE = os.path.join(HERE, "background-rates.json")
ALPHA = 0.05
POWER = 0.80
# A lens must actually fire on at least this many documents before a floor means anything.
MIN_LIVE_DOCS = 8


def tokens(text):
    return max(1, len(text.split()))


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def perturb(text, rng):
    """Return {name: variant}. None of these changes any method-content."""
    sents = sentences(text)
    out = {}

    if len(sents) > 2:
        shuffled = sents[:]
        rng.shuffle(shuffled)
        out["sentence-order"] = " ".join(shuffled)

    # Move the boundary: drop the first sentence and re-append it, so the same words sit in a
    # different window without any being added or removed.
    if len(sents) > 3:
        out["chunk-boundary"] = " ".join(sents[1:] + sents[:1])

    out["whitespace"] = re.sub(r"\s+", " ", text).strip()
    out["duplication"] = text.strip() + "\n\n" + text.strip()
    return out


def index_of(text, taxonomy):
    hits = detect(text, taxonomy, backend="cues")
    return grade_document_for_lens(taxonomy, hits, tokens(text)).index


def corpus_docs(limit):
    # An earlier version of this excluded _calibration-cache and _news-control as "eval
    # fixtures we should not tune against". That reasoning is wrong for a NOISE floor and it
    # excluded every document in the repository. A floor measures whether the index moves when
    # the content does not; there is no label to overfit to and nothing to tune. _news-control
    # is off-topic control text, which is the best possible material for it.
    #
    # 2026-09-01: this globbed corpus/**/*.txt directly and so never saw a JSONL corpus at
    # all -- 68 method specimens and 18 congressional hearings, none of them visible to the
    # tool reporting that most lenses had no material to measure a floor over. Enumeration
    # moved to tradecraft.corpus_docs; the cap is now a spread rather than a head-slice,
    # because path order put every JSONL record past it.
    return spread(documents(min_words=60), limit)


#: Step of the MDE search, in index points. Reported values are multiples of it, so it is the
#: granularity of the answer and must not be mistaken for the answer.
MDE_STEP = 0.5


def mde(deltas, threshold):
    """Smallest upward shift of the observed noise that clears `threshold` 80% of the time.

    Returns **None for a degenerate null** -- one where nothing moved at all -- rather than a
    number, because there is no number to give.

    2026-09-02: this returned 0.5 in that case, which is the search STEP and not a
    measurement. It mattered immediately: after density was repaired to a real rate, all four
    lenses with a measured floor moved 0.0 on every perturbation, and all four then reported
    "MDE 0.5" -- which reads as "resolves half an index point" and is unearned. The instrument
    showed no noise; what it can resolve is bounded by granularity, and that is a different
    statement from a resolution of 0.5.
    """
    if not deltas:
        return float("nan")
    if all(abs(x) <= 0.0 for x in deltas):
        return None
    d = 0.0
    while d <= 100.0:
        shifted = [abs(x) + d for x in deltas]
        if sum(1 for s in shifted if s > threshold) / len(shifted) >= POWER:
            return d
        d += MDE_STEP
    return float("nan")


def mde_label(value):
    """How an MDE prints. A degenerate null gets a phrase, not a digit."""
    if value is None:
        return "none measured"
    if value != value:                                  # NaN
        return "n/a"
    return "%g" % value


def pctile(vals, q):
    v = sorted(vals)
    if not v:
        return float("nan")
    return v[min(int(q * len(v)), len(v) - 1)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lens", action="append", default=None)
    # DEFAULT IS THE WHOLE CORPUS. It was 40, and that is a trap of the same family as the
    # head-slice `corpus_docs.spread()` exists to prevent: running this tool with no arguments
    # measured a 40-document sample, found that NO lens reached MIN_LIVE_DOCS on it, and wrote
    # that over floors measured on 206. The command that destroys the result is the shortest
    # one to type, and its output looks like an ordinary bad-news measurement.
    # Caught 2026-09-03 by doing exactly that.
    ap.add_argument("--docs", type=int, default=None,
                    help="cap the corpus (default: every document; a cap can only lose signal)")
    ap.add_argument("--allow-regression", action="store_true",
                    help="permit writing a floor file that records FEWER lenses than the "
                         "existing one; for a deliberate corpus cut or lens retirement")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any lens lacks a recorded floor")
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    if args.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(args.lens)}
    if not lenses:
        print("no lenses matched")
        return 1

    if args.check:
        if not os.path.exists(FLOOR_FILE):
            print("NO FLOORS RECORDED. Run: python eval/lens_floor.py")
            print("A lens without a measured floor cannot say whether a score difference is a")
            print("finding or the width of its own ruler.")
            return 1
        recorded = json.load(io.open(FLOOR_FILE, encoding="utf-8"))
        indexed = set(recorded.get("lenses", {}))

        # Gate 24, in the form it was always meant to have: every lens must hold the
        # resolution object ITS STATE requires, not the one this file happens to compute.
        # An index floor needs MIN_LIVE_DOCS live documents, and twelve of sixteen lenses
        # cannot meet that because the move they detect is rare -- which is a property of the
        # phenomenon, not a defect. Those lenses carry a measured BACKGROUND FIRING RATE
        # instead (eval/background_rate.py), against which a subject's firing rate is a
        # finding or is not.
        #
        # This is not a loosening. Demanding an index floor from a rare lens made the check
        # unsatisfiable, so it sat outside CI and gated nothing at all. What must never pass
        # is a lens holding NEITHER object: a reading with no ruler is the exact defect this
        # project exists to indict in other people's instruments.
        rated = set()
        if os.path.exists(RATE_FILE):
            rated = set(json.load(io.open(RATE_FILE, encoding="utf-8")).get("lenses", {}))

        unruled = sorted(k for k in lenses if k not in indexed and k not in rated)
        if unruled:
            print("LENSES WITH NO RESOLUTION OBJECT AT ALL: %s" % ", ".join(unruled))
            print("Each needs either a measured index floor or a measured background rate:")
            print("  python eval/lens_floor.py          # index floors")
            print("  python eval/background_rate.py     # background firing rates")
            return 1

        by_index = sorted(k for k in lenses if k in indexed)
        by_rate = sorted(k for k in lenses if k not in indexed and k in rated)
        print("all %d lens(es) hold a resolution object" % len(lenses))
        print("  %2d index-bearing (measured floor): %s" % (len(by_index), ", ".join(by_index)))
        print("  %2d receipts-only (background rate): %s" % (len(by_rate), ", ".join(by_rate)))
        return 0

    picked = corpus_docs(args.docs)
    if not picked:
        print("no corpus documents found under corpus/")
        return 1

    rng = random.Random(SEED)
    docs = [(d.name, d.text) for d in picked]
    origins = {}
    for d in picked:
        origins[d.origin] = origins.get(d.origin, 0) + 1
    print("corpus: %d document(s) across %d file(s)" % (len(docs), len(origins)))

    results = {}
    vacuous = {}
    for lens_id, taxonomy in sorted(lenses.items()):
        per_kind = {}
        all_deltas = []
        base_indices = []
        for name, text in docs:
            try:
                base = index_of(text, taxonomy)
            except Exception:
                continue
            base_indices.append(base)
            for kind, variant in perturb(text, rng).items():
                try:
                    got = index_of(variant, taxonomy)
                except Exception:
                    continue
                d = got - base
                per_kind.setdefault(kind, []).append(d)
                all_deltas.append(d)
        if not all_deltas:
            continue
        # A floor measured over documents the lens never fires on is the stability of zero,
        # not the width of the ruler. First run of this harness returned MDE 0.5 for all 15
        # lenses because the only corpus in the repo is news-control text and 19 of 600
        # lens-document cells were nonzero. Reporting that as a clean floor would have been
        # the most flattering possible reading of no data.
        live = sum(1 for b in base_indices if b > 0)
        if live < MIN_LIVE_DOCS:
            vacuous[lens_id] = live
            continue
        absall = [abs(x) for x in all_deltas]
        thr = pctile(absall, 1 - ALPHA)
        results[lens_id] = {
            "n_docs": len(docs),
            "n_comparisons": len(all_deltas),
            "median": round(st.median(absall), 2),
            "p90": round(pctile(absall, 0.90), 2),
            "max": round(max(absall), 2),
            "threshold_p95": round(thr, 2),
            "mde": (lambda m: None if m is None else round(m, 2))(mde(all_deltas, thr)),
            # p90 collapses onto max when the sample is small: nearest-rank puts
            # int(0.90*n) at n-1 for every n <= 10, so the two columns print the same
            # number and look like two statistics. Flagged rather than hidden.
            "p90_is_max": pctile(absall, 0.90) == max(absall),
            "n_small": len(absall) <= 10,
            "by_perturbation": {k: round(max(abs(x) for x in v), 2)
                                for k, v in sorted(per_kind.items())},
        }

    payload = {
        "_note": ("Detection floors per lens, in index points, measured with the deterministic "
                  "cues backend on corpus/**/*.txt. Perturbations change no method-content: "
                  "sentence order, chunk boundary, whitespace, duplication. An LLM-backend "
                  "floor would be larger, so these are lower bounds. Regenerate with "
                  "python eval/lens_floor.py"),
        "seed": SEED,
        "lenses": results,
        "no_floor_measurable": vacuous,
    }
    # REGRESSION GUARD. A floor file that loses lenses is a measurement that got worse, and it
    # is indistinguishable in the output from a lens honestly failing MIN_LIVE_DOCS -- both
    # print "fired on N of M documents (need 8)". Losing four floors that way on 2026-09-03
    # cost nothing only because the file was in git.
    #
    # This is the never-loosen rule applied to a derived artifact: a dropped baseline FAILS
    # rather than silently replacing the thing it is worse than. Overriding is deliberate and
    # named, because there are legitimate reasons (a corpus was cut, a lens was retired).
    if os.path.exists(FLOOR_FILE) and not args.allow_regression:
        try:
            previous = set(json.load(io.open(FLOOR_FILE, encoding="utf-8")).get("lenses", {}))
        except ValueError:
            previous = set()
        lost = sorted(previous - set(results))
        if lost:
            print("")
            print("REFUSING TO WRITE: this run records %d lens floor(s), the existing file has "
                  "%d." % (len(results), len(previous)))
            print("Lenses that would LOSE their measured floor: %s" % ", ".join(lost))
            print("")
            print("A smaller corpus is the usual cause -- this run used %d document(s). Check "
                  "--docs before" % len(docs))
            print("assuming the lenses got worse. If the loss is intended (corpus cut, lens "
                  "retired), re-run")
            print("with --allow-regression.")
            return 1

    io.open(FLOOR_FILE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, indent=2) + "\n")

    if args.markdown:
        print("| lens | comparisons | median | p90 | max | MDE |")
        print("|---|---:|---:|---:|---:|---:|")
        for k, v in sorted(results.items(), key=lambda kv: -(kv[1]["mde"] or 0.0)):
            print("| `%s` | %d | %.1f | %.1f | %.1f | **%s** |"
                  % (k, v["n_comparisons"], v["median"], v["p90"], v["max"], mde_label(v["mde"])))
        return 0

    print("LENS DETECTION FLOORS -- index points moved by changing nothing substantive")
    print("cues backend, %d documents, seed %d" % (len(docs), SEED))
    print()
    print("%-26s %6s %7s %6s %6s %6s" % ("lens", "comps", "median", "p90", "max", "MDE"))
    for k, v in sorted(results.items(), key=lambda kv: -(kv[1]["mde"] or 0.0)):
        print("%-26s %6d %7.1f %6.1f %6.1f %13s"
              % (k, v["n_comparisons"], v["median"], v["p90"], v["max"], mde_label(v["mde"])))
    print()
    print("MDE = smallest index difference this lens can resolve 80%% of the time against its")
    print("own noise. A score gap below a lens's MDE is not a finding; it is the ruler's width.")
    print()
    measured = {k: v for k, v in results.items() if v["mde"] is not None}
    if measured:
        k, v = max(measured.items(), key=lambda kv: kv[1]["mde"])
        print("Widest ruler: %s at %s points." % (k, mde_label(v["mde"])))
        print("  driven by: %s" % ", ".join("%s %.1f" % (a, b)
                                            for a, b in v["by_perturbation"].items()))
    elif results:
        # Every lens returned an exactly-zero null. Saying "widest ruler: none measured
        # points" was worse than saying nothing; and this state is worth naming, because a
        # clean sweep across four perturbations is either a repaired instrument or a broken
        # harness, and the reader should be pointed at that question rather than past it.
        print("NO NOISE ON ANY MEASURED LENS. All %d moved 0.0 index points under every"
              % len(results))
        print("perturbation, so no minimum detectable effect follows from this run: what these")
        print("lenses can resolve is bounded by index granularity, not by measured noise.")
        print()
        print("That is the expected state after the 2026-09-02 density repair, and it is also")
        print("what a harness that had stopped perturbing anything would print. The difference")
        print("is checkable: tests/test_floors.py asserts the perturbations still alter the")
        print("text, and eval/length_dependence.py measures the same nulls independently.")
    print()
    if vacuous:
        print()
        print("NO FLOOR MEASURABLE for %d of %d lens(es): the corpus does not make them fire."
              % (len(vacuous), len(lenses)))
        for k, live in sorted(vacuous.items()):
            print("  %-26s fired on %d of %d documents (need %d)"
                  % (k, live, len(docs), MIN_LIVE_DOCS))
        print()
        print("This is not a clean result. A floor over documents a lens never fires on")
        print("measures the stability of zero. These lenses need a corpus of material they")
        print("actually detect before their resolution can be stated.")
    print()
    print("wrote %s" % os.path.relpath(FLOOR_FILE, ROOT))
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
