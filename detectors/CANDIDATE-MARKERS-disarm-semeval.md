# CANDIDATE MARKERS — SemEval persuasion taxonomy + DISARM influence-ops TTPs

**Status: CANDIDATE catalog. NOT WIRED.** This is a sourced *menu* for future taxonomy PRs — a
mapping of two established, externally-published frameworks onto the detector's marker schema. No
YAML in `detectors/` has been changed; nothing here is loaded by the grader. Each entry is written
so it can later be lifted into a `markers:` block (see `detectors/institutional_permeation/taxonomy.yaml`
for the prose-lens shape and `detectors/revolving_door/taxonomy.yaml` for the behavioral-lens shape).

## The one principle, restated for imported markers

**Method, not ideology.** Every candidate below keys on *how* a text or behavior operates — the
rhetorical move, the account topology, the laundering path — and never on whose side it serves. A
SemEval "loaded language" marker fires identically on a left tract and a right one; a DISARM
"create inauthentic accounts" marker fires identically whether the network pushes a friendly or a
hostile narrative. That ideology-blindness is the precondition for importing either framework.

**Flag-and-show-receipts, never a verdict** (load-bearing for DISARM especially). The DISARM
techniques are *coordinated-inauthentic-behavior* (CIB) categories. They must be imported as
**behavioral markers whose receipt is the observed edge/artifact** (the account list, the timestamp
cluster, the shared registration, the cross-post fingerprint) — **never** as an asserted
"coordination" or "cabal" verdict. The detector surfaces *this account was created in a burst with
these others and posted the same string within N minutes*; a human adjudicates whether that is a
campaign. Asserting "this is a coordinated operation" from the marker alone is exactly the
captured-neutral oracle the books warn against. Same rule the `revolving_door` lens already lives by:
a topology is a fact, not a finding about a person.

## Two destinations

1. **A NEW `persuasion_technique` language lens** — the natural home for the SemEval taxonomy. It
   would be a sibling of `adept_speech` (register detection) and `institutional_permeation` (move
   detection), scored by the same prose grader (breadth × intensity × density). **The SemEval shared
   tasks ship a labeled corpus** — the PTC-SemEval20 corpus (8,981 annotated spans across 536
   articles) and the SemEval-2023 multilingual set. That is the **validation-set opportunity**: the
   language lenses today have only the 7-fixture `eval/fixtures.json` smoke set; the SemEval corpus
   is a real labeled gold standard to tune `marker_present_threshold` and per-detection weights
   against, and to measure precision/recall instead of eyeballing fixtures.

2. **A NEW behavioral `influence_operation` (CIB) lens** — the natural home for DISARM. It would be
   a sibling of `revolving_door` (the other behavioral/graph lens): `w_density: 0.0`, signal is
   breadth × intensity over observed structural artifacts, receipt = the artifact. DISARM has **no
   public labeled text corpus** the way SemEval does — it is a TTP catalog (like MITRE ATT&CK), so
   this lens is validated by curated incident write-ups, not a shared-task gold set. Flag that gap.

A handful of SemEval techniques also **sharpen existing `institutional_permeation` detections**
(`captured_neutral`, `manufactured_consent`) rather than needing the new lens — noted per-entry.

---

# Part 1 — SemEval propaganda / persuasion technique taxonomy

**Primary sources:**
- Da San Martino, Yu, Barrón-Cedeño, Petrov, Nakov, *Fine-Grained Analysis of Propaganda in News
  Articles*, EMNLP-IJCNLP 2019 — https://aclanthology.org/D19-1565/ (the original **18**-technique
  schema). Definitions page: https://propaganda.math.unipd.it/annotations/definitions.html
- Da San Martino, Barrón-Cedeño, Wachsmuth, Petrov, Nakov, *SemEval-2020 Task 11: Detection of
  Propaganda Techniques in News Articles* — https://aclanthology.org/2020.semeval-1.186/ /
  https://arxiv.org/abs/2009.02696 (the **14**-technique consolidation + PTC-SemEval20 corpus).
