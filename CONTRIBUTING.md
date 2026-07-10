# Contributing

Tradecraft evolves through its **taxonomies**, not its code. Most contributions are: propose a new
detection, fix a false positive, or add a lens. The grader is deliberately small and stable.

## The two rules every contribution must satisfy

1. **Method, not ideology.** A detection must fire on *how* a text operates, regardless of whose
   side it is on. If a proposed detection would only ever flag one political team, it is mis-specified
   — rewrite it as the underlying method, or it will be rejected.
2. **Every detection carries a receipt.** A new detection needs at least one **gold example** with a
   **source** (a real, verifiable quote that the detection is meant to catch). No receipt, no merge.
   This is what keeps the project reproducible and honest.

## Propose a detection

Open a *Detection proposal* issue (template provided). Include: the marker it belongs to, an id, a
one-line definition of the **method**, cue phrases, and the gold example + source. If accepted, it
goes into `detectors/<lens>/taxonomy.yaml` with its weight.

## Report a false positive

Open a *False positive* issue with the text, which detection fired, and why it is incidental rhetoric
rather than tradecraft. False positives tune thresholds and cue lists — they are as valuable as new
detections. Remember the design: one marker firing is *expected*; the signal is **breadth × density ×
co-occurrence**, surfaced with spans for **human** judgment. The tool never renders a verdict.

## Add a lens

A lens is a single `detectors/<lens>/taxonomy.yaml`. Match the schema of the existing lenses, keep
markers method-based, give every detection a sourced gold example, and keep it on its **own axis** —
lenses are never blended into one number.

## Submit a receipt (the Capture Leaderboard)

The public [Capture Leaderboard](https://evilrobots.lol/tech/capture-leaderboard/) ranks institutions by
**verified capture receipts**. Anyone can submit one — this is the contribution path that grows the board:

1. **Build it** at [evilrobots.lol/tech/receipt-collector](https://evilrobots.lol/tech/receipt-collector/)
   (or open a *Capture receipt* issue by hand). The collector produces a portable receipt JSON and its
   Submit button opens a pre-filled `receipt`-labeled issue here.
2. **A maintainer verifies** it against the checklist in the issue template: `source_url` resolves and
   supports the claim, an `archive_url` exists, the tier is honest, it is defamation-safe (accusation stated
   AS an accusation), and the **same evidentiary bar** was applied that every faction gets — including our own.
3. **Map + merge:** an approved receipt becomes a `leaderboard/data/leaderboard.jsonl` record
   (`institution, marker, move, actor, assurance, severity, self_correction, span, source`); regenerate
   `leaderboard/leaderboard.json` and sync the site data copy; it deploys.

**Only FACT-tier receipts move a rank.** ATTRIBUTED (a sourced accusation) and RUMOR are shown on the board
and **never counted** — so nothing can be pretended-hidden, and nothing unverified inflates a score.
Method-not-ideology and receipts-not-reputation apply here exactly as they do to detections.

## Run the tests

```
pip install -r requirements.txt pytest
pytest
python -m tradecraft.cli demo   # offline output-shape check
```

The grader tests are pure and deterministic; keep them green.
