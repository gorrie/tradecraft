# Receipt verifier — calibration results (2026-06-29)

## Why this exists

Grading the apparatus subjects' own X posts on the offline `cues` backend (single-word substring
matching) produced per-document "method markers" that were **mostly context-blind false positives** —
and two that fired on the **opposite** of the text's meaning. Publishing those as receipts on named
real people would be defamatory, trivially mockable, and a misrepresentation. The `cues` floor is a
high-recall *detector*, not a publishable grader for real-person receipts.

## The fix

`detect.verified_cue_receipts` = a find→verify pipeline. `detect_cues` finds candidates cheaply
(high recall); `verify_hit` then asks a context-reading backend (`auto`→cloud, fall back to local) a
narrow question per candidate — **genuine / incidental / opposite** — and keeps only `genuine`,
defaulting to rejection on any failure, refusal, or uncertainty. A false positive about a real person
is worse than a missed marker, so the bias is to drop.

Exposed to the graph tool as `ratchet_mcp.texts.verified_person_receipts` (the publishable path on top
of `grade_person_texts`; `cues` backend rejected — verification needs a context read).

## Live calibration (`eval/verify_eval.py`, backend=auto)

One synthetic **control** (an unambiguous there-is-no-alternative line) that must survive, plus the
**seven real X cases** that the `cues` floor false-flagged — all of which must drop.

| Case | Lens | Expected | Result |
|---|---|---|---|
| CONTROL: naked TINA ("adapt or be left behind") | inevitability_framing | KEEP | ✅ kept |
| Jack Clark — *"Change is inevitable. Autonomy is not"* | inevitability_framing | drop (nuanced) | ✅ dropped |
| Joanne Jang — *"harness engineering"* | institutional_permeation | drop (incidental) | ✅ dropped |
| Dan Hendrycks — anti-centralization / robocops | distributed_accountability | drop (opposite) | ✅ dropped |
| Renée DiResta — accusing others of a *"narrative"* | institutional_permeation | drop (opposite) | ✅ dropped |
| Zico Kolter — *"excited about the work"* | adept_speech | drop (incidental) | ✅ dropped |
| Beth Barnes — *"automatically-scoreable"* | distributed_accountability | drop (incidental) | ✅ dropped |
| Marius Hobbhahn — *"engineers / default"* | institutional_permeation | drop (incidental) | ✅ dropped |

**1 control kept, 7 real cases dropped, 0 false positives leaked, 0 lost control.** (`pytest
tests/test_verify.py` — 7 mocked-transport tests — covers the keep/drop/conservative-default logic
offline; full suite 108 passed.)

## The substantive finding

The verifier **corrected the analyst's own false positive**: even Jack Clark's tweet, which looked
like a clean inevitability marker, is on a context read a *nuanced juxtaposition* ("Change is
inevitable. Autonomy is **not**") — not a naked there-is-no-alternative claim. The verifier dropped it
with a reasoned rationale (confidence 0.8), and separately kept the unambiguous control, proving it is
context-aware rather than failing-closed.

Net: **zero publishable in-context markers came out of the short-tweet sample.** Tweets are noise for
these lenses; genuine method markers live in **longform** (essays, Substacks, testimony, org posts).
This is empirical justification for the monitoring backlog's **RSS-first** priority
(`gorrie/scripts/x/MONITORING-BACKLOG.md`): the longform feeds are where verified receipts will
actually come from.
