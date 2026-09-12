# Corpus + tradecraft — backlog of desired additional functions

> **CORRECTION 2026-09-03.** Items 14 and 28 below both queue a corpus acquisition on
> the theory that the silent lenses need a different REGISTER. That theory is now
> DISPROVEN and must not be re-queued from here. Measured: congressional hearings
> (74,923 words) produced almost nothing; public rulemaking comments (16,450 words)
> produced nothing; and across all 244 documents held -- 600,458 words -- the silent
> lenses cue phrases are ABSENT rather than blocked (costly_signal 0 of 18 present,
> counterproductivity 0 of 37). Probing concept synonyms instead of authored cues,
> "counterproductive" appears ONCE in 600k words and backfire / unintended-consequence
> / diminishing-return appear zero times each. The missing material is a different
> GENRE of authorship and the blocker is LICENSING, not sourcing. See
> `../eval/RESULTS-2026-09-03-detection-census.md` and
> `../../PLAN-2026-09-02-barometer-realization.md`.

Prioritized. Each item names the deliverable and the discipline it must keep. Nothing here is a verdict
machine; every addition stays symmetric, method-not-ideology, flag-with-receipts.

## A. Corpus breadth (the "sample" half of the loop)
1. **`about/` coverage specimens per pawl** — coverage OF each pawl (of Opus Dei, of the misinformation
   field, of EA/FTX, of WEF, of GFANZ). This is what actually exercises `narrative_management` and
   `sourcing_asymmetry`. Gather via `research-dossier`; fair-use snippet + provenance.
2. **Several `self/` specimens per pawl** (target ≥5) — one specimen per pawl makes the symmetry report
   an anecdote; ≥5 makes it a per-pawl fire-rate with a spread. Breadth before more lenses.
3. **Matched event pairs** — CHOP/CHAZ ↔ Jan 6 (author already holds the receipts: Hunters Capital suit,
   Zilly sanctions, Durkan quotes, the Reddit megathread; Sicknick corrections, Trump v. Anderson). A
   matched left/right event is the sharpest single symmetry test for the coverage lenses.
4. **M5 / archive.org fetches** (IP-blocked from this box, do NOT loop here):
   - WEF Davos Manifesto 2020 (weforum.org 403s origin + curl here).
   - BlackRock Larry Fink CEO letter (canonical URL 404'd/moved — find current + a dated archived copy).
   - Fabian Tract 207 full text (archive.org) to upgrade `tech_webb_gradualness` provenance to primary.

## B. Grading / "train" half of the loop
5. **Model-panel backend calibration** — run `run_corpus.py auto|cloud` and the local backend over the
   corpus; compare model-backend recall against the cues floor; record agreement + the per-pawl spread.
   This is the direct answer to "the cues floor is silent on real prose."
6. **Recall harvest** — feed corpus specimens the cues floor *misses* into `tools/harvest_tells.py` to
   propose new cues, human-reviewed, then re-guard with `tools/fp_audit.py`. Grow recall without FP drift.
7. **Symmetry statistic** — once ≥N specimens/pawl, upgrade the report from mean-index to per-pawl
   fire-rate with bootstrap CIs, and add **matched-method-density sampling** (compare pawls at equal
   method density so a spread reflects the lens, not the sample).

## C. New lenses (Lane B of coverage_asymmetry, and beyond)
8. **`coverage_asymmetry` metadata lens (Lane B)** — the Ground News blindspot method, but over a
   *cluster* not a feed: distribution of outlet coverage on one event, using an open feed (GDELT has an
   API; AllSides/Ad Fontes/MBFC labels enter as **cited disagreement, never imported as truth** — show
   the rater spread, flag not verdict). Pairs with the shipped in-text `sourcing_asymmetry`.
9. **Author's rater priors** — encode PBS/MPR (author's stated most-biased priors) as *documented rater
   disagreement* inputs to Lane B, never as our assertion.

## D. Bias-study integration (wire the corpus into the prompt→pipeline→weight ladder)
Target: `gorrie/bias-study/` (agent `bias-barometer`; `scripts/run_study.py`, `score.py`, the ladder).
The corpus + lenses connect at three points — a novel, concrete experiment set:

