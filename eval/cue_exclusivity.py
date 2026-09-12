#!/usr/bin/env python
"""Per-lens cue exclusivity: the share of a lens's hits that come from ordinary vocabulary.

WHAT THIS IS FOR

Adding cues without a benchmark is how a detector silently gets worse. The PTC benchmark
supplies one, but it needs human span annotation, which exists for news and nothing else.
This is the same signal **without needing annotation at all** -- so it can be run against
any register, and it can be run before and after a cue edit to see whether the edit helped.

THE FINDING IT IMPLEMENTS

Measured 2026-08-26 against PTC lift (precision over chance, from ptc_precision.py):

    lift 2.16   50% of hits from generic cues   subculture_register
    lift 1.93   58%                             reference_capture
    lift 1.44   80%                             sourcing_asymmetry
    lift 1.19   93%                             institutional_permeation
    lift 0.22   89%                             narrative_management

Monotonic across the top four. The share of a lens's hits that come from phrases occurring
freely in ordinary prose predicts its discriminative power.

WHAT DOES *NOT* PREDICT IT, TESTED AND WRONG

Cue length. The hypothesis was that longer, more specific cues discriminate better. The
data says the opposite, cleanly: `narrative_management` has the LONGEST cues (3.25 mean
words, 2% single-word) and the WORST lift (0.22), while `subculture_register` has the
shortest and most single-word cues (2.16 words, 30% single) and the BEST lift (2.16).

The reason is that length is not specificity. `SHTF` is one token and appears essentially
nowhere outside prepper writing. `in an attempt to` is four tokens and appears everywhere.
The taxonomy's own docstring for `subculture_register` had it right all along -- "unlike a
repurposed common word, a coined tell IS the membership marker, so it is a high-precision
signal by construction" -- and the lens that follows that principle is the one that scores.

The flagship lens does not follow it. `institutional_permeation` draws 93% of its hits from
generic phrases: on PTC news its top five matches are `the media` (44 hits),
`national security` (37), `ongoing` (31), `movement` (30) and `judiciary` (20) -- 71% of all
its firing. Those are institution names, a topic, and two ordinary English words. The marker
concepts are sound; the cues standing in for them are keyword stubs.

READ IT AS A LEADING INDICATOR, NOT A VERDICT

A high generic share does not prove a lens is wrong; it proves the lens cannot distinguish
its target from ordinary prose *in the background register used*. Change the background and
the number changes, which is the point -- run it against the register a lens is actually
aimed at.

    python tradecraft/eval/cue_exclusivity.py                       # all lenses, PTC background
    python tradecraft/eval/cue_exclusivity.py --bg <dir-or-file>
    python tradecraft/eval/cue_exclusivity.py --lens institutional_permeation --worst 15
    python tradecraft/eval/cue_exclusivity.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT.parent
sys.path.insert(0, str(ROOT))

DEFAULT_BG = ROOT / "eval" / "ptc-background" / "bg_ptc_unannotated.txt"
PROBE = SERIES / "research" / "external" / "ptc" / "train-articles"

#: A matched phrase counts as GENERIC when it appears at least this often in the neutral
#: background. Three, not one: a single incidental appearance in 1.8M characters is not
#: evidence a phrase is common, and a threshold of one would flag almost everything.
GENERIC_MIN = 3


def load_bg(path: Path) -> tuple[str, list[str]]:
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if p.suffix in (".txt", ".md"))
        return "\n".join(p.read_text(encoding="utf-8", errors="replace").lower()
                         for p in files), [p.name for p in files]
    if not path.is_file():
        sys.exit(f"no background at {path}")
    return path.read_text(encoding="utf-8", errors="replace").lower(), [path.name]


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", default=str(DEFAULT_BG),
                    help="neutral background: a file or a directory of .txt")
    ap.add_argument("--probe", default=str(PROBE),
                    help="documents to run the detector over (default: PTC articles)")
    ap.add_argument("--lens", action="append")
    ap.add_argument("--worst", type=int, default=0,
                    help="also list this many worst-offending phrases per lens")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    from tradecraft.detect import detect
    from tradecraft.loader import load_lenses

    bg, bg_files = load_bg(Path(a.bg))
    probe_dir = Path(a.probe)
    if not probe_dir.is_dir():
        sys.exit(f"no probe corpus at {probe_dir}")
    docs = [p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(probe_dir.glob("*.txt"))]
    if not docs:
        sys.exit(f"no .txt documents in {probe_dir}")

    lenses = load_lenses(str(ROOT / "detectors"))
    if a.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(a.lens)}

    rows = []
    for lid, tax in sorted(lenses.items()):
        phrases = Counter()
        for text in docs:
            try:
                hs = detect(text, tax, backend="cues")
            except Exception:
                hs = []
            for h in hs:
                s = (getattr(h, "span", "") or "").lower()
                if s:
                    phrases[s] += 1
        hits = sum(phrases.values())
        generic = {p: n for p, n in phrases.items() if bg.count(p) >= GENERIC_MIN}
        gen_hits = sum(generic.values())
        rows.append({
            "lens": lid, "hits": hits,
            "distinct_phrases": len(phrases),
            "generic_phrases": len(generic),
            "generic_hit_share": round(gen_hits / hits, 4) if hits else None,
            "worst": [{"phrase": p, "hits": n, "bg_count": bg.count(p)}
                      for p, n in sorted(generic.items(), key=lambda kv: -kv[1])[:a.worst]],
        })

    result = {"background": {"files": bg_files, "chars": len(bg),
                             "generic_min": GENERIC_MIN},
              "probe": {"dir": str(probe_dir), "documents": len(docs)},
              "how_to_read": (
                  "generic_hit_share is the fraction of a lens's hits whose matched phrase "
                  f"also occurs >={GENERIC_MIN} times in the neutral background. Measured "
                  "against PTC lift it is monotonic across the top four lenses: 50% -> 2.16, "
                  "58% -> 1.93, 80% -> 1.44, 93% -> 1.19. Cue LENGTH does not predict lift "
                  "and was tested: the longest-cue lens has the worst lift. It is a leading "
                  "indicator against the background used, not a verdict on the lens."),
              "lenses": sorted((r for r in rows if r["hits"]),
                               key=lambda r: -(r["generic_hit_share"] or 0)),
              "no_hits": [r["lens"] for r in rows if not r["hits"]]}

    if a.json:
        print(json.dumps(result, indent=1))
        return 0

    b = result["background"]
    print(f"background: {b['chars']:,} chars from {b['files']}  (generic if seen >={GENERIC_MIN}x)")
    print(f"probe: {len(docs)} documents from {probe_dir.name}")
    print()
    print(f"  {'lens':<28} {'hits':>6} {'phrases':>8} {'generic':>8} {'generic hit share':>18}")
    for r in result["lenses"]:
        print(f"  {r['lens']:<28} {r['hits']:>6} {r['distinct_phrases']:>8} "
              f"{r['generic_phrases']:>8} {r['generic_hit_share']:>17.0%}")
        for w in r["worst"]:
            print(f"        {w['hits']:>4} hits  bg {w['bg_count']:>5}x  {w['phrase'][:48]!r}")
    if result["no_hits"]:
        print()
        print(f"  no hits on this probe corpus ({len(result['no_hits'])}): "
              f"{', '.join(result['no_hits'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
