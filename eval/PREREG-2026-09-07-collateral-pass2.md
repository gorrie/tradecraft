# Pre-registration: collateral, second pass — the board institutions' own output

Written and committed **before** any URL is fetched. The results file
(`RESULTS-2026-09-07-collateral-pass2.md`) names the commit. Rig: `eval/collateral_pass2.py`,
which imports the first pass's grading, rulers and sampling unchanged; smoke-tested only on
`--help` and on loading the ruling. Nothing fetched, nothing graded.

## The question the first pass could not answer

Pass 1 read the record's texts-by-person store and reached **one** of 36 board institutions. The
board's other 35 rows say *no collateral on hand*. The ledger's receipts include the institutions'
own documents — policy pages, codes of practice, a party congress's resolutions, a forum's founding
statement — and those are the material a "what does the institution's own output exhibit" reading
requires. This pass grades exactly that, and nothing else.

## The ruling, made before this file (`receipt_url_ruling.py`, `receipt-url-ruling.json`)

Every one of the ledger's 194 (institution, URL) pairs is ruled by five ordered rules — Wayback
unwrap; per-URL override with reason; own host; archived primary text of the institution's
principals/organs; archive landing page — and defaults to **third-party**. Result: **31 own, 9
own-archived, 4 own-landing (text not on the page, ruled own, not graded), 150 third-party; 16 of
36 institutions have gradable own output.** The rules and every override's reason are in the
script's header and the JSON; `--check` fails if the ledger and the JSON drift. Three rulings a
reader might dispute, stated: the Frontier Model Forum's launch statement on two founders' blogs is
ruled the forum's own founding text; a Nature *news* article on publishing is ruled own for the
"big-five oligopoly" row because Nature is one of the five (caveat carried on the row); Lenin's,
the Comintern's and Stalin's texts on marxists.org and Marcuse's essay on marcuse.org are ruled the
institution's own words on the principle that hosting is not authorship.

## What is fixed

| parameter | value | why |
|---|---|---|
| material | every URL ruled `own` or `own-archived`; landing pages and third-party never fetched for grading | the ruling is the boundary |
| fetch | once, serial, 2.0 s apart, `fetch_manifest.UA`, cap 60, 45 s timeout; non-text (PDF, binary) skipped and counted; under 120 words counted as a stub; HTTP 429 backs off 30 s and does not retry; Wikipedia through the MediaWiki parse API + `mediawiki.plain()` | the project's standing fetch discipline; Wikipedia's chrome would otherwise be graded as Wikipedia's prose |
| store | `collateral-own-output.jsonl` — extracted text, sha256, fetch date, status per URL — committed; all grading and `--check` read it, no network afterwards | the measured text is the committed text; the gate runs in CI |
| detectors | tradecraft cues on 14 text lenses (taxonomy as of the cue repair, hash recorded); the shipped scanner through node (words floor 100 now in force) | as pass 1 |
| units, rulers, verdicts | as pass 1: docs-fired + Wilson, per-1k + exact Poisson; `background-rates.json` / `occurrence-rates.json` (regenerated after the cue repair); interval comparison only; detectable-multiple for zeros | comparability with pass 1 |
| roll-up | per institution (a URL shared by two institutions — the EIP report, ruled own for both EIP and SIO — is graded on both rows); pooled table across all own-output docs | the board row is the unit |
| hand-read | 40 spans, `random.Random(20260908)`, from lenses with > 3 hits; every hit of lenses with ≤ 3; frozen after the first run; **both readers again** — Reader A (the rig's agent) and a fresh blind Reader B on a different model, same codebook as pass 1 | the pass-1 protocol |
| quotation annotation | as pass 1 (measurement, not filter) | |

## Predictions — scored in the results, wrong ones kept

| # | prediction | falsified if |
|---|---|---|
| Q1 | ≥ 12 institutions end with ≥ 1 graded document; ≥ 30 documents graded as text; ≥ 3 ruled URLs are non-text or fail and are listed as such | fewer on any count |
| Q2 | `legibility` (index-bearing; home genre rulemaking) is **above background** on the pooled own-output docs | indistinguishable or below |
| Q3 | `institutional_permeation` is above background on the Lenin/Comintern/Stalin documents (the lens was seeded from permeation doctrine) | not |
| Q4 | `reference_capture` is above background on Wikipedia's own governance pages, and the hand-read finds the construct in **> 40%** of its read spans there — the cues were coined from this domain | either half |
| Q5 | scanner: ≥ 80% of scored institutional documents land Low; the marxists.org texts are the exception (Moderate or High) | fewer Low, or Lenin/Stalin Low |
| Q6 | hand-read precision on the pooled sample lands **between 25% and 50%** — higher than pass 1's 20–25% because these documents are written in the lenses' home registers | outside the band |
| Q7 | Stanford Internet Observatory's own output (the EIP report, the Virality Project page) fires at least one lens, so its board row stops being a null | nothing fires |
| Q8 | the `existential risk` exclusion from the cue repair suppresses **zero** occurrences here (institutional prose does not use the term) | any suppression, measured as `existential` occurrences vs firings |

## What counts as doing well vs badly

**Well:** the rulers apply; the home-register lenses (`legibility` on rulemaking, `reference_capture`
on Wikipedia) show the construct on read, not just the vocabulary; SIO's row gets a real reading.
**Badly:** above-background lenses whose read spans are again trade vocabulary; a Wikipedia article
about a third party (WikiScanner) driving Wikipedia's row; the scanner "High" on a long institutional
page for reasons a reader would not endorse. Each failure is printed beside its number, flags first.

## Known limits, stated before the run

- Only 16 of 36 institutions have any own output on the ledger; the other 20 stay *no collateral on
  hand* and the board says so. This pass does not go looking for more (that would be a third
  pre-registration with its own selection rule).
- Wikipedia's "own output" includes an encyclopedia article about WikiScanner — Wikipedia's text,
  but about someone else. Ruled own by the host rule; read with that in mind.
- A code of practice is written by a regulator for regulated parties; `legibility` firing on it may
  be the construct or may be the genre. The read decides; the number does not.
- Every number is what the text exhibits, attributed to the text with its URL. Not intent.