10. **Prompt-rung stimulus** — pawl `about/` specimens become study inputs: ask each model to analyze the
    coverage, then grade the model's OUTPUT with our lenses. Signal: does a model reproduce
    `sourcing_asymmetry` / `narrative_management` more when covering right-coded vs left-coded pawls?
    That asymmetry IS an institutional-skepticism-bias measurement, in the study's own frame.
11. **Deterministic auxiliary judge** — add our grader as a NON-LLM judge method in the cross-method
    sweep (`judge_methods.py`). Value: it is not itself an LLM carrying the bias under test; lens index →
    a contamination signal that the 4-LLM-judge median can be checked against.
12. **Weight-rung experiment** — run the corpus prompts through stock vs abliterated open-weight models
    (`run_local.py`), grade both with our lenses, and measure whether refusal-direction ablation changes
    lens-firing **asymmetry across pawls** (does removing the mask make the model treat the pawls more
    evenly?). Requires GPU/OpenRouter — gated behind the barometer's Gate B budget approval.
13. **Adapter** — `corpus/to_bias_study.py`: emit specimens in the study's prompt schema
    (`questions.md` format) so #10/#12 are one command. Spec only until a run is budgeted.

## E. Housekeeping
14. Run `tools/fp_audit.py` on `narrative_management` + `sourcing_asymmetry` (new lenses) as a standing
    gate; wire `run_corpus.py` into the same CI that runs `run_eval.py`.
15. Decide whether the corpus ships public (evilrobots.lol) or stays a dev-only eval asset — snippets are
    fair-use but the *labeling* is analytic; default: dev-only until reviewed.

## F. Resolution — can a lens tell a finding from its own ruler? (2026-09-01)

The eval suite measures whether an index is RIGHT: precision against labels, false-positive
sweeps, mirror-pairs for direction neutrality, cross-faction attestation. Nothing measures
whether an index DIFFERENCE is bigger than what the grader produces by accident. A leaderboard
that grades named people needs an answer when someone asks whether 61 against 54 is a finding
or the width of the ruler.

The sibling bias study spent three days finding exactly this hole in the published
LLM-political-bias literature — ten studies reporting effects, none reporting the resolution of
the instrument producing them, floors the same size as the effects — and then found four of its
own null results sitting below what its instrument could detect. This repo has the same shape
of exposure and should not learn it the same way.

14. **A positive corpus per lens, before any floor number is quoted.** `eval/lens_floor.py`
    exists and currently reports NO FLOOR MEASURABLE for 15 of 15 lenses: the only corpus in
    the repo is news-control text, 19 of 600 lens-document cells fire, and the first run
    returned a clean-looking MDE of 0.5 for every lens that was the stability of zero. The
    harness now refuses to report that. Unblock it with material each lens actually detects —
    this is item 2 (`self/` specimens per pawl) being load-bearing for a second reason.

15. **A DOMAIN-MATCHED negative corpus per lens.** `_news-control` is a shared off-topic
    control, and asking `rollback_asymmetry` not to fire on sports reporting is a trivial test.
    The hard test is regulatory prose that discusses sunset clauses, dependencies and renewal
    WITHOUT exhibiting the asymmetry. A lens that cannot separate those two is detecting
    subject matter rather than method, and that failure is invisible against an off-topic
    control. **This repo has already been burned by a control that varied the wrong factor:**
    the PTC background measured a different construct, was read as a verdict for two days, and
    drove the 34-cue cut that deleted `ongoing`, `movement` and `national security` — the cues
    that fire on rulemaking. Domain-matched negatives are the guard.

16. **Three control types per lens, and they are not substitutes.** Positive (fires, should),
    domain-matched negative (same register and subject, no method), mirrored (same method,
    opposite political direction — `eval/mirror-pairs.json`). Item 15 is the expensive one and
    the only one that catches topic-detection.

17. **Then the floors, then a resolution gate.** Once 14-16 land, `eval/lens_floor.py` yields a
    per-lens MDE, and the leaderboard reports a score gap below a lens's MDE as *not
    resolvable* rather than as a ranking. Wire `--check` into CI so a lens without a measured
    floor cannot ship.

## G. Axis 3 — the ratchet, read off the text (2026-09-01)

