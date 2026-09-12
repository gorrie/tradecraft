# The working detectors on the board institutions' OWN output — second collateral pass

**Pre-registration:** `PREREG-2026-09-07-collateral-pass2.md`, committed at `63d6ea4a` before any URL
was fetched. **Ruling:** `receipt-url-ruling.json` (`receipt_url_ruling.py`) — 194 (institution, URL)
pairs, 31 own / 9 own-archived / 4 own-landing / 150 third-party, 16 of 36 institutions with gradable
own output. **Rig:** `eval/collateral_pass2.py`. **Store:** `collateral-own-output.jsonl` — 39 unique
URLs fetched once, serially, 2026-09-07; 33 ok, 2 stub (<120 words), 3 non-text (PDF), 1 http 429
(not retried, per the pre-registered fetch discipline). **Taxonomy:** `1d4d3ada28d0034b` — the
cue-repair taxonomy (`PREREG-/RESULTS-2026-09-07-cue-repair.md`), not pass 1's. **Hand-read:** 42
spans, seed 20260908, both readers.

Grading run time 3 s (fetch already on disk). Nothing was tuned between the pre-registration and
this file.

## What ran, what did not

| detector | status |
|---|---|
| tradecraft `cues` backend, 14 text lenses (post-repair taxonomy) | **ran** |
| capture scanner — shipped `scanner.js` + `capture-cats.js`, through node (words floor 100 in force, plan item 3) | **ran** |
| tradecraft LLM find/verify stage (local 14B) | **not run** — GPU held by the detached Phase-1.2 measurement |
| bias study | not applicable |

## The one-line result

**34 own-output documents, 14 institutions, 112,486 words. 34 cue occurrences on `institutional_permeation`
and 230 on `subculture_register` — both above their general-prose background, alongside `reference_capture`
(18, above background).** The hand-read puts the construct behind **32 of 42** fired spans (76%,
both readers) — a precision more than **3x pass 1's 20%**, and the reason is composition, not a
better detector: 32 of the 42 sampled spans are Lenin's/the Comintern's own writing on marxists.org,
where `subculture_register` measures exactly what the text is. Strip that lens out and the picture
matches pass 1: `institutional_permeation`'s 6 sampled `civil society` hits (EU, EIP, FMF x3, SIO)
are cue-only in both readers' judgment. Stanford Internet Observatory's own output (the only
institution pass 1 reached) now fires — `institutional_permeation` above background, both its
documents Moderate on the scanner — so its board row stops being a null, as pre-registered.

## Lens table

*bg* = the same general-prose background pool (171 docs / 885.3 kwords), regenerated after the
cue repair. *detectable at* = the smallest multiple of the background rate this corpus's exposure
could show as "above background."

