# Pre-registration: a discipline-matched control corpus for the AI-governance misread

Written and committed **before** any document is fetched and before any occurrence is counted.
The corpus, the fetcher, and this file's predictions are frozen at commit time; the results file
(`RESULTS-2026-09-08-shoptalk-corpus.md`) names the commit and is written only after the numbers
exist.

## What is being repaired

`RESULTS-2026-09-07-cue-repair.md` ran a pre-registered cut rule over 17 candidate cues and
selected 4. **Thirteen were kept**, and the rule's own reasoning names why: the benign-ubiquity
gate is measured against the unannotated PTC background (news prose six annotators declined to
mark) and the general-prose pool (171 documents / 885.3 kwords, itself Federal Register notices,
congressional hearings, and public rulemaking comments) — and seven of the thirteen never occur
in either pool at all (`training pipeline`, `diffuse`, `arithmetic`, `proprietary model`, `a few
hundred`, `high score`, `in a bid to`), so the rule has no evidence to cut them on. That file's own
verdict: *"the way through is not a looser rule but a calibration corpus that contains the register
the collateral is written in — AI-governance prose."* That corpus does not exist yet. This builds
it.

## What register it covers, and what it deliberately excludes

**In scope:** AI-governance and AI-safety institutional shop-talk — the register in which a
frontier lab, a standards body, a governance think tank, or a legislator's witness discusses model
training, evaluation, deployment risk, and regulatory design in matter-of-fact, non-persuasive or
lightly-persuasive prose. This is NOT the tradecraft register the lenses were built to catch
(institutional permeation, reference capture, militant mobilization, and so on) — it is the
vocabulary of people doing the actual engineering and policy work of AI development, who happen to
use words like *pipeline*, *arithmetic*, *proprietary*, *diffuse*, *high score* (benchmark),
*human capital*, *existential* (risk), and *level playing field* (international competition) as
ordinary trade vocabulary rather than as the rhetorical moves those cues were written to detect.

**Source classes (four, each independently attributed):**

1. **AI-lab safety/policy blog posts** — Anthropic, OpenAI, Google DeepMind, Frontier Model Forum,
   METR: responsible-scaling policies, frontier safety frameworks, preparedness documents,
   red-teaming and evaluation writeups. Public, no login, no paywall.
2. **Governance think-tank pieces** — CSET (Georgetown), GovAI, RAND, Brookings, CNAS: published
   research posts and briefs on frontier AI governance, compute governance, and international
   coordination.
3. **Standards/framework text** — NIST AI RMF 1.0 and its Generative AI profile (US government
   work, public domain), OECD AI Principles, the Bletchley Declaration, the Hiroshima AI Process
   / G7 code of conduct: international and standards prose, not persuasive advocacy.