18. **`rollback_asymmetry` lens — BUILT, unvalidated.** Five markers, ten detections:
    floor-language, asymmetric repeal burden, sunset erosion, infrastructure lock, one-way
    procedure. Smoke test: 60.6 on a ratchet-positive passage, 0.0 on neutral control, 57.9 on
    the same passage with the political direction flipped. It has no corpus, no floor and no
    mirror-pair entry yet, so the 2.7-point direction gap cannot yet be called noise.

    Why it matters beyond this repo: the three-axis model defines REVERSIBILITY behaviourally
    — *"You don't get to self-report. It's read off what you do."* No questionnaire can place a
    subject on Axis 3, which is why the bias study's forced-choice battery measures opinions
    ABOUT the ratchet rather than the ratchet. This lens reads it off the text, which makes it
    the first direct Axis-3 instrument in the project.

19. **Legislative corpus for it, both arms from one source.** Impact assessments,
    post-implementation reviews, sunset-clause renewal debates, statutory instrument
    explanatory memoranda. Same register and vocabulary throughout, and some genuinely wind
    measures down — so the domain-matched negative of item 15 comes free with the positive
    arm. Public, and the cheapest per-lens corpus in the programme. Start here.

20. **Mirror-pair entries for the new lens**, and a note in `mirror-pairs.json` that a lens
    about irreversibility must fire equally on measures the reader approves of.

## H. Sourcing where the subject is documented only by opponents (2026-09-01)

21. **The contamination this creates, stated so it cannot be forgotten.** For several pawls the
    readily available text is adversarial characterisation rather than primary material. A lens
    tuned on that detects the CHARACTERISATION, not the method — it learns to fire on "text
    about group X" and will then fire on a neutral account of X and stay silent on X's own
    prose. The corpus design already anticipates this with `self/` against `about/` (items 1-2);
    the discipline is that a lens must be checked on BOTH arms and a fire-rate gap between them
    is a defect report, not a finding.

22. **Primary-source priority for the thin pawls.** Manifestos, organisational documents, court
    filings, conference proceedings, forum archives — harder to collect than journalism about
    them, and the only material that makes item 21's check possible. Fair-use snippet with
    provenance, as elsewhere.

23. **Coordination is never asserted.** The lenses detect method-markers and nothing about
    intent or common direction. `RESULTS-2026-08-27-cross-faction.md` measured 7 of 17 methods
    attested under opposed flags, which is what makes the tool credible and unfalsifiable
    claims what would destroy it. Keep flag-with-receipts; never a verdict.

## I. Launch gates — what must be true before this is public

24. **No lens ships without a measured floor** (item 17) or with a `self/`-vs-`about/` fire-rate
    gap it cannot explain (item 21).
25. **Every published grade carries its lens's MDE**, so a reader can see whether the gap
    between two subjects is resolvable.
26. **The leaderboard states what it is not:** a method-marker profile, per lens, never blended
    into one number, never a claim about intent or coordination.
27. **A hostile read of the assembled instrument**, not of individual lenses. The bias study
    shipped four claims that died to exactly this and it has still never had one on the whole.

## J. The ratchet is two instruments, not one (2026-09-01, measured)

Item 19's corpus was built and it broke item 18's lens on contact, which is what a corpus is
for. 30 Federal Register documents, both arms from one publisher, `arm=null` pending human
labels. `rollback_asymmetry` fires on 4 of 30 under the cues backend.

The misses are the finding. **"ALP Express Pilot to Permanent Status" scores 0.0. "Fourth
Temporary Extension of COVID-19 Telemedicine Flexibilities" scores 0.0.** Both are textbook
ratchets by title.

Two causes, and they are different problems:

**Register mismatch.** The lens's cues are written in advocacy voice — "there is no
alternative", "reckless to unwind", "the burden is on those who would repeal". Regulatory prose
does not argue, it administers: "the Department is extending the effective date". The lens was
authored for speeches and op-eds and tested against statute.

**And the deeper one: in administrative prose the ratchet is a COUNT, not a rhetoric.** "Fourth
Temporary Extension" is only a ratchet if you know there were three before it. The document
itself is unremarkable — a routine extension, reasonably argued, one click. No cue-matching over
that single document can recover the pattern, because the pattern is not in it.

That splits the Axis-3 instrument:

28. **`rollback_asymmetry` stays a RHETORICAL lens, and gets the corpus it was built for.**
    Advocacy text: op-eds, speeches, consultation responses, campaign material arguing that a
    measure must not be reversed. The Federal Register set is the wrong corpus for it and
    should not be used to tune its cues — doing so would repeat the PTC mistake of letting a
    corpus measuring a different construct drive a cue change. Keep the 30 documents as a
    NEGATIVE control for it instead: regulatory text is exactly where this lens should stay
    quiet unless the prose turns argumentative.

