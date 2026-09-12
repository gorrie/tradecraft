#!/usr/bin/env python3
"""Measure the background firing rate in a LENGTH-INVARIANT unit, and report what changes.

WHY (GitLab issue #7)
---------------------
Every background rate in `background_rate.py` is fired-documents over n-documents, with no
length normalisation. After the 2026-09-05 by-id refetch restored the corpora to full length,
the background pool runs **140 to 57,458 words -- a 410x range**. A congressional hearing fires
more often than a public comment for no reason except that there is forty times more of it.

The issue names two candidate units and says both need MEASURING before either is adopted.
This measures the second one and prints the comparison. It adopts nothing: `background_rate.py`
still owns the published numbers, and this exists so the choice is made against data rather
than taste.

    per-document (today)   a document fires if its whole-text index > 0
    per-window (here)      a document fires if ANY N-word window fires

The windowed unit keeps the binomial machinery and the "document fires" idiom, which is the
argument for it over firings-per-1,000-words -- that one turns the statistic into a rate and
needs Poisson replacements for the Wilson bound and the whole MDR apparatus.

CHOOSING N, WHICH THE ISSUE CORRECTLY REFUSED TO DO BY DEFAULT
--------------------------------------------------------------
`_news-control`'s 3,200 is not a defensible N -- it is an artefact of how someone else chunked
wire copy. Two constraints decide it here:

  * **Long enough for a lens to fire at all.** These detectors grade against a per-1,000-word
    density, so a window far below 1,000 words makes a single cue look like a torrent.
  * **Short enough that most of the pool contains one.** A window longer than the median
    document silently reverts to the per-document unit for half the corpus.

`--sweep` prints the rate at several N so the sensitivity to that choice is visible rather than
assumed. The default, 500, is the round number nearest the shortest background bucket's median
(advocacy-comments, 459 words) -- chosen so the SHORTEST material still contributes a whole
window, since the long material is the side that needs constraining.

    python tradecraft/eval/window_rate.py                # compare both units at N=500
    python tradecraft/eval/window_rate.py --sweep        # rates at 250/500/1000/2000
    python tradecraft/eval/window_rate.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, HERE)

import background_rate as B  # noqa: E402
from tradecraft.corpus_docs import documents  # noqa: E402
from tradecraft.loader import load_lenses  # noqa: E402

DEFAULT_WINDOW = 500
SWEEP = (250, 500, 1000, 2000)
#: Overlap so a cue cluster straddling a boundary is not lost. Half a window is the usual
#: choice and is cheap here; the corpus is a few hundred documents.
STRIDE_FRACTION = 0.5


def windows(text, size, stride_fraction=STRIDE_FRACTION):
    """Overlapping N-word windows. A document shorter than N yields itself, once.

    Yielding the whole short document rather than skipping it matters: skipping would drop the
    public-comment bucket entirely and re-create the length bias pointing the other way.
    """
    words = text.split()
    if len(words) <= size:
        yield text
        return
    stride = max(1, int(size * stride_fraction))
    for start in range(0, len(words) - size + 1, stride):
        yield " ".join(words[start:start + size])


def fires_windowed(text, taxonomy, size):
    """Does ANY window of this document fire? Returns (fired, n_windows)."""
    n = 0
    for w in windows(text, size):
        n += 1
        try:
            if B.index_of(w, taxonomy) > 0:
                return True, n
        except Exception:
            continue
    return False, n


def measure(size, lenses, docs):
    out = {}
    for lens_id, taxonomy in sorted(lenses.items()):
        doc_fired = win_fired = n = 0
        win_total = 0
        for d in docs:
            try:
                whole = B.index_of(d.text, taxonomy)
            except Exception:
                continue
            n += 1
            if whole > 0:
                doc_fired += 1
            f, nw = fires_windowed(d.text, taxonomy, size)
            win_total += nw
            if f:
                win_fired += 1
        if not n:
            continue
        out[lens_id] = {
            "n_docs": n,
            "doc_fired": doc_fired,
            "doc_rate": round(doc_fired / n, 4),
            "win_fired": win_fired,
            "win_rate": round(win_fired / n, 4),
            "windows": win_total,
            "delta": round((win_fired - doc_fired) / n, 4),
        }
    return out


def by_length(lenses, docs, quartiles=4, window=None):
    """Firing rate per length quartile. THE QUESTION THE ISSUE IS ACTUALLY ASKING.

    Windowing turned out to change almost nothing (1 of 16 lenses, by under two points), which
    is a real answer but not to this. "Does a document fire if any window of it fires" is close
    to "does the whole document fire" by construction, because the whole-document index already
    aggregates the same cues.

    The defect issue #7 describes is different and simpler: **does firing probability rise with
    length?** If a hearing fires more than a public comment only because there is forty times
    more of it, that shows up here as a rate climbing across quartiles. If it does not climb,
    the 410x spread is a real property of the pool with no measurable effect on the null, and
    the honest close is to say so rather than to re-engineer the statistic.
    """
    ranked = sorted(docs, key=lambda d: len(d.text.split()))
    size = max(1, len(ranked) // quartiles)
    groups = [ranked[i * size:(i + 1) * size] for i in range(quartiles - 1)]
    groups.append(ranked[(quartiles - 1) * size:])

    out = {}
    for lens_id, taxonomy in sorted(lenses.items()):
        row = []
        for g in groups:
            fired = n = 0
            for d in g:
                try:
                    if window:
                        # THE DECISIVE TEST for candidate 2. If the windowed unit is
                        # length-invariant, the spread across these quartiles collapses.
                        hit = fires_windowed(d.text, taxonomy, window)[0]
                    else:
                        hit = B.index_of(d.text, taxonomy) > 0
                except Exception:
                    continue
                n += 1
                if hit:
                    fired += 1
            row.append({"n": n, "fired": fired,
                        "rate": round(fired / n, 4) if n else None,
                        "median_words": (sorted(len(d.text.split()) for d in g)[len(g) // 2]
                                         if g else 0)})
        out[lens_id] = row
    return out


def background_docs():
    """The background pool background_rate.py itself uses, so the two are comparable."""
    # role_of() returns the ROLES RECORD, not the role string. Comparing the dict to
    # "background" silently yielded an empty pool and this printed "nothing to measure" over a
    # corpus of 331 documents -- a filter that excludes everything looks exactly like a corpus
    # that is absent.
    return [d for d in documents(min_words=B.MIN_WORDS)
            if (B.role_of(d.origin) or {}).get("role") == "background"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--windowed", action="store_true",
                    help="use the windowed firing rule for --by-length")
    ap.add_argument("--by-length", action="store_true",
                    help="firing rate per length quartile -- the question the issue asks")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    docs = background_docs()
    if not docs:
        print("no background documents in this checkout -- nothing to measure")
        return 0

    lengths = sorted(len(d.text.split()) for d in docs)
    print("BACKGROUND POOL: %d document(s), %d to %d words (median %d)"
          % (len(lengths), lengths[0], lengths[-1], lengths[len(lengths) // 2]))
    print("  the 410x spread is the defect; a length-invariant unit is the fix under test")
    print("")

    if args.by_length:
        rows = by_length(lenses, docs, window=args.window if args.windowed else None)
        heads = rows[sorted(rows)[0]]
        print("FIRING RATE BY LENGTH QUARTILE -- %s unit (median words per quartile: %s)"
              % ("WINDOWED N=%d" % args.window if args.windowed else "per-document",
                 ", ".join(str(q["median_words"]) for q in heads)))
        print("  %-28s %8s %8s %8s %8s %9s" % ("lens", "Q1", "Q2", "Q3", "Q4", "Q4-Q1"))
        climbing = 0
        for lens_id in sorted(rows, key=lambda k: -(rows[k][3]["rate"] - rows[k][0]["rate"])):
            r = rows[lens_id]
            spread = r[3]["rate"] - r[0]["rate"]
            if abs(spread) >= 0.10:
                climbing += 1
            print("  %-28s %8.3f %8.3f %8.3f %8.3f %+9.3f%s"
                  % (lens_id, r[0]["rate"], r[1]["rate"], r[2]["rate"], r[3]["rate"], spread,
                     "  <-- length-dependent" if abs(spread) >= 0.10 else ""))
        print("")
        print("  %d of %d lens(es) differ by 10 points or more between the shortest and"
              % (climbing, len(rows)))
        print("  longest quartile. That is the size of the length bias in the published null.")
        return 0

    sizes = SWEEP if args.sweep else (args.window,)
    results = {}
    for size in sizes:
        results[size] = measure(size, lenses, docs)

    if args.json:
        print(json.dumps({"window_sizes": list(sizes), "results": results},
                         indent=2, ensure_ascii=False))
        return 0

    for size in sizes:
        r = results[size]
        moved = [(k, v) for k, v in sorted(r.items()) if v["delta"]]
        print("N = %d words, %.0f%% overlap" % (size, STRIDE_FRACTION * 100))
        print("  %-28s %10s %10s %8s" % ("lens", "per-doc", "per-window", "delta"))
        for lens_id, v in sorted(r.items(), key=lambda kv: -abs(kv[1]["delta"])):
            mark = "  <-- moves" if abs(v["delta"]) >= 0.05 else ""
            print("  %-28s %5d/%-4d %5d/%-4d %+8.3f%s"
                  % (lens_id, v["doc_fired"], v["n_docs"],
                     v["win_fired"], v["n_docs"], v["delta"], mark))
        print("  %d of %d lens(es) change at all; %d move by 5 points or more"
              % (len(moved), len(r),
                 sum(1 for _k, v in moved if abs(v["delta"]) >= 0.05)))
        print("")

    print("ADOPTS NOTHING. background_rate.py still owns the published rates; this prints the")
    print("comparison so issue #7 can be closed against data instead of taste.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