4. **Congressional-testimony-style policy prose** — govinfo.gov hearings on AI oversight,
   frontier-model risk, and AI national-security policy, fetched the same way
   `corpus/fetch_govinfo.py` already fetches advocacy prose (same API, same discipline, a new
   term list, a new output file so this corpus's provenance stays separate and auditable).

**Deliberately excluded:** Ian's own book manuscripts (any book, any series) — never used as
corpus or control. Anything behind a login or paywall. Anything I cannot attribute to a named
author/org, date, and a URL that resolves. No document is selected because it contains a
candidate cue phrase — that would be selection on the outcome, the exact trap
`background_rate.py`'s own docstring names and forbids. Documents are selected by topic/genre
only, the same discipline `fetch_govinfo.py` and `fetch_regulations.py` already use.

## Target size

A **bounded first pass**: 30–60 documents, aiming for roughly 40, spread across the four source
classes above (not evenly — blog posts and think-tank pieces run 500–3,000 words, standards and
hearing text run longer). Target total exposure: a few tens of thousands of words, enough to move
the occurrence-rate denominator meaningfully without pretending to be exhaustive. This is not
meant to settle the question for all time — it is meant to give the pre-registered cut rule a
first real chance to see this register at all.

## Where it lives, how it is fetched

- New file: `corpus/ai-governance-shoptalk.jsonl`, one JSON object per line: `{id, source_class,
  org, title, author, date, source_url, note, text}`. Every record carries a resolving URL and a
  fetch date.
- New fetcher: `corpus/fetch_ai_governance_shoptalk.py`, following the existing fetchers'
  discipline: serial requests only, one host at a time, a descriptive User-Agent naming this
  research and a contact URL, a fixed delay between requests, exponential backoff
  and a full stop (never a retry loop) on any 429, and a local cache so nothing is fetched twice.
  Blog/think-tank/standards pages are fetched by direct URL; congressional hearings reuse the
  govinfo API and content path exactly as `fetch_govinfo.py` does, with a new term list scoped to
  AI oversight and a new output file.
- Declared in `eval/background_rate.py`'s `ROLES` as `role: "background"`,
  `recomputable: True` — these documents are gathered by TOPIC (AI governance/safety), not by any
  lens's cue, which is exactly the property that qualifies a bucket as a ruler rather than a
  recall fixture. Every record's URL makes it reader-rebuildable.

## What is measured, in order, after the corpus is committed

1. `python eval/background_rate.py` (writes `background-rates.json`) and
   `python eval/occurrence_rate.py --write` — the new bucket enters the background pool that
   `cue_repair_eval.py`'s `Corpora.bg_docs` already reads from, with no code change to either
   tool.
2. A new repair-recheck plan, `CUE-REPAIR-2026-09-08-shoptalk-recheck.json`, carrying the
   **same 13 kept candidates, the same actions, and the identical rule** (`ptc_bg_min: 3`,
   `bg_min_occurrences: 3`, `exclude_min_read: 3`) as `CUE-REPAIR-2026-09-07.json` — nothing about
   the rule is loosened or tuned to this corpus's content. Run through
   `python eval/cue_repair_eval.py --plan CUE-REPAIR-2026-09-08-shoptalk-recheck.json`.
3. `python eval/ptc_precision.py --json` and `python eval/detection_census.py` before and after
   any `--apply`, exactly as the 2026-09-07 repair did.
4. `python eval/collateral_eval.py --check` (the 51-span frozen sample) re-run after any
   `--apply`, to see whether the corpus's evidence changes the collateral precision without
   dropping a construct-present span.
5. Every derived artifact regenerated if anything is applied: `lens-floors.json`,
   `detection-census.json`, `instrument.json`, the demo split — same list 2026-09-07 used.

## Predictions, scored honestly whichever way they land

| # | prediction | falsified if |
|---|---|---|
| P1 | At least 8 of the 13 candidate cues show **at least one** occurrence in the new corpus | fewer than 8 show any occurrence at all |
| P2 | At least 3 of the 13 clear `bg_min_occurrences >= 3` in this corpus alone | fewer than 3 clear it |
| P3 | `human capital` stays **KEPT** regardless of new corpus evidence, because Reader B already found the construct present in the collateral read (a guard the rule applies before ubiquity is even checked) | it is cut |
| P4 | `from within` stays **KEPT** regardless of new corpus evidence, because cutting it demotes the demonstrated `infiltrate-existing-institutions` detection | it is cut |
| P5 | At least 3 of the 13 flip from KEEP to CUT or REPLACE under the unchanged rule once this corpus's occurrences are added to the general-prose pool | fewer than 3 flip |
| P6 | `institutional_permeation`'s general-prose per-1k occurrence rate (from `occurrence_rate.py`) rises after the new bucket is added, because five of its own candidate cues (`training pipeline`, `diffuse`, `arithmetic`, `proprietary model`, `level playing field`) are exactly this register's ordinary vocabulary | the rate does not rise, or falls |
| P7 | Applying whatever the rule selects does **not** drop any collateral span either reader marked construct-present, and does not demote any PTC-demonstrated detection (the same non-negotiable guards as 2026-09-07) | any CP span is silenced, or any demonstrated detection is demoted |
| P8 | Collateral precision on the frozen 51/39-span sample rises measurably (a few points, not a step change) if anything is cut, because the corpus targets exactly the vocabulary class the collateral read already identified as cue-only | precision falls, or is unchanged when >=1 cue is cut |

## The decision rule for "did the ceiling move"

**The corpus lets the detector distinguish shop-talk from tradecraft** if P5 holds (>= 3 of 13
flip to CUT/REPLACE) and P7 holds (nothing real is lost) — that is real, usable evidence the
previous corpora could not supply, converted into a precision gain with the receipts to show it.

**It does not** if P5 is falsified — 0, 1, or 2 flips — meaning even a register-matched corpus
finds these phrases too rare or too contested (own PTC lift, reader-found construct, demonstrated
detections) to clear a rule built to protect against tuning to one complaint. That is a documented
null: the detector's false-fire vocabulary on this material is not resolved by more of this kind
of evidence, and the finding is written up as exactly that, not hidden or re-run until it looks
better.

## What must not happen

No threshold in the rule changes to fit what this corpus turns up. No cue is cut that the rule
would keep. No document is selected because it contains a candidate phrase. No book manuscript is
used as corpus or control. No fabricated document, source, quote, or URL — every record's
`source_url` is checked to resolve before it is written, and a source that stops resolving after
being fetched is kept with its fetch date rather than silently dropped. Internet discipline:
serial or at most two concurrent requests, one host at a time, cached and deduplicated, and any
429 is a stop-and-back-off, never a retry loop.