29. **A new detector for the ADMINISTRATIVE ratchet: `ratchet_series`.** Not a text lens. It
    takes a series of documents concerning one measure and counts one-way movement:
    extensions granted against extensions denied, scope widened against scope narrowed,
    sunsets renewed against sunsets allowed to expire. Output is a per-measure asymmetry ratio
    with the receipts — document numbers and dates — attached.

    This is the same shape as the bias study's lineage-over-versions work, and the same shape
    as its refusal one-way doors: the signal lives in the sequence and is invisible in any
    single member of it. The Federal Register API supplies the series for free, and
    `corpus/fetch_federal_register.py` already talks to it.

30. **The floor for a counting detector is a different object.** Its nuisance factors are not
    sentence order and whitespace; they are docket-matching errors (is this the same measure?),
    coverage gaps (did we see every document in the series?), and classification of ambiguous
    movements. Item 17's harness does not transfer and a second one is needed.

31. **Open and unmeasured: how much of the 26 misses is register versus cue-list gaps.** The
    cues backend is documented as blunter than the LLM read — it only sees literal cues an
    author wrote down. Roughly 30 calls settles it, and until it is run the split above rests
    on reading the titles rather than on a measurement.


## K. The index is partly a length measurement (2026-09-01, measured)

32. ~~**LAUNCH GATE: no lens ships while its score is a function of document length.**~~ **PASSES 2026-09-02** — see below; the duplication null is now exactly satisfied for all 12 firing lenses. Original state:
    `eval/length_dependence.py --check`, tolerance 0.05 index points. **All 12 firing lenses
    currently fail it.** Duplication is a null — the same text twice has the same rate of
    method-marking — and every lens moves, `distributed_accountability` by 7.28 points and
    `institutional_permeation` by 6.74. Length↔index Spearman is **−1.000** for
    `subculture_register`, −0.673 for `institutional_permeation`, −0.498 for
    `reference_capture`. Full measurement in `eval/RESULTS-2026-09-01-length-dependence.md`.

33. **Decide what density means, and it is an author's call.** The cause is the join of two
    individually reasonable decisions: `detect_cues` fires once per detection ("one firing per
    detection is enough"), and the grader divides by token count while calling the result
    "weighted hits per 1k tokens". With one hit per detection the quotient reduces to
    `k / length`. A 102-word Fabian tract gets density 0.8987 and index 22.56; a 28,677-word
    rulemaking with the same single hit gets 0.0029 and 8.60 — roughly 13 of the tract's 22
    points are its brevity. Two repairs, both moving every grade:
    - **count occurrences** so density is a real rate (changes receipt volume too), or
    - **stop dividing by total length** — e.g. share of document segments carrying a marker.

    Now is the cheap moment: the leaderboard is internal and the public `/tech/` render is
    parked, so there are no published grades to protect.

34. **This is a bias in the leaderboard's core claim, not noise.** Institutions are graded
    across document sets whose lengths differ by two orders of magnitude. An institution that
    writes briefly outscores one that writes at length with identical rhetoric — the
    method-not-style rule failing in the arithmetic rather than the taxonomy.

35. **Item 33 DECIDED and DONE (2026-09-02, author's call): count occurrences.** The matcher
    returns every firing; `density` is a rate. **Duplication movement went from up to 7.28
    index points to 0.00 on every lens**, so gate 32 passes. Gold recall unchanged at 138/161,
    156 tests, engine parity green with two new occurrence-counting mechanism fixtures.
    One consequence the decision did not name but required: occurrences must not feed
    `breadth`/`intensity`, or a document repeating one cue would cap its marker score and read
    as broad on one phrase. The grader keeps two sums — every occurrence for the rate, each
    detection once for presence — and `engine.js` mirrors both.
    Residual length correlation is now a real property rather than arithmetic:
    `institutional_permeation`'s hit count is uncorrelated with length (−0.002), so its falling
    rate is a true statement about administrative prose. `subculture_register` flipped from
    −1.000 to +0.959 on eight documents, which is a corpus observation awaiting material.
    Full measurement: `eval/RESULTS-2026-09-02-density-is-a-rate.md`.
