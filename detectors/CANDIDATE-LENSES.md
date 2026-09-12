# Candidate lenses + detection backlog

Queued detector work (Ian, 2026-07-25). Sequencing: **books first**, then a dedicated tradecraft /
detection session. Captured here so nothing is lost. Every candidate must obey the repo's two rules:
**detect the method, not the ideology** (fire symmetrically across factions) and **flag-with-receipts,
never a verdict**. Build each as a versioned YAML in `detectors/`, tuned against `eval/fixtures.json`
(a positive probe + a dual-use / steel-man negative), same as `militant_mobilization`.

## 1. `asymmetric_enforcement` (a.k.a. two-tier justice) — HIGH PRIORITY

**Seed:** the UK "two-tier justice" pattern — the in-power faction permitted latitude the opposing
(nativist) faction is denied, under the SAME statutes. Already seeded in `research-lawfare.md` §3g
(Lucy Connolly's 31-month online-speech sentence; the ~12,183 non-crime/online arrests-per-year datum).
This is the lawfare file's core thesis (same instrument, opposite application) turned into a text lens.

**What it detects (method, symmetric):** the rhetorical + procedural *artifacts* of selective
enforcement — the double-standard structure itself, whoever benefits:
- comparator asymmetry ("X got Y for the same thing Z walked on"),
- charge/sentence disparity language keyed to identity/affiliation rather than conduct,
- discretionary-latitude signals ("context," "no further action," "not in the public interest") applied
  to one side and withheld from the other,
- designation-as-license (feeds the `militant_mobilization` eliminationist marker and the lawfare
  "designation machine").

**Symmetry requirement:** must fire the same on "the establishment shields its own" claims from EITHER
direction. Gold = documented comparator pairs with court/sentence records on BOTH sides (do not build a
one-directional grievance filter — that fails the repo's non-factional rule and would be dismissed).

**Integration into current work:** expand the `research-lawfare.md` §3g UK cluster into a proper
two-tier artifact set (sourced: Connolly + comparators; CPS/Sentencing Council guidance controversies;
Southport-riot vs. other-protest policing comparisons — all ATTRIBUTED, both-sides, per research-dossier
standard). Cross-link to `research-tactical-raids.md` (arrest-theater is the kinetic end of the same
asymmetry).

## 2. UK influence-ratchets — DO NOT reduce to Fabianism (Ian, 2026-07-25)

The UK capture story is **not all Fabian**. `institutional_permeation` is Fabian-SEEDED but is
method-not-ideology and must stay so. When we build the UK material, profile it across MULTIPLE lenses
(institutional_permeation, legibility, distributed_accountability, reference_capture, the new
asymmetric_enforcement) — there are likely several distinct influence ratchets (the online-speech
regime, the NGO/quango complex, the charity-commission/regulator instruments, the sentencing apparatus),
not one Fabian throughline. Hunt and name them separately; never weld them into a single ideological
actor (consistent with the standing Fabian-attribution hard rule).

## 3. "More groups for detection" — entities + capture-leaderboard expansion

Ian: identify more groups for detection in tradecraft (`data/research-entities.json`) and in capture
detection (`leaderboard/`). Do this in the dedicated session, sourced per research-dossier:
- the designation-machine orgs (already partly tracked: SPLC/ADL/Professor Watchlist/Canary Mission —
  lawfare §4) as symmetric pairs,
- insurrectionary/accelerationist networks BOTH directions (the `militant_mobilization` targets:
  Terrorgram/764 already in lawfare §3i; add the symmetric insurrectionary-left networks),
- UK regulators/quangos per item 2,
- each new group needs sourced entity records + a receipt, not a bare name.

## 3b. The FUNDING RATCHET — donor / fiscal-sponsor infrastructure (the money under the deniable arm)

Ian, 2026-07-25: is the funding of direct-action cells (NGO / USAID / pass-throughs) in the ratchet
model? **Coverage audit result: mostly NO.** The FOREIGN apparatus is present (USAID as an entity via
its administrators; NED + "color revolution" in research + The Ratchet ch08/ch10, framed as foreign
influence). The DOMESTIC direct-action funding pipeline is a gap: Open Society/Soros, Tides,
Arabella/Sixteen Thirty, fiscal sponsors, bail funds, mutual-aid networks = ~0 in both the entity graph
and the research (one bail-fund mention: Cop City RICO, lawfare §3h).

**Build spec — the money-layer that connects funders to the militant_mobilization / paramilitarism
deniable arm. This is a MINEFIELD; the discipline is the whole point:**
- **SYMMETRIC or it's worthless.** Map BOTH directions' donor infrastructure from primary records —
  left (Open Society, Tides, Arabella/Sixteen Thirty, bail/mutual-aid funds) AND right (DonorsTrust,
  Bradley, Federalist Society, 85 Fund) — plus the foreign (USAID/NED). A one-sided "Soros" map is the
  captured factional filter the tradecraft repo forbids (method-not-ideology) and fails our own
  left/right-axis-is-captured rule. No exceptions.
- **Primary-sourced FACT only:** IRS Form 990s, FEC/state filings, grant databases, the orgs' own
  reports. Document the MONEY FLOW as fact; attribute every "funds violence / funds the cells"
  characterization to its named source; **NEVER** the "globalist puppet-master" trope — that is the
  antisemitism-adjacent conspiracy register, documented AS such if at all, never adopted.
- **§3i HARD BOUND carries over:** no funder is asserted to have DIRECTED a specific act of violence
  absent recoverable wiring (grant-earmarked-to-the-act, solicitation, tasking). Funding an advocacy
  org whose members later act is documented as funding, not as a directed operation. Connection-strength
  ratings as in §3i (documented-direct / documented-response / attributed-only).
- **Integration:** new sourced entity records + edges in `ratchet-mcp/server/data/` (donor -> fiscal
  sponsor -> recipient), a `research-funding-ratchet.md` dossier, and it becomes an input the
  `network_brokerage` / `revolving_door` graph lenses already read. Cross-link paramilitarism (deniable
  arm needs money) + lawfare §4 designation machine (some funders also fund the designators).

## 3c. International ratchets AS METHODS — the `regulatory_arbitrage` / harm-offloading lens

Ian, 2026-07-25: the international funders/apparatus (USAID, NED, DTRA, pharma) are PAWLS of
international ratchets — "get these in the model because they are METHODS." The durable, non-partisan
way in is a METHOD lens, not a villain list. The method: **harm / liability offloading via regulatory
arbitrage** — relocate a dangerous, exploitative, or accountability-heavy activity to a jurisdiction or
population with weaker oversight, cheaper liability, or less political voice, so it proceeds where it
could not at home. Symmetric, method-not-ideology; fires the same whoever does it.

Instances (each a documented METHOD-CASE, sourced per SAFE METHOD below; the conspiracy overlay is
attributed, never adopted):
- **Offshored biolabs.** FACT: the US DoD Biological Threat Reduction Program (DTRA / Nunn-Lugar)
  funded biological-research labs in Ukraine and other post-Soviet states (US Embassy Kyiv + DTRA, on
  the record). METHOD = site BSL work + Soviet-legacy-pathogen handling in a lower-oversight
  jurisdiction. OVERLAY (attribute, don't adopt): "bioweapon development" is a Russian-MoD/contested
  claim; the US frames them as biosafety/pathogen-security + surveillance. CORRECTION (fact-check):
  DTRA/DoD, NOT Fauci/NIAID — a common conflation; Fauci is a separate pawl (next).
- **Offshored high-hazard research funding (gain-of-function).** DISTINCT pawl: NIH/NIAID (Fauci)
  funding, via the US pass-through EcoHealth Alliance, of coronavirus research at the Wuhan Institute
  of Virology — the grant record is FACT; the "engineered / lab-leak / bioweapon" claims are contested,
  attributed (congressional findings, the split agency assessments), asserted never. METHOD = fund the
  hazard through a pass-through in a lower-oversight lab abroad. (The GoF label itself is disputed —
  report NIH's contest of it too.)
- **Offshored human experimentation.** CASE: Pfizer's 1996 Trovan meningitis trial in Kano, Nigeria
  (Abdullahi v. Pfizer; litigated; settled ~2009-11) is the canonical primary-sourced instance; plus
  the broader documented pattern of trials relocated to low-income populations. METHOD = run the risky
  trial where consent, liability, and oversight are weakest. OVERLAY: "because life is cheap there" is
  an attributed motive-frame, not our voice.

**International-body capture (Ian, 2026-07-25 — flagged as "well documented"; COVERAGE AUDIT says it is
NOT).** WHO / UN Human Rights Council / UNESCO / WEF / IHR-pandemic-treaty = 0 research files and ~0
entity records; only passing book mentions (The Ratchet ch05, ch15). We have the `institutional_permeation`
lens (the method) and the adjacent Gates-Foundation profile, but never applied them here. Build it on the
non-contested documented spine, per SAFE METHOD: Gates Foundation as a top-two WHO funder (WHO's own
contributor data = FACT; "captured WHO" = attributed); UNHRC seating documented rights-abusing member
states (membership record = FACT); the IHR-2024 amendments / pandemic-treaty sovereignty fight (the texts +
national reservations = FACT). This is funding-capture (3b) + institutional_permeation applied to IGOs —
add WHO/UNHRC/UNESCO/WEF as sourced entities with funder edges, then run the permeation + brokerage lenses.

In the model: a `regulatory_arbitrage` (working name) text lens + sourced entity records (DTRA, USAID,
NIAID/EcoHealth, the Pfizer-Kano matter) with edges + receipts feeding the graph lenses. Cross-links:
paramilitarism (§3i), funding ratchet (3b), The Ratchet ch10 "Eagle" / ch08 "Embassy" / ch19-20 (China
as destination), research-nation-state-ratchets.md. Symmetric requirement holds: this is the method of
ANY power exporting its harms (Western pharma/biolabs AND e.g. hazardous-industry/e-waste dumping,
labor arbitrage, others) — not a one-flag map.

## 3d. Feasibility — measuring per-entity capture, and the AI-governance calibration (Ian, 2026-07-25)

Q: use the international bodies (WHO/UNHRC) as the examples to measure/estimate each faction's control
via tradecraft detection — feasible? A: **per-ENTITY yes; per-FACTION no (by design).**

FEASIBLE, from primary data — a body's **capture profile** (never a single blended score):
- **Funding leverage** = each donor's share of the body's budget + the earmarked/flexible ratio
  (earmarked = donor directs the spend = hard leverage). Primary: the body's own contributor data.
- **Brokerage centrality** (`network_brokerage`) = structural chokepoint position, ideology-blind.
- **Revolving-door count** (`revolving_door`) = industry/IGO/gov circulation through the body's committees.
- **Text-vector** (`institutional_permeation`, `inevitability_framing`, ...) on the body's own outputs.
Each metric sourced; the profile is read by a human. This is rigorous and publishable.

NOT FEASIBLE / REFUSED: a single "faction X controls Y by N%." It violates the one ethic (no black-box
control/guilt score) AND "faction" re-imports the ideology the tool strips out (left/right-axis-is-captured
trap). Measure per-entity leverage; never aggregate to a factional verdict.

**The AI calibration (why this whole thread matters — Ian's core thesis):** the same powers that captured
the international bodies will capture AI, and AI capture is the world-domination endgame. Make it
MEASURABLE, not asserted: the international bodies are the **calibration set** (capture playbook —
fund it, staff it via revolving door, permeate the standard-setting — is documented there), validate the
detector against them, then run the SAME method on AI-governance entities (Frontier Model Forum AI Safety
Fund + FLI already in the graph; add the AI Safety Institutes, NIST AI, the EU AI Office, the standards
bodies) and show whether the SAME capture signature is migrating from the health/rights bodies to the AI
bodies. That converts "capture AI = world domination" into a falsifiable, receipt-backed claim — and it is
the spine that ties this whole detector program back to the Evil Robots series. Do it per SAFE METHOD.

## SAFE METHOD — governs all of 3b / 3c (funding + international + any sensitive/named-wrongdoing work)

The line between accountability journalism and a partisan liability is exactly this method. Non-negotiable:
1. **Money/activity flow as FACT, motive NEVER.** Only the record — IRS 990s, FARA, FEC, EU
   Transparency System, DTRA/agency disclosures, court dockets, the orgs' own reports. State the flow,
   cite the filing; never assert why or that it bought an outcome.
2. **§3i hard bound.** Funding/enabling an actor who later acts is funding, NOT a directed operation —
   assert direction only with recoverable wiring (earmark, tasking, solicitation). Carry the
   documented-direct / documented-response / attributed-only rating.
3. **Symmetric or it's a weapon.** Same evidentiary bar, same pass, every faction and every state.
4. **Separate documented FACT from the MYTH (genealogy of distrust).** Where a real state overreach
   seeds a downstream false claim, record the real genealogy [FACT] without endorsing the myth; the
   biolab and GoF cases are the model — the documented program is fact, the "bioweapon" overlay is not.
5. **Attribute the label, adopt none.** "Dark money," "bioweapon," "color revolution," "life is cheap,"
   "CCP influence" — credited to a named source, never our voice.
6. **No conspiracy register.** Puppet-master / "controls everything" tropes (any direction) are out —
   documented as attributed claims if relevant, asserted never.
7. **Nation-state names, not ethnic** (standing hard rule). Government instruments (UFWD, DTRA, NIAID),
   never a people.
8. **Defamation care on living subjects; flag-with-receipts, never a verdict.** Verified resolving
   source or [SOURCE NEEDED]; DEFAMATION NOTE on sensitive clusters; output is the sourced graph the
   reader adjudicates. Local-model failover for a legitimate-but-refused generation step.
9. **The reference register (semi-academic / hands-clean — this IS the liability shield).** State the
   record as fact; attribute every characterization to a named source; assert no motive. Phrasings:
   "per the court filing," "the family alleges," "the official ruling was X; the estate disputes it."
   Documentary voice, receipts-first, at most one earned sardonic line — the facts damn the subject, we
   never do. The moment we assert the conclusion instead of showing the receipt, the hands are no longer
   clean and the work is dismissible.
10. **The aggregation trap (deaths, "suspicious" events, coincidences).** A LIST can smuggle a conclusion
    each entry carefully avoids — ten hedged "died, ruled suicide, family disputes" rows still whisper
    "they're being killed." Test every catalog against DISAGGREGATION: does the claim survive if you
    delete the list and read one case alone? If the pattern only appears in aggregate, the aggregate is
    the assertion — and it is forbidden. **No body-counts.** Document individual cases with their official
    ruling + the attributed questions; never imply a coordinated killer the evidence doesn't show
    (§3i, hard). Honestly handled, this register DEFUSES conspiracy rather than feeding it — which is the
    only credible treatment. See `research-whistleblower-deaths.md` for the worked frame.
11. **FOIA-watchdog source pipelines (symmetric — the primary-document firehose).** Litigation watchdogs
    that FOIA government records are a PRIMARY-DOCUMENT pipeline, not just commentary: **Judicial Watch**
    (right) and, e.g., **American Oversight** (left); the funding-flow trackers (**InfluenceWatch/Capital
    Research** right; **CMD / Accountable.us / Sludge** left) are the money-side counterpart. Rule: use the
    watchdog to LOCATE the underlying FOIA'd document / filing, then CITE that primary record (the released
    memo, the body-cam file, the 990) and ATTRIBUTE the watchdog's framing — never adopt it. Symmetric by
    construction: pull from both partisan watchdog stacks at the same evidentiary bar. (This is already how
    research-tactical-raids.md uses the Judicial Watch body-cam FOIA in the Duncan Lemp case — the document
    is the receipt; JW is how it was found.)

## 3e. Human trafficking as instrumentalized-migration / "5th-generation warfare" (Ian, 2026-07-25)

Ian flags trafficking-as-5GW as particularly despicable and in-scope. It belongs with the EXISTING
instrumentalized-migration record (`research-lawfare.md` §3f: Belarus 2021 "hybrid attack" per the EU;
Russia-Finland 2023-24 per Finland; the EU Reg. 2024/1359 "instrumentalisation" definition) and the
paramilitarism theory (§3i deniable arm). Build per SAFE METHOD, with THREE guardrails that are
non-negotiable here:
- **NEVER welded to demographic-replacement narratives** — standing hard rule (§3f/lens #4). This is the
  single most important guardrail for this thread; the documented instrument is state-orchestrated
  coercive migration/trafficking flows, NOT any claim about intended demographic outcomes.
- **"5th-generation warfare" is an ATTRIBUTED analytical frame**, not established doctrine — document it
  as the frame its proponents use, never assert it as fact.
- **Documented cases only:** the DOCUMENTED state-orchestration cases (Belarus, Russia-Finland) + the
  DOCUMENTED trafficking-prosecution record (DOJ/Europol/UNODC), each primary-sourced; the
  connection-strength rating (documented-direct / documented-response / attributed-only) as in §3i.
  Trafficking VICTIMS are never re-victimized; the focus is the orchestrating instrument, not the trafficked.

## 4. `militant_mobilization` follow-ups (lens shipped 2026-07-25)

- Add model-backend (llm) gold-verification fixtures beyond the cues floor.
- Consider a `verified_cue_receipts` pass to reject dual-use false positives on the soft
  direct-action marker at scale.
- Source contemporary living-subject exemplars ONLY with verified receipts + defamation discipline
  (kept out of the shipped gold on purpose).

## 5. `narrative_management` — record-shaping tradecraft (Ian, 2026-08) — ✅ SHIPPED

**Status:** BUILT — `detectors/narrative_management/taxonomy.yaml` (6 markers, 11 detections, receipted
gold) + eval fixtures (`nm_probe` fires 6/6, idx 90.2; `nm_neg_legit_correction`/`nm_neg_meta` quiet).
Full suite 50/50 positives, 30/30 negatives quiet, 114 pytest green. Notes below record the design.


**Seed:** `book/(internal research source)` (the Disappearance Engine ledger).
Turns that dossier's receipted cases into a text lens. Distinct axis from `distributed_accountability`
(no-one-decides / jurisdiction-over-truth) — compose, never blend.

**What it detects (method, symmetric) — proposed markers, each with a gold example already receipted:**
- `discredit-the-messenger` — attack the reporter's credibility/bias/credentials instead of the claim.
  Cues: "spreading false reports", "so-called journalist", "has ties to", "debunked", "lost all
  credibility", demands to pull credentials. Gold: the Jennings/Kruse pile-on ("spreading false reports
  of extortion" + credential demands) — r/SeattleWA h13gzu; Kruse's WA-House credential denial (SeattleRed);
  Q13 crew assaulted while reporting (U.S. Press Freedom Tracker).
- `euphemism-reframe` — soften/relabel a documented event. Cues: "mostly peaceful", "summer of love",
  "block party atmosphere", "fiery but". Gold: Durkan, "block party atmosphere… could have a summer of
  love" for the armed occupation (Fox13 Seattle, 11 Jun 2020).
- `false-causal-attribution` — pin an outcome on a disfavored actor without evidence, sourced to
  anonymous officials, later quietly corrected. Cues: "according to two law enforcement officials",
  "died from injuries sustained", "beaten with". Gold: NYT Sicknick fire-extinguisher claim (8 Jan 2021)
  vs. the D.C. medical examiner's natural-causes ruling.
- `contested-label-as-settled` — assert a legally/factually disputed characterization as established
  fact, unattributed. Gold: "the deadly insurrection" / "the extortion" stated as bare fact where the
  label is contested (SCOTUS *Trump v. Anderson*; the CHOP extortion dispute).
- `memory-hole` — destroy/alter/withdraw the record: record destruction, stealth correction, unpublish,
  deplatform/designate. Cues: "this article has been updated", "no longer available", "retention
  settings", "designated a terrorist organization". Gold: CHOP deleted texts (Judge Zilly's sanctions);
  the NYT quiet Sicknick correction; the Antifa domestic-terror + State FTO designations.
- `passive-agency-laundering` — passive voice / nominalization to hide the actor. Cues: "officer-involved
  shooting", "shots were fired", "mistakes were made", "was met with force". Gold: illustrative.

**Symmetry requirement (both-sides gold in hand):** Fox/Dominion $787.5M (right-coded — false claims
knowingly aired); Sandmann/CNN-WaPo-NBC + Rolling Stone/UVA (left-coded retracted coverage);
Durkan/Sicknick (left-coded); the Antifa designation (state-vs-left). Do NOT build a one-directional
press-criticism filter — that fails the repo's non-factional rule.

**Connections:** shares the UK/Connolly material with candidate #1 `asymmetric_enforcement` and
`research/research-lawfare.md`; the messenger-targeting SCALE is receipted by the U.S. Press Freedom
Tracker (142 journalist arrests / ~300 assaults in 2020). Build as a versioned `detectors/narrative_management/
taxonomy.yaml` tuned against `eval/fixtures.json` (positive probe + a steel-man negative: legitimate
source-criticism / a genuine correction), same as `militant_mobilization`.

## 6. `coverage_asymmetry` (a.k.a. blindspot / partisan-lean) — a METADATA lane, not a text lens (Ian, 2026-08, "something like Ground News")

**Seed:** Ian's proposal to use something like Ground News. This is NOT a prose lens — it is a
**coverage-distribution** signal, closer to the graph lane's arithmetic than to the LLM text lane.

**What it detects (method, symmetric):** for a given story/event, the ASYMMETRY of *who covers it* —
partisan distribution of outlets running it (blindspot = near-one-sided coverage), which side's outlets
issued a correction/retraction vs. left it standing, and volume/prominence asymmetry. Ideology-blind:
it flags that ONE side is ignoring or over-covering a story, never which side is right.

**Inputs / discipline:** multi-rater source-lean, **never a single vendor's number** — AllSides +
Ad Fontes + MBFC + Ground News — and **show the spread** (per the repo's "show your work / never blend"
rule; a source's lean is itself contested, so display rater disagreement rather than assert one label).

**Open build questions (dedicated session):** data access — Ground News has no open API; AllSides /
Ad Fontes datasets + MBFC are usable; GDELT for coverage-volume/blindspot. Output = a per-story
blindspot/asymmetry score + the rater spread, flagged not verdicted. Pairs with `narrative_management`
and with the shipped in-text Lane A below.

**Lane A SHIPPED as `sourcing_asymmetry`** (2026-08) — `detectors/sourcing_asymmetry/taxonomy.yaml`.
The in-text analog of Ground News's blindspot: reads ONE document for balance (whose voice, whose
evidence) instead of outlets across a feed. Borrows the AllSides text rubric (bias by omission, loaded
language, mind-reading, opinion-as-fact) rather than importing a commercial outlet-lean label. 5 markers
(one_sided_sourcing, refusal_as_closure, loaded_labeling, unsubstantiated_attribution, false_balance) —
two-directional: fires on one-sidedness AND on manufactured false balance. `sa_probe` fires 5/5 (idx 94);
`sa_neg_balanced_report`/`sa_neg_meta` quiet. Lane B (metadata/rater-panel over a cluster, GDELT-first,
commercial raters as cited disagreement not truth) remains TODO.
(#5): the text lens catches the tactic in a document; this catches the one-sidedness across the corpus.
