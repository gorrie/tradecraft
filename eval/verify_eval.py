"""LIVE calibration of the receipt verifier against real, documented cases.

Background: grading the apparatus subjects' own posts on the offline `cues` backend produced receipts
that were mostly context-blind false positives — and two that fired on the OPPOSITE of the text's
meaning. Publishing those on named real people would be defamatory and trivially mockable. The verifier
(detect.verified_cue_receipts) is the fix: it keeps a cue hit only if a context read confirms the AUTHOR
genuinely employs the method, defaulting to rejection.

This eval runs the verifier against the actual cases found in the ratchet texts store (2026-06):
one TRUE positive that must survive, and six documented false positives that must be dropped. It hits a
LIVE backend (auto -> cloud, fall back to local), so it is NOT part of the offline CI suite — run it on
demand:  python eval/verify_eval.py [--backend auto|cloud|local]

Verbatim texts are quoted from the subjects' public posts (URLs in the ratchet texts store). They are
included here as evidence fixtures, not as characterizations.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from tradecraft.loader import load_lenses          # noqa: E402
from tradecraft.detect import verified_cue_receipts  # noqa: E402

# Merge ~/.claude/agents/.env (OpenRouter key) into the environment, like the other live tools.
ENV = os.path.expanduser("~/.claude/agents/.env")
if os.path.exists(ENV):
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# (label, lens, expect_receipt, verbatim text)
#
# Finding (2026-06-29): of the apparatus X sample, ZERO short posts yielded a publishable in-context
# marker — including Jack Clark's, which on a context read is a nuanced juxtaposition ("Change is
# inevitable. Autonomy is NOT"), not a naked there-is-no-alternative claim. The verifier dropped it
# with a reasoned rationale, correcting the analyst's own false positive. The must-keep case is
# therefore a clear CONTROL (an unambiguous adapt-or-perish line); it proves the verifier still keeps
# genuine markers and is not merely failing-closed. Real takeaway: tweets are noise for these lenses;
# genuine markers live in LONGFORM (the monitoring backlog's RSS-first priority).
CASES = [
    # CONTROL — an unambiguous there-is-no-alternative line; must SURVIVE (proves the verifier keeps
    # genuine markers, not just rejects everything). Synthetic control, not attributed to anyone.
    ("CONTROL: naked TINA (KEEP)", "inevitability_framing", True,
     "Resistance is pointless. AI is coming whether you like it or not, the trend is unstoppable, "
     "and you must adapt or be left behind."),
    # Real X cases — ALL must be DROPPED (incidental, or fires opposite to the text's meaning).
    ("Jack Clark (drop: nuanced)", "inevitability_framing", False,
     'I will be giving a lecture in Oxford on May 20th called "Change is inevitable. '
     'Autonomy is not". Excited for people to hear it, and I hope to publish it afterwards as well.'),
    ("Joanne Jang (drop: incidental)", "institutional_permeation", False,
     "omg he was harness engineering"),
    ("Dan Hendrycks (drop: opposite)", "distributed_accountability", False,
     "Robocops would dangerously centralize power. To overthrow a tyrant, the police must defect. "
     "Human officers might refuse to fire on a crowd that includes their neighbors and their children. "
     "But robocops will not have any of these sympathies and will execute the order."),
    ("Renee DiResta (drop: opposite)", "institutional_permeation", False,
     "The Free Press let a whiner spin nonsense about his book review being censored -- supposedly, "
     "by me. They promoted the narrative heavily. When they were shown emails proving this narrative "
     "was bs, they chose to ignore them -- protecting their friend and their story over the facts."),
    ("Zico Kolter (drop: incidental)", "adept_speech", False,
     "How do you balance repeat training on high quality data versus adding more low quality data to "
     "the mix? @pratyushmaini and @goyalsachin007 provide scaling laws. Really excited about the work!"),
    ("Beth Barnes (drop: incidental)", "distributed_accountability", False,
     "there's an exponential trend with doubling time between ~2-12 months on automatically-scoreable, "
     "relatively clean + green-field software tasks from a few distributions"),
    ("Marius Hobbhahn (drop: incidental)", "institutional_permeation", False,
     "Coding agents should be treated as untrusted by default. We built Watcher as an MDM/EDR for "
     "coding agents. Security teams set hard boundaries (blocked commands, req. monitors), engineers "
     "set the rest."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="auto", choices=["auto", "cloud", "local"])
    args = ap.parse_args()

    lenses = load_lenses(os.path.join(REPO, "detectors"))
    print(f"Receipt verifier — live calibration (backend={args.backend})\n")
    tp = fp = fn = tn = 0
    for label, lens_id, expect, text in CASES:
        tax = lenses[lens_id]
        kept = verified_cue_receipts(text, tax, backend=args.backend)
        got = bool(kept)
        ok = (got == expect)
        if expect and got:
            tp += 1
        elif expect and not got:
            fn += 1
        elif not expect and got:
            fp += 1
        else:
            tn += 1
        mark = "PASS" if ok else "**FAIL**"
        detail = f"{len(kept)} receipt(s)" + (f": {kept[0].span!r}" if kept else "")
        print(f"  [{mark}] {label:34} {lens_id:26} -> {detail}")
    print(f"\n  kept-true {tp}  dropped-false {tn}  | leaked-false-positive {fp}  lost-true {fn}")
    print("  GOAL: 1 control kept, 7 real cases dropped, 0 leaked-false-positive, 0 lost-control.")
    return 0 if (fp == 0 and fn == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
