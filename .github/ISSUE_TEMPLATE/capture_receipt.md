---
name: Capture receipt
about: Submit a sourced receipt of a capture move for the Capture Leaderboard
title: "receipt: <actor> — <short>"
labels: receipt
---

Paste the JSON from the Receipt Collector (https://evilrobots.lol/tech/receipt-collector/), or fill it by hand.

**Receipt (JSON):**

```json
{
  "claim": "",
  "actor": "",
  "action": "",
  "source_url": "",
  "archive_url": "",
  "tier": "FACT | ATTRIBUTED | RUMOR",
  "date": "",
  "submitter": ""
}
```

**Institution** (which captured institution this attaches to):

**Marker / move** (the METHOD, if known — e.g. `pseudonymous_enforcement` / `permeation`; leave blank if unsure):

---

*Maintainer — verify before merge (nothing merges unchecked):*
- [ ] `source_url` resolves and actually supports the claim
- [ ] `archive_url` present (or capture one — a receipt without an archive is a rumor with a date)
- [ ] tier honest: **FACT** = verified/sourced · **ATTRIBUTED** = an accusation, sourced to who made it · **RUMOR** = shown, never counted
- [ ] defamation-safe: accusation stated AS an accusation; no motive asserted
- [ ] symmetric standard: same evidentiary bar as every other faction, including our own
- [ ] mapped to a `leaderboard/data/leaderboard.jsonl` record (institution, marker, move, actor, assurance, severity, self_correction, span, source)
