#!/usr/bin/env python3
"""Run the labeled eval fixtures through the detector + grader.

Reports: did positives fire? did negatives stay quiet (false-positive check)? did the right
markers fire among the positives (coverage)? Usage:

    python eval/run_eval.py [backend]        # backend: auto (default) | cloud | local
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from tradecraft.loader import load_lenses          # noqa: E402
from tradecraft.detect import detect               # noqa: E402
from tradecraft.grader import grade_document_for_lens  # noqa: E402
from tradecraft import adapters                    # noqa: E402


def main() -> int:
    argv = sys.argv[1:]
    strict = "--strict" in argv          # CI gate: nonzero exit if any fixture fails
    argv = [a for a in argv if a != "--strict"]
    backend = argv[0] if argv else "auto"
    if backend == "cloud":   # detect() names the cloud backend "anthropic"
        backend = "anthropic"
    # The deterministic "cues" floor only matches literal cue phrases, so it cannot resolve
    # fixtures marked min_backend == "llm" — neither paraphrased positives it cannot fire on, nor
    # nuance-dependent negatives (e.g. a steel-man self-correction that names the capture action but
    # must be read as the immune response, not the capture). On the cues run those fixtures are
    # SKIPPED, not failed; every other backend (cloud/local/auto) asserts them all.
    floor_only = backend == "cues"

    lenses = load_lenses(os.path.join(REPO, "detectors"))
    with open(os.path.join(HERE, "fixtures.json"), encoding="utf-8") as fh:
        fixtures = json.load(fh)

    pos_hit = pos_total = neg_quiet = neg_total = cover_hit = cover_total = skipped = 0
    for fx in fixtures:
        if floor_only and fx.get("min_backend") == "llm":
            skipped += 1
            kind = "positive" if fx.get("should_fire") else "negative"
            print(f"[SKIP] {fx['id']:28} {fx['lens']:26} needs a model (min_backend=llm, {kind})")
            continue
        tax = lenses[fx["lens"]]
        hits = detect(fx["text"], tax, backend=backend)
        mr = grade_document_for_lens(tax, hits, adapters.token_estimate(fx["text"]))
        fired = bool(mr.markers_present)
        ok = fired == fx["should_fire"]
        cov = ""
        if fx["should_fire"]:
            pos_total += 1
            pos_hit += int(fired)
            if fx.get("expect_any"):
                c = any(m in mr.markers_present for m in fx["expect_any"])
                cover_total += 1
                cover_hit += int(c)
                cov = "  cover:OK" if c else "  cover:MISS"
        else:
            neg_total += 1
            neg_quiet += int(not fired)
        print(f"[{'PASS' if ok else 'FAIL'}] {fx['id']:28} {fx['lens']:26} "
              f"should={str(fx['should_fire']):5} fired={str(fired):5} idx={mr.index:6} "
              f"{mr.tier:24} {mr.markers_present}{cov}")

    print()
    print(f"positives fired:   {pos_hit}/{pos_total}")
    print(f"negatives quiet:   {neg_quiet}/{neg_total}   (false-positive check)")
    if cover_total:
        print(f"marker coverage:   {cover_hit}/{cover_total}   (an expected marker fired)")
    if skipped:
        print(f"skipped (need model): {skipped}   (run with cloud/auto/local to assert these)")
    print(f"backend: {backend}")
    failures = (pos_total - pos_hit) + (neg_total - neg_quiet)
    if strict and failures:
        print(f"STRICT: {failures} fixture(s) failed the gate")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
