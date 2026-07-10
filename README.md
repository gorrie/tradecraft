# Tradecraft

**An open, reproducible framework for detecting and grading influence *tradecraft* — the methods, not the ideology.**

*Working name; rename welcome. Built in the lineage of OpenSecrets / LittleSis / GovTrack: accountability tooling that shows its work.*

---

## What it is

A **pluggable detection-and-grading framework**. Each *lens* is a versioned taxonomy of
method-markers (the recurring tells of a kind of influence operation). A shared, deterministic
**weighted grader** scores a text against a lens, then aggregates those scores across any input:
a **subject** (a person/org's corpus), a **URL**, a **timeline** (dated documents, to show
escalation), or a raw passage.

Lenses are **independent and composable**. Running several produces a **profile** — a vector
across lenses — never a single blended number. Institutional capture and cognitive steering are
different things; the tool keeps them on separate axes.

## The lenses (detector modules)

| Lens | Measures | Seeded from |
|------|----------|-------------|
| `institutional_permeation` | **Institutional moves** — gradualist capture/permeation tradecraft (left *and* right). This is *The Ratchet*'s domain and stays a discrete, well-scoped module. | `research-fabian-permeation-genealogy.md`, `research-corporate-permeation.md` |
| `cognitive_capture` | AI-mediated persuasion, sycophancy, recommender steering, companion capture. *Quiet Autocomplete*'s domain. | `research-cognitive-capture.md` |
| `adept_speech` | Occult / mystery-school power register — apophatic framing, secret knowledge, teleological work, initiatory address (8 marker families). *The Hidden Fire*'s domain. | book corpus + adept-speech spec |
| `network_brokerage` | Structural position in the entity graph — high betweenness, hub degree, cross-group brokerage. Graph-based, ideology-blind. | ratchet-mcp entity graph |
| `revolving_door` | Career/funding topology — monitor↔monitored circulation, gov↔industry crossing. | ratchet-mcp careers |
| `legibility` | **Legibility as control (Scott)** — standardize / register / make-visible / manage-to-the-metric. The Ratchet's structural backbone (the click before the pawl). | Scott, *Seeing Like a State* |
| `counterproductivity` | **Iatrogenesis (Illich)** — the remedy produces the harm, radical monopoly, disabling professions, means-become-ends. The Ratchet's failure-mode signature. | Illich, *Medical Nemesis* / *Tools for Conviviality* |
| `distributed_accountability` | **No-one-decides (Kierkegaard/Nietzsche)** — diffuse agency, jurisdiction over truth, dissent-as-sin, unfalsifiable consensus. The attribution-gap signature. | the crowd / ascetic-priest theses |
| `inevitability_framing` | **Resistance-is-futile** — TINA, right-side-of-history, adapt-or-be-left-behind. The forward-pointed Fabian "inevitability of gradualness." | Fabian inevitability thesis |

A new lens is a new YAML taxonomy dropped in `detectors/`. Nothing else changes.

## Two lanes: prose and graph

The lenses split by what they read. **Text lenses** read prose with an LLM (`detect.py`) — or, for
an offline/CI floor, with the deterministic `cues` backend (literal cue-phrase matching, no key, no
model). **Graph lenses** (`revolving_door`, `network_brokerage`) read entity topology with pure
arithmetic (`structural.py`); running them on prose would be a category error, so the prose lane
excludes them.

- **Grade one document** under one lens: `python -m tradecraft.cli grade --file speech.txt --lens inevitability_framing`
- **The texts-by-person lane** — all text lenses over a subject's texts, aggregated per subject,
  never blended: `python -m tradecraft.cli subject --id Rubin --texts texts.jsonl` (offline `cues`
  default; `--backend auto` for the model read). `subject.py` is the public API
  (`grade_person`, `grade_text`, `text_lenses`); the Ratchet MCP server calls it to profile a
  dataset person by how their own words operate.
