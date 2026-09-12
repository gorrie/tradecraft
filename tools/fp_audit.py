#!/usr/bin/env python3
"""False-positive audit: scan EVERY cue in the detector against a large general-English background.

A coined shibboleth should not appear in ordinary English. So: load every cue from every lens (or one
lens), and check whether it occurs in a big neutral background corpus (public-domain books + the benign
eval fixtures). Any cue that appears there is DUAL-USE and a false-positive risk — the same defect the
hand-written FP probes catch, but found automatically across the whole taxonomy at once. Reports each
risky cue with its background hit count so it can be cut or narrowed.

This is the systematic version of the manual FP-probe: it would have caught 'job guarantee', 'grid-down',
'RINO', and 'drain the swamp' without anyone thinking to write a probe for each.

Usage:
    python tools/fp_audit.py <corpus_dir>                 # audit all lenses
    python tools/fp_audit.py <corpus_dir> --lens subculture_register
    python tools/fp_audit.py <corpus_dir> --min-len 5     # ignore very short cues (acronyms) if noisy
"""
from __future__ import annotations
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from tradecraft.loader import load_lenses  # noqa: E402

def load_background(corpus_dir):
    """Concatenate the benign/background files named in manifest.json (_benign key), else all bg_*.txt."""
    texts = []
    man_p = os.path.join(corpus_dir, "manifest.json")
    files = []
    if os.path.exists(man_p):
        files = json.load(open(man_p, encoding="utf-8")).get("_benign", [])
    if not files:
        files = [f for f in os.listdir(corpus_dir) if f.startswith("bg_") or f == "_benign.txt"]
    for fn in files:
        p = os.path.join(corpus_dir, fn)
        if os.path.exists(p):
            texts.append(open(p, encoding="utf-8", errors="ignore").read().lower())
    return "\n".join(texts), files

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("--lens", default=None)
    ap.add_argument("--min-len", type=int, default=0, help="skip cues shorter than this many chars")
    a = ap.parse_args()
    bg, files = load_background(a.corpus_dir)
    if not bg:
        print("no background corpus found (need bg_*.txt / _benign.txt in corpus_dir)"); return 2
    print(f"background: {len(bg):,} chars from {files}\n")
    lenses = load_lenses(os.path.join(REPO, "detectors"))
    names = [a.lens] if a.lens else sorted(lenses)
    total_cues = flagged = 0
    for name in names:
        tax = lenses.get(name)
        if not tax:
            print(f"[skip] {name}: not found"); continue
        risky = []
        for m in tax.markers:
            for d in m.detections:
                for cue in getattr(d, "cues", []):
                    total_cues += 1
                    if len(cue) < a.min_len:
                        continue
                    c = cue.lower()
                    n = bg.count(c)
                    if n > 0:
                        risky.append((n, m.id, cue))
        if risky:
            flagged += len(risky)
            print(f"### {name} — {len(risky)} DUAL-USE cue(s) found in background:")
            for n, mid, cue in sorted(risky, reverse=True):
                print(f"    {n:4}x  {mid:26} {cue!r}")
            print()
    print(f"== audited {total_cues} cues across {len(names)} lens(es); {flagged} appear in background (review) ==")
    return 1 if flagged else 0

if __name__ == "__main__":
    sys.exit(main())
