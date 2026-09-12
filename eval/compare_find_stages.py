#!/usr/bin/env python
"""Cues vs embeddings, same corpus, same ground truth, same statistic.

The find stage is the part of the pipeline that is failing, and there are now two
candidates for it. This runs both against PTC's human character-span annotation and
reports the numbers side by side, so the choice is made on evidence rather than on which
architecture sounds more modern.

WHAT IS AND IS NOT A FAIR COMPARISON HERE

PTC is news. It is length-matched to the corpus the embedding thresholds were calibrated
on (long documents, multi-sentence windows), which the mirror-pair suite is NOT -- those
are single sentences, and a threshold derived from 3-sentence windows in 3,000-word
rulemaking does not transfer to them. So mirror results for the embedding stage are
reported separately and read with that caveat; this file is the length-matched test.

PTC is also EXHAUSTED as a tuning corpus for the cue stage: the 2026-08-26 cut was made
against a PTC-derived background, so the cue numbers here are partly self-fulfilling. The
embedding stage has never seen PTC. That asymmetry favours the cues, and it is stated
rather than corrected -- correcting it would mean re-tuning something, which is how the
first Goodhart happened.

METRICS, all three together as always: precision, lift over chance, and the absolute count
of human-annotated spans recovered. Precision alone is maximised by firing once.

    python tradecraft/eval/compare_find_stages.py --lens institutional_permeation
    python tradecraft/eval/compare_find_stages.py --limit 100 --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ptc_precision import covered, load_corpus            # noqa: E402

#: Permutation draws per hit for the length-matched null. 200 is plenty: the quantity
#: estimated is a single overlap probability per hit, and the per-lens average pools
#: thousands of them.
PERM_DRAWS = 200


def chance_for(spans, doc_len, hit_len, rng):
    """P(a randomly placed span of THIS length overlaps any annotation in THIS document).

    THE WHOLE POINT. `ptc_precision`'s chance rate is the fraction of CHARACTERS that sit
    inside an annotation -- correct when every hit is a short literal cue, and badly wrong
    the moment hits have different lengths. A 3-sentence embedding window is ~300 chars and
    overlaps something by luck far more often than a 10-char keyword does, so scoring both
    against one character-level baseline hands the window-based stage a large free lift.

    Measured here instead of assumed: drop a span of the same length at a uniformly random
    offset in the same document, see how often it lands on an annotation.
    """
    if not spans or hit_len <= 0 or doc_len <= hit_len:
        return 0.0
    hi = doc_len - hit_len
    n = 0
    for _ in range(PERM_DRAWS):
        a = rng.randrange(hi)
        if covered(spans, a, a + hit_len):
            n += 1
    return n / PERM_DRAWS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", action="append",
                    help="restrict to these lenses (default: all with cue hits)")
    ap.add_argument("--limit", type=int, default=0, help="first N articles only")
    ap.add_argument("--json", action="store_true")
    # DEFAULT READ FROM THE THRESHOLDS, not from the module constant.
    #
    # The docstring already warned that this MUST match the window the thresholds were
    # calibrated at "or the comparison is scoring one geometry against another's noise floor"
    # -- and then defaulted to None, which falls through to embed_find.WINDOW_SENTENCES = 3
    # while the committed thresholds.json records window_sentences = 1. So the documented
    # trap was the default behaviour. Caught 2026-09-03.
    #
    # A number that must agree with a file should be read from that file. Passing --window
    # explicitly still overrides, for the deliberate case of testing a different geometry.
    ap.add_argument("--window", type=int, default=None,
                    help="embedding window in sentences; defaults to whatever the committed "
                         "thresholds were calibrated at (they record it), because a mismatch "
                         "scores one geometry against another's noise floor")
    # THE THIRD ARM, added 2026-09-03. Cues are at a measured ceiling (97% of one lens's cues
    # never appear in this corpus; 3 of 140 detections beat chance) and the embedding stage
    # measured AT CHANCE on 2026-08-27. The LLM find stage is the only candidate that has
    # never been put on this benchmark, and it is where the Appeal_to_Authority and
    # Whataboutism disproofs independently pointed: both are unreachable by substring
    # matching because the signal is relational or sits outside the annotated span.
    #
    # Off by default. It is ~16s per article per lens against a local 14B, so the full 371 is
    # over an hour for ONE lens -- a cost worth paying deliberately and not by accident.
    ap.add_argument("--llm", action="store_true",
                    help="add the LLM find stage as a third arm (slow; local model)")
    ap.add_argument("--llm-model", default="huihui_ai/qwen2.5-abliterate:14b",
                    help="local model for the LLM arm")
    a = ap.parse_args(argv)

    from tradecraft.detect import detect, detect_cues
    from tradecraft.loader import load_lenses
    from tradecraft.embed_find import detect_embed, load_model, THRESHOLDS

    corpus = load_corpus()
    if a.limit:
        corpus = corpus[:a.limit]
    lenses = load_lenses(str(ROOT / "detectors"))
    if a.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(a.lens)}

    chance = (sum(e - s for d in corpus for s, e in d["spans"])
              / sum(len(d["text"]) for d in corpus))
    threshold_blob = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    thresholds = threshold_blob["thresholds"]
    if a.window is None:
        a.window = threshold_blob.get("window_sentences")
    calibrated_at = threshold_blob.get("window_sentences")
    if calibrated_at is not None and a.window != calibrated_at:
        print("  [embed] WINDOW MISMATCH: running at %s, thresholds calibrated at %s -- this "
              "scores one geometry against another's noise floor"
              % (a.window, calibrated_at), file=sys.stderr, flush=True)
    model = load_model()

    arms = ["cues", "embed"] + (["llm"] if a.llm else [])
    tally = {name: {lid: {"hits": 0, "inside": 0, "chance_sum": 0.0, "len_sum": 0}
                    for lid in lenses}
             for name in arms}
    import random
    rng = random.Random(20260827)          # fixed: the null must not move between runs
    t0 = time.time()
    for i, d in enumerate(corpus, 1):
        for lid, tax in lenses.items():
            staged = [("cues", _safe(detect_cues, d["text"], tax, _arm="cues")),
                      ("embed", _safe(detect_embed, d["text"], tax, model,
                                      thresholds, 12, a.window, _arm="embed"))]
            if a.llm:
                staged.append(("llm", _safe(detect, d["text"], tax, _arm="llm",
                                            backend="local", model=a.llm_model)))
            for name, hs in staged:
                for h in hs:
                    if h.char_start is None:
                        continue
                    t = tally[name][lid]
                    t["hits"] += 1
                    end = h.char_end or (h.char_start + len(h.span))
                    hl = max(1, end - h.char_start)
                    t["len_sum"] += hl
                    t["chance_sum"] += chance_for(d["spans"], len(d["text"]), hl, rng)
                    if covered(d["spans"], h.char_start, end):
                        t["inside"] += 1
        if i % 25 == 0:
            el = time.time() - t0
            print(f"  {i}/{len(corpus)} articles  {el/i:.2f}s/article  "
                  f"~{(el/i)*(len(corpus)-i)/60:.0f}m left", file=sys.stderr, flush=True)

    rows = []
    for lid in lenses:
        row = {"lens": lid}
        for name in arms:
            t = tally[name][lid]
            prec = (t["inside"] / t["hits"]) if t["hits"] else None
            mchance = (t["chance_sum"] / t["hits"]) if t["hits"] else None
            row[name] = {
                "hits": t["hits"], "inside": t["inside"],
                "mean_hit_chars": round(t["len_sum"] / t["hits"]) if t["hits"] else None,
                "precision": round(prec, 4) if prec is not None else None,
                "naive_lift": round(prec / chance, 3) if prec is not None else None,
                "length_matched_chance": round(mchance, 4) if mchance is not None else None,
                "lift": (round(prec / mchance, 3)
                         if prec is not None and mchance else None)}
        rows.append(row)
    rows.sort(key=lambda r: -(r["embed"]["hits"] + r["cues"]["hits"]))

    result = {
        "articles": len(corpus), "chance_precision": round(chance, 4),
        "caveat": ("PTC was used to tune the CUE stage (the 2026-08-26 cut used a "
                   "PTC-derived background), and has never been seen by the embedding "
                   "stage. The comparison therefore favours cues. Stated, not corrected."),
        "lenses": rows,
    }
    if a.json:
        print(json.dumps(result, indent=1))
        return 0
    print(f"\nPTC: {len(corpus)} articles, chance precision {chance:.4f}")
    print("  lift is LENGTH-MATCHED: precision divided by the measured chance that a span")
    print("  of the same length, dropped at random in the same document, hits an annotation.")
    print()
    print(f"  {'lens':<26} {'stage':<6} {'hits':>5} {'chars':>6} {'prec':>6} "
          f"{'chance':>7} {'LIFT':>6} {'naive':>6}")
    for r in rows:
        for name in arms:
            x = r[name]
            if not x["hits"]:
                print(f"  {r['lens'][:26]:<26} {name:<6} {0:>5}      -      -       -      -      -")
                continue
            lf = f"{x['lift']:.2f}" if x["lift"] else "  -  "
            nv = f"{x['naive_lift']:.2f}" if x["naive_lift"] else "  -  "
            print(f"  {r['lens'][:26]:<26} {name:<6} {x['hits']:>5} "
                  f"{x['mean_hit_chars']:>6} {x['precision']:>6.3f} "
                  f"{x['length_matched_chance']:>7.3f} {lf:>6} {nv:>6}")
    print("\ncaveat: " + result["caveat"])
    if FAILURES:
        print("")
        print("ARM FAILURES: %s" % ", ".join("%s=%d" % kv for kv in sorted(FAILURES.items())))
        print("A zero-hit arm with failures is an arm that never ran, not one that found")
        print("nothing. Read the counts above with that in mind.")
    return 0


#: Failures per arm, counted rather than swallowed. `_safe` returned [] on any exception, which
#: is survivable for an arm known to work and dangerous for a new one: an LLM arm whose every
#: call failed would report ZERO HITS and read as "found nothing" rather than "never ran". That
#: is the silent-failure shape this whole benchmark exists to avoid, so failures are now tallied
#: and printed, and the caller says which arm it is asking about.
FAILURES: dict[str, int] = {}


def _safe(fn, *args, _arm="?", **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        FAILURES[_arm] = FAILURES.get(_arm, 0) + 1
        if FAILURES[_arm] == 1:
            print("  [%s] first failure: %s: %s"
                  % (_arm, type(exc).__name__, str(exc)[:200]), file=sys.stderr, flush=True)
        return []


if __name__ == "__main__":
    sys.exit(main())