- **The combined profile** — both lanes for one subject, each lens on its own axis, never blended:
  `python -m tradecraft.cli profile --id Rubin --ratchet-dir <ratchet>/server/data --texts texts.jsonl`.
  `profile.py` runs **both** graph lenses on the topology (via `adapters.write_ratchet_graph`):
  `network_brokerage` from adjacency + sector, and `revolving_door` from the subject's affiliation
  edges — on an untyped graph it reports cross-sector affiliation breadth (each receipt annotated
  that this is breadth, not a proven time-ordered trajectory); on a rel-typed graph it reports the
  career-move trajectory. Plus the text lenses on the words, returning `{graph, text}` — the network
  position and the rhetoric, side by side, as separate facts, not one score.

## Intake — where material comes from

`adapters.py` turns sources into documents to grade. The aim is to read from **as many places as
feasible** with the core staying dependency-free (network/PDF deps are lazy, optional):

| Adapter | Source |
|---------|--------|
| `from_text` | a raw string |
| `from_file` / `from_dir` | a text/markdown file, or a whole folder of them (speeches, transcripts, op-eds) |
| `from_jsonl` | a JSONL texts store (the texts-by-person format) — the bridge from stored evidence |
| `from_url` | a web page (browser UA, crude visible-text extraction) |
| `from_pdf` | a PDF (reports, testimony, white papers) — needs optional `pypdf`/`pdfminer.six` |
| `from_x_export` | an X/Twitter export from the `x_ingest` tool — offline, reads the file, never calls the API |
| `from_subject` | a dataset person's sourced URLs from the entity graph (fetch each via `from_url`) |
| `group_timeline` | order dated documents oldest-first for the escalation view |

## The one principle

**Detect the method, not the ideology.** Markers key on *how* a text operates, never on whose
team it's on. The `institutional_permeation` lens fires the same on a Fabian tract and a Powell
memo. That is what makes the tool both novel and non-factional.

## The one ethic (load-bearing)

**It flags and shows the receipts. It never renders a verdict.** The signal is **breadth ×
density × co-occurrence**, surfaced *with the exact spans* so a human adjudicates. Everyone uses
one marker; the question is whether many fire together, densely, across a corpus. There is no
black-box "guilt" score — that would make this the captured-neutral oracle the books warn about.
Every detection cites the gold example (and its source) that defines it.

## Reproducible by construction

- Taxonomies are **data** (versioned YAML), not code. Tunable via pull request.
- The grader is **deterministic** — given the same hits, the same grade. (The LLM produces hits;
  the grader does math you can re-run and audit.)
- The **research that seeds each detection is cited inline** and ships with the books' dossiers.
- CI runs the test suite. The taxonomy evolves through **issues** (propose a detection, report a
  false positive) and PRs.

## Status

`v0.1` scaffold — core schema, grader, two seeded lenses, grader tests. See `detectors/` for the
taxonomies and `tradecraft/grader.py` for the scoring model.

## Related projects

Tradecraft is the prose-grader in a three-repo capture-measurement toolkit:

- **[ratchet-mcp](https://github.com/gorrie/ratchet-mcp)** — MCP server + curated
  dataset of named persons/institutions across the US control grid. It calls
  Tradecraft's TEXT lenses (`grade_person_texts`) to profile a dataset person's
  own words; Tradecraft supplies the prose half, ratchet-mcp the graph half.
- **[bias-study](https://github.com/gorrie/bias-study)** — a reproducible audit of
  institutional-skepticism framing across 36+ LLMs. Its **[The Wash](https://github.com/gorrie/bias-study/blob/main/results/THE-WASH-2026-06-10.md)**
  instrument validates a low-flinch abliterated judge — exactly the kind of
  context-reading model Tradecraft's `verified_cue_receipts` verify step runs as
  its `local`/`cloud` backend to reject false-positive cue hits. The Wash proves
  *why* an ordinary aligned model is a poor referee; Tradecraft is what consumes a
  good one.
- **[evilrobots.lol](https://evilrobots.lol)** — the narrative companion (Evil
  Robots Series, 4LULZ), including the public Capture Leaderboard this grader feeds.

## License

Apache-2.0 — governed by the `LICENSE` at the repository root.