- Piskorski, Stefanovitch, Da San Martino, Nakov, *SemEval-2023 Task 3: Detecting the Category, the
  Framing, and the Persuasion Techniques in Online News in a Multi-lingual Setup* —
  https://aclanthology.org/2023.semeval-1.317/ (the **23**-technique, six-coarse-category multilingual
  expansion).

**Lineage note (verbatim from the 2020 paper, arXiv:2009.02696 §2):** the annotation team started
with **18** techniques; for SemEval-2020 they "merged similar techniques with very low frequency."
*Red Herring* and *Straw Man* were merged into *Whataboutism* (technique 13); *Bandwagon* into
*Reductio ad Hitlerum* (technique 14); and *Obfuscation, Intentional Vagueness, Confusion* was
dropped — yielding **14**. SemEval-2023 re-split most of these and added new ones for a **23**-technique
taxonomy under **six coarse categories**. The catalog below lists the **full 18** original techniques
(so the merges and the dropped one are not lost), tags each with its 2023 coarse category, and notes
which lens it feeds.

**Default destination:** new `persuasion_technique` language lens unless flagged otherwise.
Definitions are quoted/paraphrased from the 2020 paper's numbered list (§2) and Table 1 examples.

### Coarse category: Manipulative Wording (2023)

**1. Loaded language** *(2020 #1; 2023 Manipulative Wording)*
- Def: using specific words and phrases with strong emotional implications (positive or negative) to
  influence an audience.
- Cues: emotionally weighted adjectives/nouns where a neutral term exists — "outrage," "disaster,"
  "thug," "hero," "catastrophic," "shameful," scare-quotes around an ordinary word.
- Example (paper Table 1): *"**Outrage** as Donald Trump suggests injecting disinfectant to kill virus."*
- Feeds: `persuasion_technique`. (Most frequent technique in the corpus — high-value, high-precision target.)

**2. Repetition** *(2020 #3; 2023 Manipulative Wording)*
- Def: repeating the same message/word over and over so the audience eventually accepts it.
- Cues: same keyword or slogan recurring at abnormal density within a span; anaphora.
- Example: *"I still have a **dream**. It is a **dream** deeply rooted… I have a **dream** that one day…"*
- Feeds: `persuasion_technique`. (Note: density is the native signal here — pairs well with the grader's `density` term.)

**3. Exaggeration / minimisation** *(2020 #4; 2023 Manipulative Wording)*
- Def: representing something in an excessive manner (bigger/better/worse) or making it seem less
  important/smaller than it is.
- Cues: superlatives without basis ("the greatest in history," "never before seen"); dismissives
  ("merely," "just a," "a tiny fraction," "nothing to worry about").
- Example: *"Coronavirus '**risk to the American people remains very low**', Trump said."*
- Feeds: `persuasion_technique`.

**4. Obfuscation / intentional vagueness / confusion** *(2020-dropped; restored 2023 Manipulative Wording)*
- Def: using deliberately unclear words/phrases so the audience may develop its own interpretation,
  or to evade a clear claim.
- Cues: agentless passives, "some say," "things were done," "mistakes were made," undefined "they."
- Feeds: `persuasion_technique`. **Also sharpens** `institutional_permeation` →
  `deniability_architecture` / `attribution-gap` (the "no record of who decided" move).

### Coarse category: Attack on Reputation (2023)

**5. Name-calling / labeling** *(2020 #2; 2023 Attack on Reputation)*
- Def: labeling the object of the campaign as something the target audience fears, hates, finds
  undesirable, or loves/praises.
- Cues: epithet substituted for a name — "Public Enemy Number 1," "radical," "elites," "regime,"
  "patriots," applied as a fixed tag.
- Example: *"WHO: Coronavirus emergency is '**Public Enemy Number 1**'."*
- Feeds: `persuasion_technique`.

**6. Doubt / casting doubt** *(2020 #5; 2023 Attack on Reputation)*
- Def: questioning the credibility of someone or something.
- Cues: "Can we really trust…", "What is X hiding?", "Funny how X always…", rhetorical
  credibility-undermining questions.
- Example: *"Can the same be said for the Obama Administration?"*
- Feeds: `persuasion_technique`. **Also sharpens** `institutional_permeation` → `captured_neutral`
  when used to undermine a rival's claim of neutrality.

**7. Appeal to hypocrisy (tu quoque)** *(new in 2023 Attack on Reputation; subset of 2020 whataboutism)*
- Def: attacking the opponent's character/consistency by charging them with hypocrisy, without
  disproving their argument.
- Cues: "and yet you…", "the same people who…", "where was your outrage when…".
- Feeds: `persuasion_technique`. (Overlaps Whataboutism #16; keep distinct per 2023 schema.)

**8. Guilt by association / reductio ad Hitlerum** *(2020 #14 sub; 2023 Attack on Reputation)*
- Def: persuading the audience to disapprove of an action/idea by suggesting it is popular with
  groups hated/in contempt by the audience.
- Cues: "this is exactly what [reviled group] wanted," "Nazi/Stalinist/terrorist-adjacent" guilt
  linkage, "fellow travelers of."
- Example: *"'Vichy journalism'… **collaborates in the same way that the Vichy government in France collaborated with the Nazis.**"*
- Feeds: `persuasion_technique`.

### Coarse category: Justification (2023)

**9. Appeal to authority** *(2020 #10; 2023 Justification)*
- Def: stating a claim is true simply because a (valid or invalid) authority/expert supports it,
  without other evidence; includes *testimonial* where the source is not actually an authority.
- Cues: "experts agree," "studies show" (uncited), name-drop of an authority as the whole argument.
- Example: *"Monsignor… confirmed that '**Vigan said the truth. That's all.**'"*
- Feeds: `persuasion_technique`. **Strongly sharpens** `institutional_permeation` → `captured_neutral`
  / `value-as-science` (the "the science is settled / experts agree" move) — this is the cleanest
  cross-lens overlap in the catalog.

**10. Appeal to fear / prejudice** *(2020 #6; 2023 Justification)*
- Def: seeking support for an idea by instilling anxiety/panic toward an alternative, possibly on
  preconceived judgments.
- Cues: "if we don't act now, X catastrophe," "they're coming for your…," threat-then-remedy structure.
- Example: *"A dark, impenetrable and '**irreversible**' winter of persecution of the faithful… will fall."*
- Feeds: `persuasion_technique`. **Also sharpens** `institutional_permeation` → `crisis_no_exit` /
  `define-crisis-claim-authority`.

**11. Flag-waving** *(2020 #7; 2023 Justification)*
- Def: playing on strong group feeling (nation, race, gender, political identity) to justify or
  promote an action/idea.
- Cues: "real Americans," "for the will of the people," "our nation demands," identity-as-warrant.
- Example: *"Mueller attempts **to stop the will of We the People**!!! It's time to jail Mueller."*
- Feeds: `persuasion_technique`.

**12. Appeal to popularity / bandwagon** *(2020 #14 sub; 2023 Justification)*
- Def: persuading the audience to join/take an action because "everyone else is doing the same."
- Cues: "millions agree," "the whole world sees," "join the movement," "nobody believes X anymore."
- Example: *"He tweeted, '**EU no longer considers #Hamas a terrorist group. Time for US to do same.**'"*
- Feeds: `persuasion_technique`. **Also sharpens** `institutional_permeation` → `manufactured_consent`
  (consensus manufactured by assertion).

**13. Appeal to values** *(new in 2023 Justification)*
- Def: justifying an idea by linking it to widely shared positive values (freedom, family, justice,
  tradition) as the warrant, in place of evidence.
- Cues: "this is about freedom itself," "any decent person believes," value-name as the argument.
- Feeds: `persuasion_technique`.

### Coarse category: Simplification (2023)

**14. Causal oversimplification** *(2020 #8; 2023 Simplification)*
- Def: assuming one cause/reason when there are multiple; includes *scapegoating* (transfer of blame
  to one person/group without investigating complexity).
- Cues: "the real reason is simply…," single-villain framing, "all of this because of X."
- Example: *"**If France had not have declared war on Germany then World War II would never have happened.**"*
- Feeds: `persuasion_technique`.

**15. Black-and-white fallacy / false dilemma / dictatorship** *(2020 #11; 2023 Simplification as "False Dilemma or No Choice")*
- Def: presenting two options as the only possibilities when more exist; *dictatorship* = telling the
  audience exactly what to do, eliminating any other choice.
- Cues: "either we X or we lose everything," "there is no alternative," "you're with us or against us."
- Example: *"'**Everyone is guilty for the good he could have done and did not do…If we do not oppose evil, we tacitly feed it.**'"*
- Feeds: `persuasion_technique`.

**(2023 adds *Consequential Oversimplification* — slippery-slope: "if we allow X, then inevitably Y,
Z, catastrophe." Cues: domino chains, "the first step toward." Feeds `persuasion_technique`; also
brushes `institutional_permeation` → `crisis_no_exit`.)**

### Coarse category: Call (2023)

**16. Slogans** *(2020 #9; 2023 Call)*
- Def: a brief, striking phrase that may include labeling/stereotyping; acts as an emotional appeal.
- Cues: short capitalized/quoted rallying phrase, often imperative — "BUILD THE WALL!", three-word
  chants.
- Example: *"'**BUILD THE WALL!**' Trump tweeted."*
- Feeds: `persuasion_technique`.

**17. Thought-terminating cliché / conversation killer** *(2020 #12; 2023 Call as "Conversation Killer")*
- Def: short, generic phrases that discourage critical thought and end discussion with a
  seemingly-simple answer or by distracting from other lines of thought.
- Cues: "it is what it is," "we'll have to agree to disagree," "that's just common sense," "end of story,"
  "do your own research."
- Example: *"I do not really see any problems there. Marx is the President."*
- Feeds: `persuasion_technique`. **Notably overlaps** `adept_speech` (initiatory thought-stoppers) — a
  co-occurrence worth tracking across the two lenses, not double-counting within one.

**(2023 adds *Appeal to Time* — "it is high time," "the moment is now," urgency-as-argument. Cues:
"now or never," "the time has come." Feeds `persuasion_technique`; brushes `crisis_no_exit`.)**

### Coarse category: Distraction (2023)

**18. Whataboutism** *(2020 #13; 2023 Distraction)*
- Def: discrediting an opponent's position by charging them with hypocrisy without directly
  disproving their argument; deflecting to a different issue.
- Cues: "but what about…," "and yet nobody mentions when X did…".
- Example: *"President Trump —**who himself avoided national military service** in the 1960's— keeps beating the war drums…"*
- Feeds: `persuasion_technique`.

**19. Straw man** *(2020 original 18; merged into #13 in 2020; 2023 Distraction)*
- Def: substituting an opponent's proposition with a similar, weaker one and refuting that instead —
  "caricaturing an opposing view so it is easy to refute."
- Cues: "so what you're really saying is…," "they want to [extreme distortion]."
- Feeds: `persuasion_technique`.

**20. Red herring** *(2020 original 18; merged into #13 in 2020; 2023 Distraction)*
- Def: introducing irrelevant material to divert attention from the points being made.
- Cues: abrupt topic pivot under challenge; emotionally loaded but off-point digression.
- Feeds: `persuasion_technique`.

### Also present in 2023, not in original 18

- **Questioning the Reputation** (Attack on Reputation) — making damaging unsupported claims/innuendo
  about a target's character/standing. Cues: "rumor has it," "people are saying," innuendo. Feeds
  `persuasion_technique`; brushes `institutional_permeation` → `front_costume` when used to discredit
  a genuine grassroots opponent.

**SemEval count cataloged: 18 original techniques (Loaded Language, Name-calling, Repetition,
Exaggeration/Minimisation, Doubt, Appeal to fear/prejudice, Flag-waving, Causal Oversimplification,
Slogans, Appeal to Authority, Black-and-white Fallacy, Thought-terminating Cliché, Whataboutism,
Reductio ad Hitlerum/Guilt-by-association, Straw Man, Red Herring, Bandwagon/Appeal-to-popularity,
Obfuscation), plus the 2023 additions noted inline (Appeal to Hypocrisy, Appeal to Values,
Consequential Oversimplification, Appeal to Time, Questioning the Reputation) — bringing the 2023
total to 23.**

---

# Part 2 — DISARM influence-operation TTP framework

**Primary source:** DISARM Foundation, *DISARM Framework* — https://www.disarm.foundation/ ;
machine-readable master data and per-technique pages:
https://github.com/DISARMFoundation/DISARMframeworks (technique IDs verbatim below are from the
generated techniques index). DISARM is the merged successor to AMITT/SP!CE and is modeled on MITRE
ATT&CK: a **tactic → technique → sub-technique** hierarchy. **DISARM Red** describes *incident-creator*
behaviors (the attacker TTPs); DISARM Blue describes countermeasures. We import only Red.

**Structure:** Red is organized into tactic phases (Plan, Prepare, Execute, Assess), e.g. *TA15
Establish Social Assets / Establish Legitimacy*, *TA16 Establish Personas*, *TA17 Maximize Exposure*,
*TA18 Drive Online Harms*. Each tactic holds techniques (Txxxx) with sub-techniques (Txxxx.yyy).

**Destination:** a NEW behavioral `influence_operation` (CIB) lens — sibling of `revolving_door`.
Config would mirror `revolving_door` (`w_density: 0.0`; signal = breadth × intensity over observed
artifacts). **Each marker's "gold"/receipt is the observed artifact** (account-creation burst,
shared registrant/IP, identical-string cross-posts, follow-train graph) — imported as a behavioral
fact, **never** an asserted coordination verdict (the hard rule above).

**Validation-corpus gap (flag):** unlike SemEval, DISARM ships **no public labeled text corpus**.
It is a TTP taxonomy validated by analyst-tagged incident reports (e.g. EU DisinfoLab, EDMO,
Graphika write-ups). This lens would be validated against curated incident dossiers, not a
shared-task gold set — a real difference from the language lenses and a known weakness to state up front.

### Candidate behavioral markers (most relevant to a CIB lens)

**1. Develop fabricated personas** — DISARM **T0097 Present Persona** (+ subs T0097.100 Individual,
.102 Journalist, .104 Hacktivist, .107 Researcher, .108 Expert, .200 Institutional personas).
- Def: adopting a fabricated/backstopped individual or institutional identity to lend credibility.
- Receipt: persona with no pre-incident footprint, stock/GAN profile photo, backstopped bio that
  doesn't resolve. **Show the artifact, not "this is a fake person."**
- Feeds: `influence_operation`.

**2. Create inauthentic news sites / outlets** — DISARM **T0098 Establish Inauthentic News Sites**
(T0098.001 Create, T0098.002 Leverage Existing); related T0097.202 News Outlet Persona,
T0097.203 Fact-Checking Org Persona.
- Def: standing up imposter/fabricated news organizations to launder content into a credible-looking
  wrapper.
- Receipt: domain registration date vs. claimed history; shared registrant/template with other sites.
- Feeds: `influence_operation`. **Also sharpens** `institutional_permeation` → `front_costume`
  (funded operation in independent-outlet costume) and `captured_neutral` (fact-checker persona).

**3. Create inauthentic accounts / sockpuppets / bots** — DISARM **T0091.003 Enlist Troll Accounts**,
**T0093.002 Acquire Botnets**, **T0049.001 Trolls Amplify and Manipulate**,
**T0049.003 Bots Amplify via Automated Forwarding and Reposting**.
- Def: operating fake human-run accounts (sockpuppets), troll accounts, or automated bot accounts.
- Receipt: creation-time burst, lockstep posting cadence, shared device/IP fingerprints, near-identical bios.
- Feeds: `influence_operation`. **The canonical CIB marker — and the canonical place the verdict rule
  bites: surface the burst + cadence, never assert "this is a bot army."**

**4. Build network / follow-trains / sub-communities** — DISARM **T0092 Build Network**
(T0092.001 Create Organisations, T0092.002 Use Follow Trains, T0092.003 Create Community/Sub-Group).
- Def: constructing interconnected accounts and amplification structures to manufacture apparent reach.
- Receipt: dense reciprocal-follow subgraph created in a window; coordinated community founding.
- Feeds: `influence_operation`. (Graph-native — directly analogous to `revolving_door`'s edge reading.)

**5. Leverage / create content farms** — DISARM **T0096 Leverage Content Farms**
(T0096.001 Create Content Farms, T0096.002 Outsource Content Creation to External Organisations).
- Def: using large-scale content-production services/orgs to mass-produce aligned material.
- Receipt: volume + templating fingerprint; shared bylines across "independent" outlets.
- Feeds: `influence_operation`. **Also sharpens** `institutional_permeation` → `build-parallel-institutions`.

**6. Launder narratives through intermediaries (co-opt trusted sources)** — DISARM
**T0100 Co-Opt Trusted Sources** (T0100.001 Co-Opt Trusted Individuals, T0100.002 Co-Opt Grassroots
Groups, T0100.003 Co-Opt Influencers); related **T0039 Bait Influencer**.
- Def: routing a narrative through credible third parties (influencers, NGOs, grassroots groups) so
  the originator stays off the record.
- Receipt: traceable origin → intermediary → mainstream hop chain; undisclosed funding/coordination link.
- Feeds: `influence_operation`. **Strongly sharpens** `institutional_permeation` →
  `deniability_architecture` / `intermediary-laundering` (the "route preferences through academic
  intermediaries so no one ordered it" move) — the tightest cross-lens overlap on the behavioral side.

**7. Astroturf / co-opt grassroots costume** — DISARM **T0100.002 Co-Opt Grassroots Groups**;
**T0092.003 Create Community or Sub-Group**; persona **T0097.208 Social Cause Persona**.
- Def: a funded/coordinated operation presenting as an independent, spontaneous grassroots movement.
- Receipt: funding/coordination link behind a "concerned citizens" front; synchronized launch.
- Feeds: `influence_operation`. **Direct twin** of `institutional_permeation` → `front_costume` /
  `astroturf` (already in that lens for the *prose* tell; this is the *behavioral* tell — keep both,
  let co-occurrence across lenses be the signal).

**8. Flood the information space** — DISARM **T0049 Flood Information Space** (T0049.002 Flood Existing
Hashtag, T0049.005 Conduct Swarming, T0049.008 Generate Information Pollution).
- Def: overwhelming a platform/hashtag/audience with high-volume inauthentic content to drown
  signal or manufacture salience.
- Receipt: volume spike + low-account-diversity ratio; hashtag-capture timeline.
- Feeds: `influence_operation`.

**9. Amplify existing narrative / cross-post** — DISARM **T0118 Amplify Existing Narrative**;
**T0119 Cross-Posting** (T0119.001 across Groups, T0119.002 across Platform).
- Def: boosting an aligned narrative and replicating identical messaging across groups/platforms to
  simulate organic spread.
- Receipt: identical-string cross-post fingerprint with synchronized timing across distinct platforms.
- Feeds: `influence_operation`.

**10. Manipulate platform algorithm / keyword squatting** — DISARM **T0121 Manipulate Platform
Algorithm**; **T0049.006 Conduct Keyword Squatting**.
- Def: gaming ranking/search/recommender systems to inflate visibility beyond organic reach.
- Receipt: engagement-pattern anomaly relative to follower graph; search-term capture.
- Feeds: `influence_operation`. **Brushes** `cognitive_capture` (recommender-steering) — note the
  axis boundary: DISARM = the attacker *gaming* the algorithm; `cognitive_capture` = the algorithm
  *itself* steering. Keep them on separate axes (the project's no-blended-number rule).

**11. Suppress / report-brigade opposition** — DISARM **T0124 Suppress Opposition**
(T0124.001 Report Non-Violative Opposing Content, T0124.003 Exploit Platform TOS/Content Moderation);
**T0048 Harass** (T0048.004 Dox).
- Def: weaponizing platform moderation (mass false-reporting) or harassment/doxing to silence opponents.
- Receipt: coordinated report-spike against one target; brigading-account overlap.
- Feeds: `influence_operation`. **Also sharpens** `institutional_permeation` → `deniability_architecture`
  (laundering takedowns through "the platform's rules").

**12. Recruit malign/ignorant agents; fund proxies** — DISARM **T0091 Recruit Malign Actors**
(T0091.001 Recruit Contractors, T0091.002 Recruit Partisans); **T0010 Cultivate Ignorant Agents**;
**T0093.001 Fund Proxies**; **T0014 Prepare Fundraising Campaigns**.
- Def: paying/contracting operatives, cultivating useful-idiot amplifiers, or funding proxy entities.
- Receipt: payment/contract trail; proxy-funding link; coordinated tasking artifact.
- Feeds: `influence_operation`. **Sharpens** both `institutional_permeation` → `deniability_architecture`
  and (on the funding-graph side) the `revolving_door` `funder_multiple_recipients` reading.

**13. Microtarget / segment audiences** — DISARM **T0072 Segment Audiences**;
**T0113 Employ Commercial Analytic Firms**.
- Def: dividing an audience by psychographic/demographic traits to deliver tailored manipulative messaging.
- Receipt: differential message variants by segment; analytics-firm engagement.
- Feeds: `influence_operation`. **Brushes** `cognitive_capture` (personalized steering) — same
  axis-separation note as #10.

**14. Develop owned media / channel assets** — DISARM **T0095 Develop Owned Media Assets**;
**T0151 Channel/Asset** family (owned blogs, forums, channels).
- Def: standing up controlled distribution channels (blogs, forums, Telegram/owned sites) as
  origination points dressed as independent media.
- Receipt: common ownership/registration across "separate" channels.
- Feeds: `influence_operation`. **Sharpens** `institutional_permeation` → `build-parallel-institutions`.

**15. Butterfly attack / impersonate a movement** — DISARM **T0094.002 Utilise Butterfly Attacks**
(under T0094 Infiltrate Existing Networks).
- Def: impersonating members of a real group to discredit it from the inside (false-flag posing).
- Receipt: impostor accounts mimicking a movement's markers while posting discrediting content.
- Feeds: `influence_operation`. **Sharpens** `institutional_permeation` → `front_costume` (inverse:
  wearing the *opponent's* costume rather than a grassroots one).

**DISARM count cataloged: 15 behavioral markers, spanning ~40 underlying DISARM technique/sub-technique
IDs across tactics TA15–TA18.**

---

# Wire-first recommendation (the 3)

Across both frameworks, these three give the most signal for the least integration risk and have the
cleanest validation story:

1. **SemEval `loaded_language`** (Part 1 #1) — the single most frequent technique in the PTC-SemEval20
   corpus, high-precision, trivially cued, and **immediately validatable** against the shipped labeled
   gold set. It is the obvious first detection of the new `persuasion_technique` lens and the proof
   that the SemEval corpus can replace the 7-fixture smoke eval.

2. **SemEval `appeal_to_authority`** (Part 1 #9) — strongest cross-lens payoff: it both anchors the
   new `persuasion_technique` lens *and* sharpens the existing `institutional_permeation`
   `captured_neutral` / `value-as-science` detection (the "experts agree / the science is settled"
   move the books center on). Wiring it tightens a lens that already ships.

3. **DISARM `launder_narratives_through_intermediaries`** (Part 2 #6, T0100 + T0039) — the highest-value
   behavioral marker: it is the exact co-opt-trusted-source / route-through-intermediaries move that
   `institutional_permeation`'s `deniability_architecture/intermediary-laundering` detection describes
   in prose, now given a *behavioral* receipt. It also forces the verdict-discipline design (receipt =
   the origin→intermediary→mainstream hop chain, never an asserted "coordination") that the whole CIB
   lens must inherit — so getting it right first sets the pattern for the rest of DISARM.

The first two stand up the `persuasion_technique` language lens against a real labeled corpus; the
third is the seed of the behavioral `influence_operation` (CIB) lens and the test of its
flag-and-show-receipts guardrail.
