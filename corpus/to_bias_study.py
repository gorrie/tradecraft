#!/usr/bin/env python3
"""W4.3 — turn the bias study's model responses into a corpus the detector can grade.

THE INTERACTION THIS EXISTS FOR
-------------------------------
The two instruments measure each other. The bias study asks what a model says under pressure;
the tradecraft detector asks how a text operates. The bias study's `runs/` are the one corpus
this project GENERATES rather than obtains -- unlimited, unencumbered, no licence, no fetcher --
and it is the corpus the detector was aimed at in the first place.

It matters most for `cognitive_capture`, whose home genre is arguably model output itself. Every
other lens is starved of material by licensing; this one has a corpus that can be produced on
demand. It also gives every lens a fresh REGISTER: a move rare in public prose may be common in
RLHF prose, and that asymmetry is itself a barometer reading rather than a nuisance.

WHY IT DOES NOT WRITE INTO corpus/ BY DEFAULT
---------------------------------------------
`corpus/` is not a folder, it is a measurement population. Every floor, background rate and
cross-tab in this repo is defined over it, and dropping 8,000 model responses in would silently
redefine all of them -- the background pool would become mostly machine text, and every lens's
"how often does this fire by accident" would answer a different question than the one it was
asked.

So the default `--out` is outside it. If model output is ever to become part of the measured
population that is a deliberate decision, and `eval/background_rate.py` now FORCES it to be one:
an undeclared corpus file is a hard error there, so the file cannot be added without someone
writing down what role it plays and whether a reader can rebuild it.

WHAT IT KEEPS, AND WHY
----------------------
One document per response, carrying `model`, `condition` and `position`. Those are the arms of
the study, and a detector reading that pools them would answer "does this model use this move"
when the interesting question is "does this move appear MORE under pressure than without it".
Keeping the arms is what makes a comparison possible later; a flat dump of text would not.

Refusals and empty bodies are dropped and counted. A refusal is not a specimen of anything a
lens detects, and silently keeping them would inflate every denominator.

    python corpus/to_bias_study.py --list
    python corpus/to_bias_study.py --out ~/corpora/model-output.jsonl
    python corpus/to_bias_study.py --run 2026-05-25 --out ~/corpora/may.jsonl
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERIES = os.path.dirname(ROOT)
RUNS = os.path.join(SERIES, "research", "bias-study", "runs")

#: Below this a response is an acknowledgement or a refusal stub, not prose to grade.
MIN_WORDS = 25

#: Openers that mark a refusal rather than an answer. A refusal is a real finding for the bias
#: study -- it has a whole table -- and is not a specimen of any method the detector looks for.
REFUSAL_MARKERS = (
    "i can't", "i cannot", "i won't", "i'm not able", "i am not able",
    "i'm unable", "i am unable", "as an ai", "i don't feel comfortable",
    "i do not feel comfortable", "sorry, but i", "i must decline",
)


def looks_like_refusal(text):
    head = " ".join(text.lower().split())[:120]
    return any(head.startswith(m) or (m in head[:60]) for m in REFUSAL_MARKERS)


def run_dirs():
    return sorted(d for d in glob.glob(os.path.join(RUNS, "2*"))
                  if os.path.isdir(d) and glob.glob(os.path.join(d, "raw", "*.jsonl")))


def records(run_filter=None):
    """Yield (run, record) for every raw response, oldest run first."""
    for d in run_dirs():
        run = os.path.basename(d)
        if run_filter and run != run_filter:
            continue
        for path in sorted(glob.glob(os.path.join(d, "raw", "*.jsonl"))):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield run, json.loads(line)
                except ValueError:
                    continue          # a malformed line is a missing document, not a crash


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="show the runs available, then stop")
    ap.add_argument("--run", help="only this run directory")
    ap.add_argument("--out", help="JSONL destination (keep it OUTSIDE corpus/ -- see the "
                                  "module docstring)")
    ap.add_argument("--min-words", type=int, default=MIN_WORDS)
    args = ap.parse_args(argv)

    if not os.path.isdir(RUNS):
        print("no bias-study runs/ at %s" % RUNS)
        return 1

    if args.list:
        dirs = run_dirs()
        print("%d run dir(s) with raw responses:" % len(dirs))
        for d in dirs:
            n = sum(1 for _ in glob.glob(os.path.join(d, "raw", "*.jsonl")))
            print("  %-34s %d model file(s)" % (os.path.basename(d), n))
        return 0

    if not args.out:
        print("--out is required. Write OUTSIDE corpus/: adding model output to the measured")
        print("population silently redefines every floor and background rate in the repo.")
        return 1

    kept = 0
    dropped_short = dropped_refusal = dropped_failed = 0
    by_model, by_condition = {}, {}
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        for run, rec in records(args.run):
            if rec.get("ok") is False:
                dropped_failed += 1
                continue
            body = (rec.get("response_text") or "").strip()
            if not body:
                dropped_failed += 1
                continue
            if looks_like_refusal(body):
                dropped_refusal += 1
                continue
            if len(body.split()) < args.min_words:
                dropped_short += 1
                continue
            model = rec.get("model") or "unknown"
            cond = rec.get("condition") or "?"
            by_model[model] = by_model.get(model, 0) + 1
            by_condition[cond] = by_condition.get(cond, 0) + 1
            fh.write(json.dumps({
                "id": "%s::%s::%s" % (run, model, rec.get("question_id") or "?"),
                "title": "%s %s %s" % (model, cond, rec.get("question_id") or ""),
                "text": body,
                # The study's arms, kept so a later comparison can ask whether a move appears
                # MORE under pressure -- which is the question worth asking. Pooling them
                # answers a different and duller one.
                "model": model,
                "condition": cond,
                "position": rec.get("position"),
                "topic": rec.get("topic"),
                "run": run,
                "source_url": None,
                "note": ("Model output from the bias study's runs/. Generated, not obtained: "
                         "no licence, no fetcher, reproducible by re-running the study."),
            }, ensure_ascii=False) + "\n")
            kept += 1

    print("wrote %d document(s) -> %s" % (kept, args.out))
    print("  dropped: %d refusal(s), %d short (<%d words), %d failed/empty"
          % (dropped_refusal, dropped_short, args.min_words, dropped_failed))
    print("  %d model(s), conditions: %s"
          % (len(by_model), ", ".join("%s=%d" % kv for kv in sorted(by_condition.items()))))
    print("")
    print("This file is NOT part of the measured population. Adding it to corpus/ requires a")
    print("role entry in eval/background_rate.py ROLES -- an undeclared corpus file is a hard")
    print("error there, deliberately, so the decision has to be written down.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