| lens | docs fired/34 | docs rate [W95] | bg docs rate | occ | per 1k [P95] | bg per 1k [95] | verdict | top detection (share) | one cue | in quotes | detectable at |
|---|---:|---|---:|---:|---|---|---|---|---|---:|---|
| `adept_speech` | 0 | 0 [0, .102] | .006 | 0 | 0 [0, .033] | .001 [.000, .006] | indistinguishable | — | no | 0 | 32.4× |
| `cognitive_capture` | 0 | 0 [0, .102] | .006 | 0 | 0 [0, .033] | .003 [.001, .010] | indistinguishable | — | no | 0 | 13.1× |
| `costly_signal` | 0 | 0 [0, .102] | 0 | 0 | 0 [0, .033] | 0 [0, .004] | indistinguishable | — | no | 0 | undefined (bg = 0) |
| `counterproductivity` | 1 | .029 [.005, .149] | 0 | 1 | .009 [.000, .050] | 0 [0, .004] | indistinguishable | institution-as-obstacle (1.0) | no | 0 | undefined (bg = 0) |
| `distributed_accountability` | 1 | .029 [.005, .149] | .023 | 1 | .009 [.000, .050] | .005 [.001, .012] | indistinguishable | authority-to-define-true (1.0) | no | 0 | 9.9× |
| `inevitability_framing` | 0 | 0 [0, .102] | .018 | 0 | 0 [0, .033] | .006 [.002, .014] | indistinguishable | — | no | 0 | 7.9× |
| **`institutional_permeation`** | 11 | .324 [.191, .492] | .123 | 34 | **.302 [.209, .422]** | .047 [.034, .065] | **above background** | intermediary-laundering (.91) | **YES** | 4 | 2.6× |
| `legibility` | 0 | 0 [0, .102] | .047 | 0 | 0 [0, .033] | .014 [.007, .024] | indistinguishable | — | no | 0 | 4.6× |
| `militant_mobilization` | 0 | 0 [0, .102] | .023 | 0 | 0 [0, .033] | .005 [.001, .012] | indistinguishable | — | no | 0 | 9.9× |
| `narrative_management` | 0 | 0 [0, .102] | .018 | 0 | 0 [0, .033] | .003 [.001, .010] | indistinguishable | — | no | 0 | 13.1× |
| **`reference_capture`** | 4 | .118 [.047, .266] | .105 | 18 | **.160 [.095, .253]** | .023 [.014, .035] | **above background** | state-corp-ip-edits (.39) | no | 9 | 3.5× |
| `rollback_asymmetry` | 0 | 0 [0, .102] | .018 | 0 | 0 [0, .033] | .003 [.001, .010] | indistinguishable | — | no | 0 | 13.1× |
| `sourcing_asymmetry` | 3 | .088 [.031, .230] | .181 | 6 | .053 [.020, .116] | .054 [.040, .072] | indistinguishable | unsourced-assertion (.83) | **YES** | 0 | 2.5× |
| **`subculture_register`** | 9 | .265 [.146, .431] | .064 | 230 | **2.045 [1.789, 2.327]** | .019 [.011, .031] | **above background** | marxist-situationist-tells (.84) | **YES** | 8 | 3.7× |

Three lenses one-cue-flagged: `institutional_permeation` on `civil society`, `sourcing_asymmetry`
on `unsourced-assertion`, `subculture_register` on `marxist-situationist-tells` (expected — that
detection alone carries 20 of its 23 cue types on this material).

## The hand-read — 42 spans, both readers

**Reader A** (Sonnet 5, the agent that ran the pass-2 grading rig) and **Reader B** (Opus, a fresh
general-purpose subagent given only the 42 span contexts, the six fired detections' taxonomy
definitions verbatim, and the fixed four-class codebook — not Reader A's verdicts, not the
occurrence tables, not these predictions, not pass 1's results). Verdicts and reasons:
`collateral-pass2-hand-read-A.json`, `collateral-pass2-hand-read-B.json`. Contexts:
`collateral-pass2.json` `precision_sample.rows`.

| | CP | CO | QA | UR | precision |
|---|---:|---:|---:|---:|---:|
| Reader A | 32 | 10 | 0 | 0 | **76.2%** |
| Reader B | 32 | 10 | 0 | 0 | **76.2%** |
| CP by **both** | 31 | | | | 73.8% |

**Agreement 40 of 42 (95.2%), Cohen's kappa = 0.87** (identical on the 4-class and binary
construct-present/not readings, since neither reader used QA or UR on this sample). Two
disagreements: **#2** (EIP's "bridged the gap between government and civil society" — B reads
the institution's self-description of its own bridging role as the intermediary-laundering
mechanism shown, A reads it as a stakeholder mention with no routing/no-principal-on-record shown)
and **#42** (Marcuse's "self-perpetuating" majority — A reads the passage as describing an
institution serving its own perpetuation over its founding mission, matching the definition
directly; B reads it as describing a self-perpetuating opinion majority rather than an
institution). Neither disagreement moves a lens's verdict.

No `sourcing_asymmetry` spans were drawn (expected value <1 of 40 given its 6-of-288-hit share
of the pooled draw; 0 came up). Its aggregate reading — 6 occurrences, indistinguishable from
background — stands unread at the span level this pass.

**By lens (42 spans):**

