# Backlog — comprehensive per-camp corpus shibboleth study

**Status:** IN PROGRESS (opened 2026-08-01). Prereq: the FP audit
(`eval/RESULTS-2026-08-01-fp-sweep.md`) established the shibboleth/generic split that motivates this.

**MVP widened 2026-08-01** — see `eval/RESULTS-2026-08-01-camp-coverage-mvp.md`. All 7 camps now carry
mined tells; 4 camps (revolutionary-left ×2, radfem, CSJ, rationalist-partial) have real-primary recall
fixtures; 3 dual-use cues cut on FP grounds despite strong recall (ruling class, existential risk,
singleton). Remaining: real-primary recall for disinfo / managerial / rationalist-post-2002
(accelerationist stays documented-only by defamation policy), then **wire into the ratchet scoring**.

**v1 landed 2026-08-01** — the `subculture_register` lens (`detectors/subculture_register/`): 7 camps
(revolutionary-left, accelerationist-right, radical-feminist, critical-social-justice, disinformation-
apparatus, managerial-technocratic, rationalist/AI-safety), each a marker whose cues are coined
true-believer tells. Validated: every camp exemplar fires ONLY its own camp (clean cross-camp
separation), benign lookalikes stay quiet ("the spectacle of the fireworks" ≠ "society of the
spectacle"), and a REAL fetched primary (Bonanno, *Armed Joy*) correctly fires `revolutionary_left`
on verbatim "class struggle" while de Cleyre's nonviolent *Direct Action* stays silent. The list below
is the DEEPENING work: mine each camp against ≥2 of its own works, add recall fixtures, widen tells.

## The finding that motivates it

The FP sweep sorted every linguistic cue into two piles that behave completely differently on the
deterministic floor:

- **Coined subculture idiom (shibboleths) — precise.** Multi-word terms a discourse community coined
  and effectively owns: `leaderless resistance`, `propaganda of the deed`, `heighten the
  contradictions`, `as above so below`, `solve et coagula`, `malinformation`, `there is no
  alternative`. Near-zero benign use, so they survive the false-positive gate.
- **Repurposed common words — useless.** `based`, `a hero`, `saint`, `consensus`, `standardize`,
  `the light`, `evidence-based`, `observability`. Everyone's vocabulary; they smeared sports pages,
  church bulletins, ops docs, and poetry. All cut.

So the highest-yield way to grow the detector is NOT to invent more abstract "move" cues — it is to
**mine each camp's own canonical works for the coined idiom it owns.** This is exactly the method the
author named ("find the group's publications and find the language and usage patterns") aimed at the
coinages instead of the common words. Ideology-blind is preserved BY DOING IT SYMMETRICALLY: a
detection set for **every** camp, so the tool fingerprints which discourse a text speaks, never
whether that discourse is good or bad. Detections for everyone.

## Method (per camp)

1. **Assemble the canon.** 2-4 primary readers / anthologies / doctrinal texts the camp itself treats
   as foundational (not critics' summaries of them). Local-first, then WebFetch of known archive URLs
   (marxists.org, sacred-texts, movement sites, court exhibits). Every candidate line URL-anchored.
2. **Mine recurring coined idiom.** Pull multi-word terms that recur ACROSS ≥2 of the camp's own works
   and are near-absent from general prose. Prefer the camp's OWN word for a thing over a critic's
   label for it (the actor says `malinformation`; the critic says `censorship` — only the former is a
   shibboleth, the latter is opposite-speaker noise).
3. **Validate each candidate as a cue:**
   - **Recall:** fires on ≥2 of the camp's primary works (add them as `should_fire` fixtures).
   - **Precision:** stays quiet on the benign control corpus AND on the OTHER camps' primary works
     (a shibboleth must identify ITS discourse, not "activist-speak" generally). Add cross-camp
     negatives.
4. **Verdict:** KEEP (recall + clean) / FIX / CUT. Record numbers in a dated RESULTS file.

## Candidate camps + starter shibboleths (unvalidated — the study validates them)

| camp | canonical works to mine | candidate coined idiom (verify each) |
|---|---|---|
| Radical / 2nd-wave feminist | *Sisterhood is Powerful* (Morgan 1970), *Radical Feminism* (Koedt/Levine/Rapone 1973), Dworkin, MacKinnon | the personal is political; compulsory heterosexuality; male gaze; sex class; consciousness-raising; the master's tools |
| Marxist-Leninist / critical theory | Marx, Lenin, Gramsci, Marcuse (marxists.org) | false consciousness; material conditions; seize the means; commodity fetishism; dictatorship of the proletariat; reserve army of labour; praxis; hegemony |
| Critical social justice (institutional) | DiAngelo, Kendi, movement style guides | lived experience; center the voices; problematize; epistemic violence; settler-colonial; cis-heteropatriarchy; carceral; decolonize |
| Accelerationist-right / militant | SIEGE, Turner Diaries, boards (DOCTRINE-only, defamation care) | there is no political solution; read siege; day of the rope; the coming storm |
| Jihadist / Islamist (DOCTRINE-only) | al-Suri, Qutb (published doctrine) | individual jihad; the near enemy / the far enemy; dar al-harb; tawhid |
| Managerial / corporate capture | ESG frameworks, consultancy decks, shareholder letters | align incentives; stakeholder capitalism; north star metric; double materiality; value creation; best-in-class |
| Disinfo / censorship apparatus | EIP/Virality reports, First Draft, CISA | malinformation ✓; cognitive infrastructure ✓; prebunking; coordinated inauthentic behavior; the information environment |
| Occult / esoteric | already `adept_speech` | solve et coagula ✓; egregore ✓; the demiurge; true will; the Great Work (needs case-sensitive) |
| Technocratic / AI-safety | LessWrong, alignment corpus | x-risk; the light cone; coordination problem; epistemics; Overton window |

(✓ = already landed as an easy win in the 2026-08 pass.)

## Second track — named rhetorical STRUCTURES (not vocabulary)

The author's other lead: **motte-and-bailey** and its family (kafkatrapping, DARVO, isolated demand
for rigor, no-true-scotsman-in-defense). These are structural, ideology-blind, and famously easy for
a human to spot in the compilations. They are NOT substring-detectable — a bailey claim sits near a
motte retreat. First target: a `rhetorical_structure` lens whose motte-and-bailey marker runs in the
verify layer (LLM reads the two-part structure), with the shibboleth floor as the candidate prefilter.

## Detector capability gaps this study will hit (fix as needed)

1. **Case-sensitive cue option.** `the Great Work`, `the Storm`, `the Work` are real shibboleths but
   were cut because case-insensitive matching fires them on `the great work of serving customers`.
   A per-cue `case_sensitive: true` flag rescues capitalized coinages.
2. **Verify-layer independent finding.** Verify currently only REFINES cue hits, so any move with no
   findable cue (motte-and-bailey, latent autocomplete-persuasion, legibility's standardization) is
   undetectable end-to-end. Structural markers need verify to find, not just confirm.
3. **Two-part / proximity cues.** Needed for motte-and-bailey (bailey-near-motte) and for co-occurrence
   gating (a single dual-use cue is not a finding).

## OSINT product roadmap (author vision, expanded 2026-08-01)

The register lens is the seed of an OSINT system, not an end in itself. Dependency-ordered:

- **A. Widen + modernize the tells — ALL camps.** SIEGE/Marx/Debord are ANCIENT sources; camps evolve.
  After the historical canon is integrated, pull MODERN materials (X/Telegram/forum corpora via
  `x_ingest.py` and the site analysis cycles) and tune each camp to current 2020s vocabulary. Cut what
  died, add what's live.
- **B. Identify MORE camps (ongoing).** 14 is not the ceiling. Candidates not yet built: tankie/MLM
  (split from anarchist revolutionary-left), tradcath/integralist, Christian-nationalist, eco-radical/
  primitivist, crypto/sovereign-libertarian, woke-capital, degrowth, transhumanist/e-acc. Each earns a
  marker once it has ≥1 validated exclusive tell.
- **C. Identify representative TRUE BELIEVERS per camp.** For each camp, name the accounts/figures whose
  output most purely exemplifies the register — the calibration set. Sourced, public, and used to
  recall-test the tells against living usage (defamation discipline: public figures, public statements,
  flag-not-verdict).
- **D. OSINT tracking + trackable clusters + LIVE AGENTS.** Stand up ongoing collection of those
  exemplars ("see them in their own words") via live agents, cluster by shared tells, and expose the
  clusters as referenceable OSINT — the detector's fingerprints become the cluster keys. Feeds
  troll.fan / evilrobots / thefire enrichment.

  Canon-widening progress (2026-08-01): widened revolutionary-left (wage labour, the proletarians,
  pseudo-need, spectacular society), CSJ (conferred dominance), rationalist (posthumanity) from real
  canon. FINDING: some camps' canon is dominated by DUAL-USE academic vocabulary (Zerzan: domestication
  / division of labor / civilization; Rothbard: statism) — those yield no clean floor cues beyond the
  exclusive coinages already held, same limit as the legibility lens. The FP gate cut 4 canon-derived
  candidates that leaked (career capital, superintelligence, unearned advantage, women's liberation).
- **E. Emergent-group discovery.** Recurring tics from the site analysis cycles that match NO camp are
  candidate NEW camps (loop back to B). The detector broadens the more the properties are worked.
- **F. Effectiveness + other metrics.** Beyond "which register," estimate each group's EFFECTIVENESS —
  a boolean/graded read (growing? influential? winning the frame?) plus other metrics (reach, velocity,
  institutional penetration). Reuses the OSINT spine + the capture/tradecraft grader; cf. lulzindex.
- **G. Compound disposition → threat / volatility / threshold-to-action.** Compose the facets (register
  + moves + costly-signal + militant-mobilization density + effectiveness) into a higher-order read.
  Flag-with-receipts for a human analyst, NEVER an automated verdict on a named person — the §3i
  "no directed-operation claim absent recoverable wiring" bound applies with MORE force here.
- **H. Wire into the ratchet toolset + update ALL scoring.** Once coverage is satisfactory, expose
  `subculture_register` through the ratchet scoring composite so register fingerprints feed the score,
  and re-run scoring everywhere it is consumed (agent/tools.py, web/server.py, profile.py, leaderboard).
  Gated on satisfactory coverage per the author; do NOT rewire scoring on a half-built taxonomy.
- **I. FINAL STEP (post-perfection): ratchet-mcp versioned release.** Once detections are perfected and
  tested against known positives, integrate + improve the ratchet-mcp tooling and CHECK IN the detectors
  and methods as a new versioned release so they can be shared (public mirror github.com/gorrie/ratchet-
  mcp; push GATED, atomic `gh auth switch`; secret scrub). This is the last step, after everything above.

## Tooling — the FP-audit (tools/fp_audit.py)

Scans every cue in the whole detector against a large general-English background; any cue that appears
there is dual-use FP risk. Ran 2026-08-01: `subculture_register` 0/172 (clean); caught the `found`
(525×) and `TINA` (30×) bugs in the move lenses. OPEN: a dedicated move-lens FP-reduction pass driven
by fp_audit — institutional_permeation / reference_capture / militant_mobilization still carry ~44
context-dependent generic cues (judiciary, civility, direct action, …). Those are move-detector cues
(breadth × density + verify, with gold/fixture/leaderboard deps), so the pass is careful per-cue
(narrow / verify-gate / cut only when it breaks no fixture), NOT a blind background-zero sweep.

## Tooling — the keyness harvester (tools/harvest_tells.py)

Data-driven replacement for hand-guessing cues: ranks 2-4-grams by exclusivity (frequent in a camp's
corpus, near-absent from all OTHER camps + a large general-English background). Over-representation IS
the exclusivity screen. Runs on curated PRIMARY/SECONDARY sources only (avoid live-content poison until
detections are solid). It PROPOSES; the eval FP gate DISPOSES — e.g. it surfaced "austrian economics"
(excl=1.00) which then FP-fired on a neutral econ seminar and was cut. Its 2026-08-01 run over the 8
fetched canon corpora found the hand-built taxonomy already largely complete (top candidates were
mostly existing cues, proper nouns, or academic dual-use terms); net clean adds: earn to give.
Corpora + manifest.json stage OUTSIDE git (movement text / some sensitive); only the tool is committed.

## Roadmap detail — why this is worth doing (author vision, 2026-08-01)

The register lens is not an end in itself; it is the shared classifier the rest of the OSINT stack
plugs into. Three payoffs, in dependency order:

1. **OSINT enrichment (now-ish).** Run `subculture_register` + the move lenses over any subject's
   corpus (an X timeline via `x_ingest.py`, a dossier's collected posts, a manifesto) and attach the
   register fingerprint + fired tells as sourced enrichment on troll.fan / evilrobots / thefire
   profiles. The tells ARE receipts — each is a verbatim span with a location. Make the OSINT tools
   work together: one detector, many properties consuming it.
2. **Emergent-group discovery (after the camps are tuned).** The analysis cycles already running for
   thefire (craft), evilrobots (mechanism), and troll.fan (drama) surface recurring tics/methods that
   match NO existing camp. Those unmatched-but-recurrent clusters are candidate NEW camps — the
   discovery loop: mine cycles → cluster novel tells → propose a new marker → validate → fold back in.
   The detector gets broader the more the other properties are used.
3. **Compound disposition / threat synthesis (the hard, fun part — furthest out).** Once the facets are
   reliable (which register + which moves + costly-signal + militant-mobilization density), COMPOSE
   them into a higher-order read of mentality/outlook, and from that a calibrated estimate of THREAT /
   VOLATILITY / THRESHOLD-TO-ACTION. Strict discipline carries over: this is a flag-with-receipts
   profile for a human analyst, NEVER an automated verdict that a named person will act — the §3i
   "no directed-operation claim absent recoverable wiring" bound and the whole flag-not-verdict rule
   apply with MORE force here, not less, because the output looks like a prediction. Dial it in on
   DOCTRINE/aggregate corpora first; gate any named-person application behind the verify layer.

## UPDATE 2026-09-03 — what failed, what it means for this program, and the readiness table

Three measurements landed today. Two are failures and belong here so they are not re-attempted;
the third turns this backlog's "deepen every camp" into a ranked list with numbers.

### Failure 1 — adding coined slogans one at a time does not work, measured held-out

Eight candidate slogans were read from **even**-numbered PTC article ids and evaluated on the
**189 odd-numbered held-out** articles, with a false-positive count over the 115 benign control
documents. Candidates were real (taken from human-annotated `Slogans` gold) and spread across
camps this lens already covers: `smash the state`, `no king but king jesus`,
`rebellion/resistance to tyrants is obedience to god`, `stopthesynod`, `we are hamas`,
`free iran`, `hungary first`.

**2 hits across 189 articles, 1 inside a Slogans span, against 3 control false positives.** FPs
outnumbered TPs. None was worth adding. Full numbers:
`eval/RESULTS-2026-09-03-cue-enumeration-ceiling.md`.

### Failure 2 — the enumeration ceiling, and the correct reading of it

Of this lens's 171 cues, **166 (97%) never appear in 371 PTC articles**; one appears in ≥5
documents. `maganr-tells`'s lift of 5.49 rests on two cues. Against the background rates measured
the same day, resolution needs a firing rate near 0.08–0.12 at n=100 while a cue in 1 of 371
documents fires at 0.003.

**Read that as a statement about PTC, not a verdict on this program.** PTC is 371 *news
articles*; a camp's coined idiom lives in the camp's own canon, and is near-absent from news *by
construction* — that absence is what makes it a shibboleth. So the ceiling does not say the
per-camp study is futile. It says precisely what §"Method (per camp)" step 3 already said: **a
camp's recall must be measured on the camp's own works, and news is only the precision arm.**
What is now disproven is the shortcut of mining slogans out of a news corpus and hoping they
generalise. The canon still has to be assembled, which is the slow part and always was.

Corollary for step 3: PTC is additionally **exhausted as a cue-tuning corpus** — the 2026-08-26
cut was made against a PTC-derived background (`eval/compare_find_stages.py`). Any new cue's
precision arm should use `_news-control` plus cross-camp negatives, and treat PTC lift as
confirmatory at best.

### The readiness table — `eval/camp_readiness.py`, new today

Per camp rather than per lens, because `eval/cue_exclusivity.py` aggregates all 27 camps into a
single number and a camp with 3 cues and no gold reads identically to one with 19.

    python eval/camp_readiness.py --lens subculture_register
    python eval/camp_readiness.py --collisions
    python eval/camp_readiness.py --markdown

State as of 2026-09-03: **14 of 27 camps are ready to validate as they stand.** Every camp has a
gold example and a `should_fire` fixture, and **no cue belongs to two camps** (a collision would
make it a shibboleth for neither — held at zero by a test).

**The nine THIN camps — the cheap wins, and the top of this backlog now.** Each needs canon
assembled and idiom mined, which is desk work with no measurement blocked behind it. Fewer than
five cues means no redundancy to survive an FP audit:

| camp | cues |
|---|---:|
| `sovereign_citizen`, `antinatalist`, `prepper_survivalist` | 3 |
| `jihadist_militant`, `gender_critical`, `tankie_mlm`, `christian_nationalist`, `georgist`, `mmt_monetary` | 4 |

`jihadist_militant` stays DOCTRINE-only, and `accelerationist_right` remains documented-only by
the standing defamation policy.

**Four cues occur in the benign control and want a human look — REVIEW, NOT A CUT.** Frequency in
ordinary prose has been Goodharted in this repo once already: the 2026-08-26 background-frequency
cut removed four "too common" cues and restoring them raised lift 1.12 → 1.77 and annotated
retention from 1-of-4 to 12-of-19. `drain the swamp` (3 control documents, `maga_new_right` — very
likely legitimate political usage), `white privilege` (1, `critical_social_justice`), `uncle ted`
(1, `eco_radical_primitivist`), `social kingship` (1, `tradcath_integralist`).

### Also relevant to this program

The two structural techniques probed today and **disproven for literal cues** —
`Appeal_to_Authority` (attribution sits outside the annotated span) and
`Whataboutism/Straw_Men/Red_Herring` (discourse-relational) — are the same class as this
backlog's **second track** (motte-and-bailey, kafkatrapping, DARVO). That track was already
specified to run in the verify layer rather than as substrings, and today's numbers are
independent confirmation that it must. `detect.py`'s LLM backend has never been measured against
PTC; `compare_find_stages.py` compares cues vs embeddings only, and embeddings measured at chance
on 2026-08-27.

## Third track — NON-ENGLISH cues, and the character-set layer (opened 2026-09-03, author)

Author's requirement: **diaspora analysis needs cues in other languages**, and character sets
are themselves OSINT worth incorporating. Measured the same day so the work can be scoped from
numbers rather than guessed.

### What the cue engine does with non-English cues today, measured

Recall works everywhere; **precision does not.** Every non-Latin cue currently behaves as a
PREFIX match, because `tradecraft/detect.py`'s boundary rule is `_WORDCHAR = [A-Za-z0-9_]`,
ASCII-only.

| script | fires on a real instance | boundary holds |
|---|---|---|
| Latin (ASCII, accented, German compound) | yes | **yes** |
| Cyrillic, Arabic, Hebrew, CJK, Devanagari | yes | **no — matches inside a longer word** |

So `دار الحرب` fires inside `دار الحربية`, and `русский мир` inside `русский мировой`. For
Arabic and Hebrew, whose morphology attaches prefixes and suffixes freely, that is a large
false-positive source rather than an edge case. **A non-English cue can be written today and
should not yet be trusted.**

**The blocker is JS/Python PARITY, not the regex.** `detect.py` already documents this: the
browser engine uses `/[A-Za-z0-9_]/`, which is not Unicode-aware, while Python's `isalpha()` is,
so making only the Python side correct would break `tools/test_engine_parity.py` — and it would
break it *only on non-English text, which is precisely when nobody would be looking.* Both
engines move together or neither does. Modern JS has `\p{L}` with the `u` flag, so the fix is
available; it is a coordinated change plus a parity fixture per script.

CJK is a **separate** problem and should not be folded into the same fix: it has no word
boundaries to respect, so it needs segmentation, and "matching inside a longer word" is a
genuine ambiguity there rather than a bug.

**Work items:**

- **T3.1 — DONE 2026-09-03.** Unicode boundaries in both engines: Python `\w`, JS
  `/[\p{L}\p{N}_]/u`. **Non-Latin cues may now ship.** Details worth keeping, because two
  plausible ways to do this are wrong and only measuring caught either:
  - The two classes were compared **character by character over 47 characters** spanning nine
    scripts, four digit systems, combining marks, ZWJ and punctuation: **0 divergences.** JS
    `\w` is ASCII-only **even with the `u` flag** (29 divergences against Python), and adding
    `\p{M}` diverges on every Arabic harakat and Devanagari vowel sign. Parity is a CI gate, so
    either mistake would have broken the browser engine against Python on exactly the text
    nobody inspects.
  - **The fix introduced its own regression, caught by re-probing rather than by reasoning.** In
    a script written without spaces every occurrence is flanked by letters, so a Unicode
    boundary rule refuses *everything*: the cue 天下为公 stopped matching 他们说天下为公很重要
    at all. From "fires but leaks" to "never fires" is strictly worse and would have shipped as
    an improvement. Each cue edge is now exempted independently when it sits in a
    scriptio-continua range (`_NO_WORD_BOUNDARY` / `NO_WORD_BOUNDARY`, literal codepoint ranges
    on both sides so no Unicode-database drift is possible; Hangul deliberately excluded because
    Korean uses spaces).
  - 14 per-script mechanism fixtures export into the parity payload (mechanism arm 7 → 21
    fixtures, all green). They are **mechanism** rather than lens fixtures because no real lens
    carries a non-Latin cue yet, which would otherwise make the gate circular. Verified to
    BITE: **6 of 6 embedded cases fail under the old ASCII rule**, and the two CJK/kana cases
    fail under a Unicode rule without the exemption — so both failure modes are pinned.
  - No regression: 261 tests, strict eval 53/53 + 34/34, gold 139/162, all 16 background rates
    byte-identical. `tests/test_multilingual_boundaries.py` holds it, including the documented
    limit that a combining mark is not a word character (identical on both sides, so parity
    holds; a cue followed by one still matches, and fixing that needs grapheme clusters).
- **T3.2** — per-camp cue sets in the camp's own language, once T3.1 holds. Same method as
  §"Method (per camp)": canon in the original language, discipline-matched control in the same
  language, and the same KEEP/FIX/CUT verdicts. Note the confound found on `georgist` applies
  doubly here — see the orthography note below.
- **T3.3 — SPEC CORRECTED 2026-09-03, and the original was backwards.** It read: *"transliteration
  variants as sibling cues, which are different cues for the same idiom and should not be
  conflated in one detection."* Following that would have silently inflated every bilingual
  document. Measured on one document containing the same idiom once in each script:

  | declaration | index | intensity |
  |---|---:|---:|
  | one detection, one cue per script | 86.50 | 0.550 |
  | two sibling detections | **100.00** | **1.000** |

  The grader accumulates marker score **per detection** — once per detection at its strongest
  hit — so two siblings add twice for a single idiom. The only argument for splitting was
  receipt clarity, and it does not survive contact: a hit carries the matched span, so which
  script fired is already visible (`'dar al-harb'` vs `'دار الحرب'`).

  **THE RULE: one detection per idiom, one cue per script.** Held by
  `tests/test_transliteration_cues.py`, which also scans the live taxonomies and fails if any
  marker splits its detections across scripts. Note why this was easy to miss: a monolingual
  corpus scores **identically** under either declaration, so nothing looks wrong until the
  first bilingual document arrives. T3.1 landing is what made the trap live.
- **T3.4 — SPLIT 2026-09-11. The boundary half is DONE and now guarded; the segmentation half
  stays deferred, and the reason is measured rather than assumed.**
  - *Boundary half, done:* both runtimes exempt each edge of a cue independently when that edge
    sits in one of ten scriptio-continua ranges (`detect.py::_NO_WORD_BOUNDARY`,
    `engine.js::NO_WORD_BOUNDARY`). Hangul is deliberately absent — Korean uses spaces.
  - *The gap that was open:* those ten ranges are **hand-copied into two files and nothing
    checked they matched.** This is the `EXCLUDE_WINDOW` shape, minus the safety net: that
    duplication is caught by the parity fixtures, and this one **cannot be**, because
    **0 of 803 shipped cues contain a scriptio-continua character** (measured 2026-09-11). No
    fixture exercises any of these ranges, so a wrong range would pass every gate and ship
    silently until the first CJK/Thai/Khmer cue arrived — i.e. until T3.2, which is blocked on
    corpora. Closed by `tests/test_scriptio_continua_parity.py`: table equality, a Hangul-absence
    assertion, a codepoint-by-codepoint behavioural check, and a self-retiring assertion that
    fires once CJK cues do ship. Verified non-vacuous — moving Khmer's upper bound by **one
    codepoint** fails it.
  - *Segmentation half, still deferred:* exempting the boundary makes a CJK cue fire; it does not
    stop it firing on a substring of a longer compound. That guards **zero shipped cues today**,
    so building a segmenter now would be speculative work against nothing. It lands with T3.2,
    when there are cues for it to protect.

### The orthography confound, which generalises well past English

`corpus/mine_camp_idiom.py` now folds British/American spelling on both sides before counting,
because the Wikisource *Wealth of Nations* is an American edition (`labor` 1,324, `labour` 56)
while George is British (`labour` 576). Un-normalised, `produce of labour` measured **zero**
occurrences in the discipline control and passed as a Georgist shibboleth — while
`produce of labor` occurs 8 times in that same text.

**Every language has this, usually worse.** Arabic has ta-marbuta and alef variants plus
optional diacritics; Hebrew has ktiv male vs ktiv haser; Serbian and Kazakh are written in two
scripts entirely; German has ß/ss and pre/post-1996 orthography. **T3.2 must normalise per
language before any count is trusted**, or every cue clears its control for free and the numbers
look excellent.

### The character-set layer — `tools/script_profile.py`, built 2026-09-03

Needs **no vocabulary at all**, so it is unaffected by the enumeration ceiling, works in
languages nobody here reads, and is fully deterministic. Per document it reports:

- **script shares** — a document 88% Latin / 12% Arabic is a different object from either
  monolingual text, and usually diaspora or translation-adjacent prose;
- **mixed-script words** — two scripts inside one word, with the word and its offset as the
  receipt;
- **confusables** — the deliberate subset, where the non-Latin characters are Latin
  look-alikes. `ruѕѕian` with a Cyrillic dze reads as Latin and matches **no** Latin cue: a test
  asserts `"russian" not in text.lower()` while the profiler flags it. This is how keyword
  filters get bypassed, and it is invisible to every other detector here;
- **invisibles** — zero-width joiners/spaces and bidi overrides, which break substring matching
  silently and can make displayed text differ from byte order;
- **diacritic rate** — separates native orthography from stripped transliteration, which matters
  when one community writes both ways.

It is **not a lens**: no index, no rank, no score — a test asserts the output contains no such
field. It profiles a document so an analyst knows which instrument to reach for. Plain English
produces zero findings, also asserted, because a profiler that flags everything gets ignored.

**Work items:** **T3.5 — DONE 2026-09-03.** The analysis moved into the package
(`tradecraft/script_profile.py`; `tools/script_profile.py` is now a thin CLI, because a package
importing from `tools/` is backwards once the profiler is part of the read). `DocumentProfile`
gained an optional `script` field, `grade_text`/`grade_person` populate it, and `SubjectProfile`
carries a subject-level summary counted **in documents, not words** — one document full of
substitutions is a different object from a whole corpus of them, and a word count would flatten
that. `None` means *not measured*, distinct from *nothing found*, same discipline as the floors
contract. Three properties are asserted: the script profile **cannot change any index** (it is
context, not a lens), bilingual prose is **not** reported as mixed-script (the distinction that
keeps it useful rather than alarmist), and plain English yields zero findings. 100% coverage on
the module, including the real alphabetic-but-unnamed character (U+17000 Tangut) rather than a
mock. **T3.6** extend the confusable map as real cases turn up (a gap costs specificity, not
recall — an unmapped look-alike still surfaces under mixed-script).

## UPDATE 2026-09-03 (second entry) — camp 2 done, and the guard list is now seven classes long

**`tankie_mlm` mined and out of THIN: 3 cues from 14 surviving candidates** (Lenin canon 73,130
words against Marx & Engels as the discipline control, 74,628 — size-matched within 2%). Full
numbers: `eval/RESULTS-2026-09-03-lenin-canon-mine.md`. **16 of 27 camps now ready.**

**The ruling standard sharpened, and this is the transferable part.** The question is not "is
this phrase distinctive?" but **"is there a reason beyond my control's silence to believe it?"**
Chronology supplied that reason three times: `finance capital` (coined 1910),
`second international` (founded 1889) and `left communists` (a 1918 faction) cannot appear in
Marx, who died in 1883, however incomplete any Marx corpus is.

Where no such reason existed the candidate was declined — including the most tempting one.
**`dictatorship of the proletariat`: 22 occurrences, 10 files, zero in the control, NOT TAKEN.**
Marx used it in *Critique of the Gotha Programme* (1875), which is absent from the fetched
control. Its zero was **control incompleteness** — the same trap as `margin of cultivation`
clearing a Smith control that predates Ricardo. A cue justified only by silence inherits every
gap in the control.

**Two more confounds, both new, both presenting exactly as findings:**

- **Work titles and author names.** The first pass ranked `infantile disorder`,
  `left-wing communism`, `vladimir ilyich lenin` and `last stage of capitalism` at the top of
  the list. The georgist run's saturation guard could not see them: it drops grams present in
  more than 80% of documents, and a TWO-book canon puts each title in about half the files.
  **A guard tuned on one work fails on two**, in the flattering direction. Fixed at the source
  (`fetch_wikisource.py` strips `ws-noexport` / `wst-header` by depth-counted div matching —
  Wikisource's own marker for "not part of the text") and again in the miner (a stoplist from
  the canon's own document titles, plus `--author`), deliberately overlapping.
- **Scholarly apparatus.** `op cit`, 16 times across 6 files, clean on both controls — the
  statistical profile of a shibboleth, and actually a footnote convention. Now filtered
  alongside navigation.

Still unfiltered and left to the human: proper nouns and quantities from cited sources
(`deutsche bank`, `lloyd george`, `million marks`). They concentrate in 2–4 files against 7–10
for real theory vocabulary, so dispersion is informative but not decisive — `division of the
world` is genuine and sits in 5.

**A gap in the fixture format, found by needing it: `forbid_markers`.** Step 3 requires each
camp be shown quiet on the OTHER camps' primary works, and the format could not express it.
This camp's cross-camp negative is the *Communist Manifesto*, which must not fire `tankie_mlm` —
but written as a lens-level negative it FAILED, correctly, because the passage fires
`revolutionary_left` and Marx **is** that camp's canon. The fixture was wrong, not the detector.
`run_eval.py` now supports `forbid_markers` with its own counter (`cross-camp quiet: n/n`)
folded into the strict gate. **Every remaining camp's cross-camp negative uses this.**

**Seven noise classes are now guarded**, each of which once presented as signal: navigation,
nested templates, saturation, work titles, author names, scholarly apparatus, orthography. Both
runs so far turned up a NEW class the previous run's guards could not see, and both were the
same shape — structural artifacts of the transcription wearing the statistics of idiom. Expect
the third camp to find an eighth.

## UPDATE 2026-09-03 (third entry) — camp 3, and the eighth confound arrived on schedule

**`revolutionary_left`: 2 cues from 9 candidates, with NO new fetching** — Marx & Engels as the
canon against the Adam Smith control, both already in hand from the two earlier runs. Numbers:
`eval/RESULTS-2026-09-03-revleft-canon-mine.md`. Cues added: `productive forces`,
`petty bourgeois`, each zero in 418,000 words of Smith. Gold 141/165 → **143/167**.

### THE EIGHTH CONFOUND: the polemical target's vocabulary

Predicted at the end of the last entry, and it is a genuinely new class:

> **`constituted value` — 21 occurrences, 7 files, zero in BOTH controls.** A textbook shibboleth
> profile. It is **Proudhon's** term, which Marx quotes relentlessly through *The Poverty of
> Philosophy* while demolishing it. Shipping it would have made the Marxist lens fire on
> **Proudhonists**.

No existing guard could see it: a camp's canon quotes its opponents at length, and the opponent
is not in the discipline control either — Proudhon is not Adam Smith. Frequency, dispersion and
both controls all agreed it was idiom.

**The separation needs no external knowledge.** An opponent's term arrives inside quotation marks
and attribution; the camp's own does not. `constituted value` 90%, `labor time` 54%,
`means of production` 14%, `productive forces` 8%, `petty bourgeois` 6%. `quoted_share()` reports
it per candidate and flags ≥50% as *"the polemical target's term?"* — **reported, not filtered**,
because a camp does sometimes adopt a term it first quoted, which is exactly why `labor time`
sits at 54%.

### The cost curve, three runs in

| camp | new fetching | candidates | cues | new confound |
|---|---|---:|---:|---|
| `georgist` | 3 works | 22 | 1 | discipline control; orthography; saturation; nested templates |
| `tankie_mlm` | 6 works | 14 | 3 | work titles + author names; scholarly apparatus |
| `revolutionary_left` | **none** | 9 | 2 | the polemical target's vocabulary |

Candidate lists shorten as guards accumulate (22 → 14 → 9) while yield holds. **Eight noise
classes guarded, every one of which first presented as a finding.** A small validation of the
method: this run independently re-surfaced `means of production`, already a hand-picked cue in
this camp — a procedure that only ever yields novel phrases might be finding noise; one that
rediscovers a known cue on its own evidence is measuring something.

**Treat a ninth class as live for camp 4.** The shape has been identical all three times: an
artifact of how the text was transcribed, published or argued, wearing the statistics of idiom —
and nothing in frequency, dispersion or control-silence distinguishes any of them, which is why
they had to be found one corpus at a time rather than reasoned out in advance.

## The seven remaining thin camps, and why they are not the same job as the first three

Recorded 2026-09-03 after three camps, so nobody schedules the next seven as if they were the
last three. **The public-domain seam is exhausted.** `georgist`, `tankie_mlm` and
`revolutionary_left` were tractable because canon AND control were both out of copyright and on
Wikisource. Every camp left is modern:

| camp | cues | canon, and what it would take |
|---|---:|---|
| `sovereign_citizen` | 3 | court filings — public record, but not on Wikisource; needs a docket fetcher |
| `antinatalist` | 3 | Benatar (2006) copyrighted; open-web efilism/antinatalist writing is fetcher-manifest material |
| `prepper_survivalist` | 3 | forums and sites — freely accessible, **the one reachable by fetcher-manifest today** |
| `jihadist_militant` | 4 | DOCTRINE-only. Needs an **Arabic-language** control: `دار الحرب` is mainstream classical juristic vocabulary, so an in-language fiqh corpus is the discipline control, and T3.1/T3.2 are prerequisites |
| `gender_critical` | 4 | contemporary web and books |
| `christian_nationalist` | 4 | Seven Mountain / dominionism, 1970s onward, copyrighted. Public-domain theology is NOT this camp's canon |
| `mmt_monetary` | 4 | Mitchell / Wray / Kelton, copyrighted — though its discipline control (classical economics, Smith) is already in hand |

Two consequences worth acting on rather than rediscovering:

- **Build controls by DISCIPLINE, not per camp.** One classical-economics control serves
  `georgist` and `mmt_monetary`; one mainstream-theology control serves `christian_nationalist`
  and `tradcath_integralist`; one security-studies control serves `jihadist_militant` and
  `militant_mobilization`. Seven camps do not need seven controls.
- **The bottleneck is the human ruling, not the fetching.** At roughly 22 → 14 → 9 candidates
  per camp and one to three cues out, the expensive step is a person deciding which surviving
  phrase is a term of art rather than an author's tic — and, since the `tankie_mlm` run, deciding
  whether there is a reason beyond the control's silence to believe it. No tooling shortens that.

## Definition of done

Every camp above has a validated shibboleth set (recall on ≥2 own-canon works; quiet on benign AND
cross-camp), a dated RESULTS file with the numbers, and the ideology-blind symmetry check passing
(the same machinery flags every camp). The motte-and-bailey structural marker ships behind the verify
layer. No camp is privileged or omitted.
