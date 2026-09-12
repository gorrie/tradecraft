"""Measure PTC lift through the FULL pipeline -- find(cues) then verify(model).

THE QUESTION THIS SETTLES

Every precision number this project published before 2026-08-26 measured the cue matcher
alone. `ptc_precision.py` calls `detect(..., backend="cues")`; so does `cue_exclusivity.py`.
On that evidence the cue repair cut 34 cues for firing too often in ordinary prose,
including the pejorative labels `regime`, `far-right`, `hardline` and `extremist` -- and
`CUE-REPAIR-PLAN.md` step 3 wrote those off as an engine limit, because separating an
attributed label from an asserted one needs context that `detect_cues` does not have.

That is a description of the verifier, which already existed and had no shipping caller. So
the pipeline was measured, tuned, and cut down at half its length.

MODE IS THE WHOLE STORY -- READ THIS BEFORE TRUSTING A NUMBER FROM HERE

The first run of this script used author mode and rejected 94% of institutional_permeation
hits and 100% of sourcing_asymmetry hits. That looked like "the verifier does not work". It
was not. Author mode asks *is the DOCUMENT'S AUTHOR employing this method?* -- and in a news
article the author is a reporter quoting a politician, so "attributed to a third party" is
the honest answer and the hit dies. PTC's annotators marked the span wherever it occurred,
without caring who spoke it.

So `--mode instance` is the DEFAULT here: is this span an instance of the technique as it
appears, whoever produced it. That is the question the corpus answers. Author mode remains
available and is the right question for a self-audit, where the document IS the subject.

WHAT IT REPORTS, AND THE TRAP IT AVOIDS

Precision is trivially maximised by rejecting everything, so precision alone would make a
broken verifier look perfect. Three numbers, always together:

    cues-only      precision and lift over chance, on the sampled hits
    verified       the same, keeping only verdict == 'genuine'
    recall cost    how many hits that DID land in a human annotation were rejected

A verifier that doubles lift while discarding 90% of true positives has not improved the
instrument. Read the absolute retained count, not just the ratio.

SAMPLING IS DETERMINISTIC AND DISCLOSED

Every k-th hit in corpus order -- no seed, no shuffle, reproducible by anyone with the
corpus, and it cannot be re-rolled until the answer improves. `-n 0` verifies every hit.
Verdicts are cached (keyed on lens, detection, span, context window, MODE and that mode's
prompt version) so a re-run after a cue edit only pays for what changed.

    python tradecraft/eval/verified_precision.py --lens sourcing_asymmetry -n 0
    python tradecraft/eval/verified_precision.py --lens institutional_permeation --mode author
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ptc_precision import covered, load_corpus          # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", action="append", required=True)
    ap.add_argument("-n", "--sample", type=int, default=120,
                    help="model calls per lens (every k-th hit, corpus order); 0 = all")
    ap.add_argument("--backend", default="local")
    ap.add_argument("--mode", default="instance", choices=("author", "instance"),
                    help="author = is the DOCUMENT'S AUTHOR employing the method (self-audit); "
                         "instance = is the span the technique as it appears, whoever produced "
                         "it (detection). Default instance: PTC annotates spans regardless of "
                         "speaker, so author mode measures a question the corpus never asked.")
    ap.add_argument("--model", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cache", default=str(ROOT / "eval" / "cache" / "ptc-verdicts.json"),
                    help="reuse verdicts across runs; --no-cache to disable")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args(argv)

    from tradecraft.detect import detect, verify_hit
    from tradecraft.loader import load_lenses
    from tradecraft import verdicts as vc
    from tradecraft.verdicts import context_window

    # A verification pass is tens of minutes. Re-running the measurement after a cue edit
    # should only re-pay for what changed, or nobody re-runs it -- and a measurement that
    # is too expensive to repeat stops being a check and becomes a citation.
    cache_path = None if a.no_cache else Path(a.cache)
    cache = vc.load(cache_path) if cache_path else {}
    if cache:
        print(f"reusing {len(cache)} cached verdicts from {cache_path.name}", file=sys.stderr)

    corpus = load_corpus()
    lenses = load_lenses(str(ROOT / "detectors"))
    chance = (sum(e - s for d in corpus for s, e in d["spans"])
              / sum(len(d["text"]) for d in corpus))

    rows = []
    for lid in a.lens:
        tax = lenses[lid]
        pool = []
        for d in corpus:
            for h in detect(d["text"], tax, backend="cues"):
                if h.char_start is None:
                    continue
                pool.append((d, h, covered(d["spans"], h.char_start,
                                           h.char_start + len(h.span))))
        if not pool:
            continue
        # -n 0 means "every hit", not "divide by zero".
        step = max(1, len(pool) // a.sample) if a.sample else 1
        samp = pool[::step][:a.sample] if a.sample else pool
        print(f"{lid}: {len(pool)} hits, verifying every {step}th ({len(samp)}) "
              f"on {a.backend}...", file=sys.stderr)

        kept_in = kept_out = rej_in = rej_out = errors = 0
        t0 = time.time()
        for i, (d, h, inside) in enumerate(samp, 1):
            win = context_window(d["text"], h.char_start, h.span)
            ck = vc.key_for(lid, h.detection_id, h.span, win, a.mode)
            hit_cache = cache.get(ck)
            if hit_cache:
                verdict = hit_cache["verdict"]
            else:
                try:
                    v = verify_hit(win, tax, h, backend=a.backend, model=a.model,
                                   mode=a.mode)
                except Exception as e:
                    errors += 1
                    print(f"  error {type(e).__name__}: {e}", file=sys.stderr)
                    continue
                if v.get("ok") is False:
                    # An unreachable backend must not be recorded as a rejection, or a dead
                    # model shows up in the results as a verifier with perfect precision.
                    errors += 1
                    print(f"  backend: {v.get('error')}", file=sys.stderr)
                    continue
                verdict = str(v.get("verdict", "")).strip().lower()
                cache[ck] = {"verdict": verdict, "lens": lid, "mode": a.mode,
                             "detection": h.detection_id, "span": h.span,
                             "confidence": v.get("confidence"),
                             "rationale": (v.get("rationale") or "")[:400]}
                if cache_path and len(cache) % 20 == 0:
                    vc.save(cache_path, cache)   # a long run WILL be interrupted
            if verdict == "genuine":
                kept_in += inside
                kept_out += (not inside)
            else:
                rej_in += inside
                rej_out += (not inside)
            if i % 20 == 0:
                el = time.time() - t0
                print(f"  {i}/{len(samp)}  {el/i:.1f}s/hit  "
                      f"~{(el/i)*(len(samp)-i)/60:.0f}m left", file=sys.stderr, flush=True)

        n = kept_in + kept_out + rej_in + rej_out
        kept = kept_in + kept_out
        cues_prec = (kept_in + rej_in) / n if n else None
        ver_prec = kept_in / kept if kept else None
        rows.append({
            "lens": lid, "hits_total": len(pool), "sampled": n, "errors": errors,
            "cues_only": {"precision": round(cues_prec, 4) if cues_prec else None,
                          "lift": round(cues_prec / chance, 3) if cues_prec else None},
            "verified": {"kept": kept,
                         "keep_rate": round(kept / n, 4) if n else None,
                         "precision": round(ver_prec, 4) if ver_prec else None,
                         "lift": round(ver_prec / chance, 3) if ver_prec else None},
            "recall_cost": {
                "in_span_hits": kept_in + rej_in,
                "in_span_kept": kept_in,
                "in_span_rejected": rej_in,
                "retention": round(kept_in / (kept_in + rej_in), 4) if (kept_in + rej_in) else None},
        })

    if cache_path:
        vc.save(cache_path, cache)
    result = {
        "chance_precision": round(chance, 4),
        "backend": a.backend,
        "mode": a.mode,
        "how_to_read": (
            "cues_only is the find stage alone -- what every previously published number "
            "measured. verified keeps only verdict=='genuine'. Read the two lifts TOGETHER "
            "with recall_cost.retention: precision is trivially maximised by rejecting "
            "everything, so a lift gain is only real if retention stays high. A verifier "
            "that doubles lift while retaining a third of the human-annotated hits has "
            "traded the instrument's recall for a better-looking number."),
        "lenses": rows,
    }
    if a.json:
        print(json.dumps(result, indent=1))
        return 0
    print(f"\nchance precision {chance:.4f}")
    for r in rows:
        c, v, rc = r["cues_only"], r["verified"], r["recall_cost"]
        print(f"\n  {r['lens']}  ({r['sampled']} of {r['hits_total']} hits sampled"
              + (f", {r['errors']} errors" if r["errors"] else "") + ")")
        print(f"    cues only   precision {c['precision']:.4f}   lift {c['lift']:.2f}")
        if v["precision"] is not None:
            print(f"    + verify    precision {v['precision']:.4f}   lift {v['lift']:.2f}"
                  f"   (kept {v['kept']}, {v['keep_rate']:.0%} of hits)")
        else:
            print("    + verify    rejected every sampled hit -- no precision to report")
        print(f"    recall cost {rc['in_span_kept']}/{rc['in_span_hits']} human-annotated "
              f"hits retained"
              + (f" ({rc['retention']:.0%})" if rc["retention"] is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