| lens | read | CP (A/B/both) | what fired |
|---|---:|---|---|
| `institutional_permeation` | 6 | 0 / 1 / 0 | `civil society` named as a stakeholder category across EU Code, EIP, FMF (×3), SIO — five straight CO/CO reads, one (#2, EIP) split |
| `subculture_register` | 32 | 30 / 30 / 30 | Lenin's and Stalin's own doctrinal vocabulary (`proletariat`, `bourgeoisie`, `class struggle`, `means of production`) deployed natively; `Second International` split CP/CO by whether the span does doctrinal work (denouncing it) or narrates organizational history |
| `reference_capture` | 2 | 2 / 2 / 2 | Marcuse's "liberating tolerance" (the taxonomy's own gold example) and a government-IP edit to a minister's own Wikipedia article — both textbook hits |
| `distributed_accountability` | 1 | 0 / 0 / 0 | "access authoritative sources" is media-literacy language pointing users outward, not the Code claiming its own gatekeeping authority |
| `counterproductivity` | 1 | 1 / 0 / 0 | split: Marcuse's "self-perpetuating" majority privileging vested interests over founding purpose |

## Predictions, scored

| # | prediction | result | holds? |
|---|---|---|---|
| Q1 | ≥12 institutions with ≥1 graded doc; ≥30 documents graded as text; ≥3 ruled URLs non-text/fail | 14 institutions; 34 documents; 4 non-text-or-failed (3 non-text + 1 http 429) | **holds** |
| Q2 | `legibility` above background on the pooled own-output docs | 0 occurrences, indistinguishable | **wrong** — the code-of-practice and rulemaking texts on hand don't trip it |
| Q3 | `institutional_permeation` above background on the Lenin/Comintern/Stalin documents | 1 occurrence on that corpus, indistinguishable (.015 per 1k vs .047 bg) | **wrong** — permeation doctrine's own texts don't use the vocabulary the lens cues on; `subculture_register` is what fires there |
| Q4 | `reference_capture` above background on Wikipedia's own pages; hand-read >40% construct there | lens above background (13 of 18 occurrences are Wikipedia's); the ONE Wikipedia span drawn in the sample is CP by both readers (100% of n=1) | **holds, on thin evidence** — only one Wikipedia span was sampled |
| Q5 | scanner ≥90% Low; marxists.org texts the exception (Moderate/High) | 27/34 Low (79.4%, below 90%); the three High-band texts are NewsGuard (1) and the EU Code of Practice (2) — the marxists.org texts are all Low | **wrong on both counts** — the anti-disinformation institutions trip the scanner's own vocabulary; the Marxist canon does not |
| Q6 | hand-read precision on the pooled sample between 25% and 50% | **76.2%** (both readers) | **wrong — above the band** |
| Q7 | SIO's own output fires at least one lens | `institutional_permeation` above background (6 occurrences, both documents Moderate on the scanner) | **holds** |
| Q8 | the `existential risk`/`existential crisis` exclusion suppresses zero occurrences here | `institutional_permeation`'s 34 occurrences carry no `existential` cue at all (detections: astroturf 2, intermediary-laundering 31, irreversibility-framing 1) | **holds** |

Four hold (one thinly), four wrong. The misses cluster: the pass-1-derived expectation that
"home-register" documents would land in a moderate 25-50% band undershot because one institution's
primary-source ideological corpus (68,108 of 112,486 words) is not merely home-register but the
literal founding texts of the register `subculture_register` measures — a different thing from
AI-governance actors occasionally using AI-governance vocabulary. `legibility` and
`institutional_permeation`-on-Leninism both predicted a lens firing on a text because of its
subject matter; both were wrong, because subject matter and register are not the same axis, which
is exactly `subculture_register`'s design principle being demonstrated by its neighbors' failure to
generalize it.

## Failure modes, named

1. **Composition dominates the pooled precision number.** 32 of 42 sampled spans (76%) are one
   institution's 68,108-word primary-source corpus on one lens built to measure exactly that
   register. A pooled hand-read precision is not comparable across passes unless the pool's
   composition is reported alongside it — which this table now does.
