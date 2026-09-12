#!/usr/bin/env python3
"""Grade the primary-source testing corpus across every lens, and report SYMMETRY.

The corpus (`corpus/specimens.jsonl`) holds real primary-source snippets labeled by pawl
(traditionalist / progressive / utilitarian / technocratic / green) and stance (self | about).
This runner grades every specimen under every lens and answers the question the synthetic
fixtures cannot: does a METHOD lens fire on the METHOD present, or does its firing track a
faction's political coding? A symmetric lens should not concentrate on one pawl.

    python eval/run_corpus.py [backend]     # backend: cues (default, offline) | auto | cloud | local
    python eval/run_corpus.py cues --md eval/corpus-report.md

Discipline: this is a diagnostic, not a verdict. A CONCENTRATED flag is a prompt to investigate
whether the concentration is in the TEXT (this pawl's specimens really do use the method more) or
in the LENS (a cue that only a left/right register trips). Flag with receipts; never a verdict.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from tradecraft.loader import load_lenses               # noqa: E402
from tradecraft.detect import detect                    # noqa: E402
from tradecraft.grader import grade_document_for_lens   # noqa: E402
from tradecraft import adapters                         # noqa: E402

NOTABLE = 35.0          # a lens is "firing meaningfully" on a specimen at/above this index
CONCENTRATION = 2.0     # max pawl-mean > CONCENTRATION x median-of-pawl-means => flag


def load_specimens() -> list[dict]:
    path = os.path.join(REPO, "corpus", "specimens.jsonl")
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main() -> int:
    argv = sys.argv[1:]
    md_path = None
    if "--md" in argv:
        i = argv.index("--md")
        md_path = argv[i + 1]
        del argv[i:i + 2]
    backend = argv[0] if argv else "cues"
    if backend == "cloud":
        backend = "anthropic"

    lenses = load_lenses(os.path.join(REPO, "detectors"))
    lens_ids = sorted(lenses)
    specimens = load_specimens()

    # grade[spec_id][lens_id] = (index, markers_present)
    grade: dict[str, dict[str, tuple]] = {}
    pawl_of = {}
    for sp in specimens:
        pawl_of[sp["id"]] = sp["pawl"]
        row = {}
        for lid in lens_ids:
            tax = lenses[lid]
            hits = detect(sp["text"], tax, backend=backend)
            mr = grade_document_for_lens(tax, hits, adapters.token_estimate(sp["text"]))
            row[lid] = (mr.index, mr.markers_present)
        grade[sp["id"]] = row

    lines: list[str] = []
    def emit(s: str = ""):
        print(s)
        lines.append(s)

    emit(f"# Corpus grading — backend: {backend}")
    emit(f"specimens: {len(specimens)}   lenses: {len(lens_ids)}")
    emit()

    # ---- per-specimen: which lenses lit, strongest first ----
    emit("## Per-specimen (lenses at/above notable, strongest first)")
    for sp in specimens:
        row = grade[sp["id"]]
        lit = sorted(((v[0], lid) for lid, v in row.items() if v[0] >= NOTABLE), reverse=True)
        desc = ", ".join(f"{lid} {idx:.0f}" for idx, lid in lit) or "(nothing notable)"
        emit(f"- **{sp['id']}** [{sp['pawl']}/{sp['stance']}] -> {desc}")
    emit()

    # ---- per-pawl x per-lens mean index ----
    pawls = sorted({sp["pawl"] for sp in specimens})
    pawl_lens_mean: dict[str, dict[str, float]] = defaultdict(dict)
    for lid in lens_ids:
        for pw in pawls:
            vals = [grade[sid][lid][0] for sid in grade if pawl_of[sid] == pw]
            pawl_lens_mean[lid][pw] = sum(vals) / len(vals) if vals else 0.0

    # ---- symmetry report ----
    emit("## Symmetry report")
    emit("For each lens that fires anywhere: mean index per pawl, and whether firing is")
    emit("CONCENTRATED in one pawl (a prompt to check the text vs the lens — not a verdict).")
    emit()
    flagged = []
    quiet = []
    for lid in lens_ids:
        means = pawl_lens_mean[lid]
        mx = max(means.values())
        if mx < NOTABLE:
            quiet.append(lid)
            continue
        nonzero = [v for v in means.values() if v > 0]
        med = median(nonzero) if nonzero else 0.0
        top = max(means, key=means.get)
        concentrated = (len([v for v in nonzero]) == 1) or (med > 0 and mx > CONCENTRATION * med)
        tag = "  <-- CONCENTRATED (%s)" % top if concentrated else "  (spread)"
        spread = "  ".join(f"{pw}:{means[pw]:.0f}" for pw in pawls)
        emit(f"- **{lid}**  [{spread}]{tag}")
        if concentrated:
            flagged.append((lid, top, mx))
    emit()
    emit(f"lenses firing (>= {NOTABLE:.0f} on some pawl): {len(lens_ids) - len(quiet)}")
    emit(f"quiet on this corpus: {len(quiet)}  ({', '.join(quiet) or 'none'})")
    if flagged:
        emit()
        emit("### To investigate (concentration != bias — check text vs lens):")
        for lid, top, mx in flagged:
            emit(f"- `{lid}` concentrates on **{top}** (mean {mx:.0f}). "
                 f"Is that pawl's specimen genuinely method-dense, or is a cue register-bound?")

    if md_path:
        with open(os.path.join(REPO, md_path) if not os.path.isabs(md_path) else md_path,
                  "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"\nwrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