2. **`civil society` is still cue-only vocabulary**, exactly as the cue repair found and declined
   to cut (not benign-ubiquitous enough in PTC/general-prose to clear the rule, but ubiquitous in
   this register): 5 of 6 sampled hits (both readers) are ordinary multi-stakeholder boilerplate
   across four different institutions, none showing the routing-without-a-principal mechanism the
   definition names.
3. **Subject-matter lenses do not fire on their own subject matter.** `institutional_permeation`
   (seeded from permeation doctrine) and `legibility` (seeded from legibility-as-control theory)
   were both predicted to fire on texts that are literally about their seed concept, and both
   stayed at or near zero. The lenses cue on modern institutional-capture vocabulary, not on the
   classical political-theory vocabulary the concepts were named after.
4. **The scanner's "High" band tracks the anti-disinformation genre, not the authoritarian one.**
   NewsGuard's own press release and the EU's own Code of Practice on Disinformation are the three
   High-band texts (74, 72, 70 degree) — pages about misinformation necessarily use the scanner's
   loaded vocabulary densely. The Leninist and Stalinist primary sources, despite being the corpus
   a reader would expect to trip a censorship/control detector, score Low throughout.
5. **One-cue dominance, twice more.** `sourcing_asymmetry`'s 6 occurrences are 83% one detection
   (`unsourced-assertion`); `subculture_register`'s 230 are 84% one detection
   (`marxist-situationist-tells`) — expected and correct here, since that detection's whole job is
   this exact register, unlike the arm-effect finding this flag caught elsewhere.

## Board institutions

- **Stanford Internet Observatory**: no longer a null (pass 1: nothing fired). Own output — the
  EIP report and the Virality Project page, 1,973 words — puts `institutional_permeation` above
  background (6 occurrences, `.83` intermediary-laundering share); both documents score Moderate
  on the scanner.
- **13 more institutions graded**: Behavioural Insights Team, EU AI Office, EU Code of Practice on
  Disinformation, Election Integrity Partnership, Frontier Model Forum, the Leninist/Comintern
  corpus, the New Left (Marcuse), NewsGuard, the SPI-B behavioural subgroup, the Soviet Communist
  Party corpus, the US AI Safety Institute, Wikipedia (English), and the World Health Organization.
  **4 fired nothing at all** (zero occurrences on every lens): Behavioural Insights Team, SPI-B, the
  US AI Safety Institute, the World Health Organization. EU AI Office fired once
  (`institutional_permeation`, indistinguishable from background) so it is graded, not null.
- **2 of the 16 ruled-own institutions graded zero documents**: Scientific publishing (one 48-word
  stub, one non-text SEC filing) and the US FDA (one non-text PDF). **2 more are entirely
  own-landing, not graded**: ExxonMobil (the ClimateFiles archive indexes; the documents themselves
  are PDFs one level down) and the public-relations industry / Bernays (archive.org and Gutenberg
  landing pages; the primary text is not on the page).
- **20 of 36 institutions**: no own output on the ledger at all; unchanged from the ruling.

## What this changes, and what it does not

- **Nothing in `floors.json`, the taxonomy, or any threshold changes.** This is a read, not a tune.
- THE RECORD's board and dossier surfaces are not yet updated with a pass-2 block — that is an
  `export_web.py` / `build_record.py` wiring change flagged for the author, parallel to how pass 1's
  `#/collateral` block was wired after its own results file existed. Doing it here would be a
  second decision (which institutions' rows point to which pass) folded into a results file rather
  than reviewed on its own.
- The 20 institutions with no own output on the ledger, and the 2 that graded to nothing, stay
  exactly as flagged in the pre-registration: not gone looking for.

## Reproduce

```bash
python tradecraft/eval/receipt_url_ruling.py --check   # the ledger's own/third-party ruling
python tradecraft/eval/collateral_pass2.py              # grade the stored texts (no network)
python tradecraft/eval/collateral_pass2.py --check       # exit 0: committed JSON matches a fresh run
python tradecraft/eval/collateral_pass2.py --markdown    # the tables above, recomputed
```
