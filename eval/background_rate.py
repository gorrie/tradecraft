#!/usr/bin/env python3
"""Measure each lens's BACKGROUND FIRING RATE, the resolution object a rare lens can own.

WHY THIS EXISTS
---------------
`eval/lens_floor.py` measures the width of the ruler for a lens whose index moves: perturb a
document without changing its method-content, see how far the index drifts, report the
smallest index difference that clears the drift. That object requires the lens to fire on at
least `MIN_LIVE_DOCS` documents. Twelve of sixteen lenses cannot meet it, and the 2026-09-02
cross-tab established why: they fire on effectively nothing in any corpus held. Two register
hypotheses (congressional hearings, then rulemaking comments) were each tested and each
produced nothing, and the cue phrases turned out to be ABSENT from the pool rather than
blocked -- `counterproductivity`'s concept appears once in 600,458 words.

The wrong conclusion is that those lenses need a bigger corpus. The right one is that an index
is the wrong statistic for a rare phenomenon. There is a second resolution object, and it needs
no positives at all:

    A rare lens's resolvable claim is not an index GAP between subjects. It is a subject's
    firing RATE against a measured background rate. The general corpus measures that
    background precisely BECAUSE the phenomenon is absent from it. Zero to three firings per
    ninety-five news-control documents is not a failure to detect. It IS the ruler.

A subject's corpus then either clears the background at its own document count or it does not,
and the minimum detectable rate at a given corpus size is computable in advance. This is what
lets a lens ship honestly as flag-and-show-receipts: a firing rate with a background to beat,
no index, no leaderboard rank.

THE TRAP THIS HARNESS REFUSES
-----------------------------
A background rate computed over a corpus that was gathered BECAUSE the phenomenon is in it is
not a background rate. It is selection on the outcome wearing a statistic's clothes, and it
would bias every claim built on it downward -- making real firings look ordinary.

`corpus/method-specimens.jsonl` is exactly that corpus: every record carries a `lens` field and
a `found_by_term` naming the cue that retrieved it. `corpus/specimens.jsonl` likewise holds
snippets chosen because a pawl's doctrine is in them. Both are RECALL FIXTURES -- they prove a
lens CAN fire, and they must never feed a floor or a background.

So every corpus file declares a role in `ROLES` below, and an undeclared file is a hard error
rather than a silent default. That is not defensive coding for its own sake: this repository
has now been bitten three times by a tool that was blind to one input and therefore blind to
others -- `lens_floor.py` globbed only `*.txt` and measured floors over the Federal Register
alone; `harvest_gold.py` globbed the same plus one hardcoded filename. A new corpus file must
either be classified by a human or stop the measurement.

RECOMPUTABLE, AND WHY THE FLAG IS NOT DECORATION
------------------------------------------------
This project's pitch is that a reader can rebuild the number. A floor measured over material a
reader cannot obtain is internal calibration, not a public statistic. Three of the four
background buckets are US government works with a fetcher and stable public identifiers in the
repo, so a reader can rebuild them exactly. `_news-control` is vendored third-party news text
with no manifest and no fetcher: real material, but not reader-recomputable.

Rates are therefore reported TWICE -- over the full background pool, and over the recomputable
subset alone -- and only the second carries `recomputable: true`. A public surface prints an
MDR only from the second. A single pooled number with a hopeful flag on it would be precisely
the defect this project indicts in the ten studies it critiques.

    python eval/background_rate.py                  # measure, write background-rates.json
    python eval/background_rate.py --markdown       # tables for a RESULTS doc
    python eval/background_rate.py --crosstab       # lens x bucket firing counts
    python eval/background_rate.py --check          # exit 1 if a lens has no background recorded
"""
from __future__ import annotations

import collections
import argparse
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.corpus_docs import documents               # noqa: E402
from tradecraft.detect import detect                       # noqa: E402
from tradecraft.grader import grade_document_for_lens       # noqa: E402
from tradecraft.loader import load_lenses                   # noqa: E402

RATE_FILE = os.path.join(HERE, "background-rates.json")
FLOOR_FILE = os.path.join(HERE, "lens-floors.json")

ALPHA = 0.05
POWER = 0.80

#: A document shorter than this is a fragment: too short to carry a rhetorical move and too
#: short to quote as a receipt. Matches lens_floor's threshold so the two objects describe the
#: same document population.
MIN_WORDS = 60

#: A lens "fires" on a document when its index is above zero -- the same definition
#: `lens_floor.py` uses to decide a document is live. `NOTABLE` is reported alongside it
#: because a receipts-only claim should not rest on one threshold choice: a rate that only
#: exists at index>0 and vanishes at 35 is a rate made of marginal hits.
NOTABLE = 35.0

#: Subject-corpus sizes at which the minimum detectable rate is reported. These are the sizes a
#: real subject dossier actually comes in -- a few dozen documents to a few hundred.
SUBJECT_SIZES = (20, 50, 100, 200)

#: Every corpus file's ROLE and whether a reader can rebuild it. Keys match `Doc.origin` with
#: forward slashes; a directory key covers everything under it.
#:
#:   background     -- not gathered for any lens's phenomenon, so it can measure how often a
#:                     lens fires when the move is (presumed) absent. These are the rulers.
#:   recall-fixture -- gathered BECAUSE the phenomenon is in it. Proves capability; never a
#:                     ruler. Selection on the outcome.
ROLES = {
    "corpus/_calibration-cache": {
        "role": "background",
        "recomputable": True,
        "what": "Federal Register notices; register-matched administrative prose",
        "why": "fetched by docket/notice id, not by any lens cue; rebuildable via "
               "corpus/fetch_federal_register.py",
    },
    "corpus/_news-control": {
        "role": "background",
        "recomputable": False,
        "what": "off-topic news wire copy, in FIXED 3,200-WORD CHUNKS -- not articles",
        "why": "vendored third-party text with no manifest and no fetcher in the repo, so a "
               "reader cannot rebuild this bucket; real background, not recomputable. "
               "AND MEASURED 2026-09-04: 94 of its 95 files are exactly 3,200 words and every "
               "one ends mid-sentence, so they are fixed-size slices of concatenated wire copy "
               "rather than articles. Rates here are fired/n_docs with no length "
               "normalisation, so THE CHUNK SIZE IS A FREE PARAMETER OF EVERY RATE: on "
               "identical prose, repackaging real 300-word articles into 3,200-word chunks "
               "moved sourcing_asymmetry from 2.1% to 12.5%. This bucket is 95 of the 171 "
               "background documents, so it sets the scale of the whole background. A uniform "
               "unit is defensible; it was UNDOCUMENTED, which is what made every rate read "
               "as a property of the prose. See "
               "eval/RESULTS-2026-09-04-truncation-is-the-recurring-defect.md and "
               "tools/truncation_scan.py, which detects this shape anywhere it is pointed",
    },
    # `corpus/news-control.manifest.jsonl` IS DELIBERATELY NOT DECLARED HERE.
    #
    # It was, briefly, on 2026-09-04: role background, recomputable True. It contributes ZERO
    # documents -- it is a manifest of Wikinews revision ids with no `text` field, so
    # corpus_docs skips every row -- and `--check` went on printing "all 16 lenses have a
    # recorded background firing rate" and exiting 0. A declared bucket measuring nothing,
    # passing green, with `recomputable: True` on it, which is the flag that lets a public
    # surface print an MDR. That is the vacuous pass this project holds to be worse than a
    # failure, and the zero-document gate below now catches it.
    #
    # The manifest is a RECIPE for a corpus, not the corpus. The pool it builds is not on disk
    # here by design (the repo carries hashes, the reader fetches text), so nothing in ROLES
    # should claim a role for it until a materialised corpus file exists.
    #
    # AND IT MUST NOT SIMPLY BE ADDED WHEN IT DOES. Those 94 articles have a median of ~300
    # words against `_news-control`'s 3,200-word chunks, and a per-document firing rate falls
    # with length -- so pooling them would drop the recomputable-only background rates and make
    # every lens EASIER to claim above background, with no change to any detector or any
    # subject. Measured on the reported fire counts: sourcing_asymmetry's recomputable upper
    # bound 0.145 -> 0.083, institutional_permeation 0.194 -> 0.098. That is the null loosened
    # through its denominator, which is the one repair this project does not make. Pooling
    # buckets of different length needs a length-invariant unit first (see the note on
    # rate_block), not a ROLES entry.
    "corpus/advocacy-comments.jsonl": {
        "role": "background",
        "recomputable": True,
        "what": "38 substantive public comments on federal rulemakings",
        "why": "retrieved by TOPIC ('surveillance oversight'), not by a lens cue; every record "
               "keeps its regulations.gov comment id, rebuildable via corpus/fetch_regulations.py",
    },
    "corpus/advocacy-specimens.jsonl": {
        "role": "background",
        "recomputable": True,
        "what": "18 congressional hearings",
        "why": "retrieved by TOPIC, not by a lens cue; govinfo package ids retained, "
               "rebuildable via corpus/fetch_govinfo.py",
    },
    "corpus/ai-governance-shoptalk.jsonl": {
        "role": "background",
        "recomputable": True,
        "what": ("46 documents / ~137 kwords of AI-governance and AI-safety institutional "
                 "shop-talk: frontier-lab safety-policy blog posts, AI-governance think-tank "
                 "pieces, standards/framework text, and congressional hearings on AI oversight"),
        "why": ("retrieved by TOPIC (a named institution's AI-safety/governance publication, "
                "or a govinfo hearing search term scoped to AI oversight), not by any lens "
                "cue -- see PREREG-2026-09-08-shoptalk-corpus.md. Built because the "
                "2026-09-07 cue repair found 7 of 13 kept candidate cues occur ZERO times in "
                "either background pool the cut rule is measured against, so the rule had no "
                "evidence to cut them on: those cues are ordinary trade vocabulary in the "
                "register AI-safety/governance people actually write in, and no corpus this "
                "detector was calibrated against contained that register at all. Every record "
                "carries a source_url; rebuildable via corpus/fetch_ai_governance_shoptalk.py"),
    },
    "corpus/method-specimens.jsonl": {
        "role": "recall-fixture",
        "recomputable": True,
        "what": "68 Federal Register measures, unadjudicated candidates for ratchet_series",
        "why": "SELECTED ON THE OUTCOME -- each record carries the `found_by_term` that "
               "retrieved it, so it can never measure how often anything fires by accident. "
               "Refiled 2026-09-03 (W1.9): these were labelled `lens: rollback_asymmetry` and "
               "are Federal Register measures, which is `ratchet_series` material -- an "
               "administrative ratchet read off a SERIES, not a prose lens reading one "
               "document. They now carry `instrument: ratchet_series` and `role: "
               "unadjudicated-candidate`, because every one is `arm: null` with the retrieval "
               "term present in only 13 of 68 texts. They do not yet demonstrate recall for "
               "anything; W2.3's hand-labelling is what would make them ground truth",
    },
    "corpus/specimens.jsonl": {
        "role": "recall-fixture",
        "recomputable": True,
        "what": "5 primary-source doctrine snippets, labeled by pawl",
        "why": "SELECTED ON THE OUTCOME -- gathered because the doctrine is in them",
    },
}


def bucket_of(origin):
    """The ROLES key covering this document, or None if the file is undeclared.

    Buckets, not files, are the unit worth reporting. `Doc.origin` for a text corpus is the
    individual file path, so grouping the cross-tab by origin produced 115 single-document
    columns of `0/1` -- technically the measurement, unreadable as a result.
    """
    key = origin.replace("\\", "/")
    if key in ROLES:
        return key
    for prefix in ROLES:
        if key.startswith(prefix + "/"):
            return prefix
    return None


def role_of(origin):
    """Role record for a document's origin, or None if the file is undeclared."""
    key = bucket_of(origin)
    return ROLES[key] if key else None


def has_candidates(path):
    """True when this path holds any file the corpus loader would even attempt to read.

    The ABSENT/EMPTY distinction in `--check` turns on this. Module scope rather than a closure
    in `main` so the tests exercise the real implementation -- a test carrying its own copy of
    this rule would keep passing after the rule changed, which is the vacuous guard this
    project keeps finding in other people's work.
    """
    if os.path.isfile(path):
        return True
    if not os.path.isdir(path):
        return False
    for _root, _dirs, files in os.walk(path):
        # NO .md HERE. corpus_docs reads only *.txt and *.jsonl, so a bucket holding a README
        # and nothing else would be classified EMPTY -- failing the gate over a file the loader
        # would never have opened. This set must MATCH the loader's, not be a superset of it.
        if any(os.path.splitext(f)[1] in (".txt", ".jsonl") for f in files):
            return True
    return False


def tokens(text):
    return max(1, len(text.split()))


def index_of(text, taxonomy):
    hits = detect(text, taxonomy, backend="cues")
    return grade_document_for_lens(taxonomy, hits, tokens(text)).index


def wilson(k, n, z=1.96):
    """Wilson score interval for a proportion. Correct at k=0, which is the case that matters.

    The normal approximation gives [0, 0] for zero successes, which would claim a background
    rate is known to be exactly zero from 95 documents. It is not: the honest upper bound is
    about 4%, and every rare-lens claim depends on that bound rather than on the point estimate.
    """
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def binom_sf(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p). Exact; n here is at most a few hundred."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    return min(1.0, total)


def critical_count(n, p0, alpha=ALPHA):
    """Smallest firing count in n documents that would be significant against background p0."""
    for k in range(0, n + 2):
        if binom_sf(k, n, p0) <= alpha:
            return k
    return n + 1


def minimum_detectable_rate(n, p0, alpha=ALPHA, power=POWER, step=0.005):
    """Smallest TRUE firing rate a subject of n documents can distinguish from background p0.

    Returns None when no rate up to 1.0 reaches the power target -- which happens when n is too
    small for the test to ever fire, and is a real answer: at this corpus size the lens cannot
    resolve anything, however common the move is.
    """
    k = critical_count(n, p0, alpha)
    if k > n:
        return None
    p1 = p0
    while p1 <= 1.0 + 1e-9:
        if binom_sf(k, n, min(1.0, p1)) >= power:
            return min(1.0, p1)
        p1 += step
    return None


def collect(docs, lenses):
    """Index every (lens, document) cell once. Everything else is a view over this."""
    cells = {}
    for lens_id, taxonomy in sorted(lenses.items()):
        for doc in docs:
            try:
                cells[(lens_id, doc.name)] = index_of(doc.text, taxonomy)
            except Exception:
                # A document the detector cannot process is a missing cell, not a zero: a zero
                # would quietly deflate the background rate it feeds.
                continue
    return cells


#: The RESULTS document whose rate table is GENERATED from `background-rates.json`.
#:
#: It was hand-typed, and by 2026-09-05 it was wrong in two independent ways at once: it
#: carried the pre-refetch rates (`institutional_permeation` 15/171 where the repaired corpus
#: measures 22/171) AND it called `legibility` receipts-only after it had become index-bearing.
#: Two copies of a fact drift; one of them is generated now, and `--check` fails when it is
#: stale, so the copy cannot rot silently again.
DOC = os.path.join(ROOT, "eval", "RESULTS-2026-09-03-background-rates.md")
DOC_BEGIN = "<!-- GENERATED:background-rate-table -- edit background_rate.py, not this -->"
DOC_END = "<!-- /GENERATED:background-rate-table -->"


def render_table(lenses_by_id):
    """The rate table, from either a live `results` dict or a loaded `background-rates.json`.

    One renderer for `--markdown`, the document block, and the freshness check -- a second
    implementation would be the same drift this function exists to end.
    """
    # THE LENGTH-INVARIANT RATE PRINTS BESIDE THE DOCUMENT-FIRING RATE.
    #
    # Issue #7: every rate in this column is fired-documents over n-documents on a pool
    # spanning 140 to 57,458 words, and `P(a document fires)` rises with length for any nonzero
    # underlying rate because firing is an EXTENSIVE MARGIN -- at least one cue anywhere.
    # `occurrence_rate.py` measures the same background as occurrences per 1,000 words, which
    # is length-invariant by construction, and gates that claim.
    #
    # BOTH COLUMNS PRINT and neither is deleted, the way both manipulation rows and both
    # ablation rows print in the sibling bias study: they are different objects with different
    # scopes, and choosing between them after seeing both is the move this project keeps
    # retracting claims for. The document-firing rate remains the published statistic. What
    # changes is that a reader can now see, on the same line, whether it is a length artifact.
    #
    # Read from the JSON rather than recomputed, so this renderer stays cheap and a stale
    # sidecar shows as "--" instead of quietly reporting last week's number.
    occ = _occurrence_sidecar()
    out = ["| lens | state | background fired | rate | 95% upper | MDR n=50 | MDR n=100 "
           "| occ/1k words | length-invariant? |",
           "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for lens_id in sorted(lenses_by_id):
        r = lenses_by_id[lens_id]
        f, b = r["background_full_pool"], r["background_recomputable_only"]
        mdr50, mdr100 = b["mdr"].get("50"), b["mdr"].get("100")
        o = occ.get(lens_id)
        out.append("| `%s` | %s | %d/%d | %.3f | %.3f | %s | %s | %s | %s |"
                   % (lens_id, r["eligible_state"], f["fired"], f["n_docs"],
                      f["rate"] or 0.0, f["wilson95"][1],
                      "--" if mdr50 is None else "%.2f" % mdr50,
                      "--" if mdr100 is None else "%.2f" % mdr100,
                      "--" if not o else "%.4f" % (o["rate_per_1k"] or 0.0),
                      _invariance_note(o)))
    return "\n".join(out)


def _occurrence_sidecar():
    """`occurrence-rates.json` keyed by lens, or {} when it has not been measured here."""
    path = os.path.join(HERE, "occurrence-rates.json")
    if not os.path.exists(path):
        return {}
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except ValueError:
        return {}
    return {r["lens"]: r for r in data.get("lenses", [])}


def _invariance_note(o):
    """What the length-invariance test says about this lens, in the table's own width.

    THREE OUTCOMES AND ONLY ONE IS A YES. A lens too rare to test is not length-invariant --
    it is unmeasured, and printing "yes" for it would be the vacuous pass `occurrence_rate.py`
    fails its own gate over.
    """
    if not o:
        return "not measured"
    if o.get("occurrences", 0) == 0:
        return "no occurrences"
    if o.get("homogeneity_p") is None:
        return "not tested"
    # NO POWER IS A NUMBER, NOT A CATEGORY.
    #
    # This column read "too rare to test" for seven lenses, which was true of the chi-square
    # and is not true of the exact conditional test that replaced it -- that one is valid at
    # any count, so every live lens has a real p-value. What the rare ones lack is POWER, and
    # `detectable_rate_ratio` says how much: the smallest short-vs-long rate ratio the corpus
    # could have caught at 80%. Where that does not exist below 50x, "no evidence" is a
    # statement about the corpus and the column has to say so rather than implying the lens
    # was checked and cleared.
    if o["homogeneity_p"] >= 0.05 and o.get("detectable_rate_ratio") is None:
        return "no evidence, and **no power** (<50x undetectable)"
    if o["homogeneity_p"] < 0.05:
        # Reattributed is not exonerated: say which axis it varies on.
        if o.get("bucket_p") is not None and o["bucket_p"] < 0.05:
            return "**no -- varies by SOURCE TYPE, quote per bucket**"
        if o.get("zero_buckets", 0) >= 2 and (o.get("bucket_concentration") or 0) >= 0.5:
            # COUNT THE BUCKETS IT FIRES IN, do not assume one. This read "fires in one
            # bucket" and `sourcing_asymmetry` fires in two of four (news 0.0994, advocacy
            # specimens 0.0556, and exactly zero in the Federal Register cache and the public
            # comments). The branch tests for concentration, not for a single bucket, and the
            # label has to say what the branch tested.
            live = sum(1 for v in (o.get("bucket_rates") or {}).values() if v.get("occ"))
            total = len(o.get("bucket_rates") or {})
            return "**no -- %d of %d buckets, quote per bucket**" % (live, total)
        return "**no -- length-dependent**"
    # Passed, WITH the ratio it could have caught, so "yes" carries its own resolution.
    r = o.get("detectable_rate_ratio")
    return "yes (could detect %.1fx)" % r if r else "yes"


XT_BEGIN = "<!-- GENERATED:background-crosstab -- edit background_rate.py, not this -->"
XT_END = "<!-- /GENERATED:background-crosstab -->"


def render_crosstab(crosstab, roles):
    """Lens x bucket firing counts. Read from the recorded JSON or a live computation."""
    names = sorted({n for row in crosstab.values() for n in row})
    short = [n.split("/")[-1].replace(".jsonl", "").lstrip("_") for n in names]
    head = ["%s (%s)" % (s, "bg" if roles.get(n, {}).get("role") == "background" else "recall")
            for s, n in zip(short, names)]
    out = ["| lens | " + " | ".join(head) + " |", "|---|" + "---:|" * len(names)]
    for lens_id in sorted(crosstab):
        row = ["%d/%d" % (crosstab[lens_id][n]["fired"], crosstab[lens_id][n]["n"])
               for n in names]
        out.append("| `%s` | %s |" % (lens_id, " | ".join(row)))
    return "\n".join(out)


def doc_block(path=DOC, begin=DOC_BEGIN, end=DOC_END):
    """The generated region of the RESULTS document, or None when the markers are absent."""
    if not os.path.exists(path):
        return None
    text = io.open(path, encoding="utf-8").read()
    a = text.find(begin)
    b = text.find(end, a + 1)
    if a < 0 or b < 0:
        return None
    return text[a + len(begin):b].strip()


def write_doc_block(table, path=DOC, begin=DOC_BEGIN, end=DOC_END):
    """Replace the generated region in place, preserving the file's CRLF line endings."""
    raw = io.open(path, "rb").read()
    crlf = raw.count(b"\r\n")
    text = raw.decode("utf-8")
    a = text.find(begin)
    b = text.find(end, a + 1)
    if a < 0 or b < 0:
        raise SystemExit("%s carries no %s marker" % (path, begin))
    new = text[:a + len(begin)] + "\n" + table + "\n" + text[b:]
    if crlf:
        # This repo's .md files are CRLF and a helper's own line endings ride into what it
        # writes. Normalise, then convert once, rather than trusting whatever `new` holds.
        new = new.replace("\r\n", "\n").replace("\n", "\r\n")
    io.open(path, "wb").write(new.encode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sync-doc", action="store_true",
                    help="rewrite the generated table in the RESULTS document")
    ap.add_argument("--markdown", action="store_true", help="tables for a RESULTS document")
    ap.add_argument("--crosstab", action="store_true", help="lens x corpus-bucket firing counts")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any lens has no recorded background rate")
    args = ap.parse_args()

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    if not lenses:
        print("no lenses loaded from detectors/")
        return 1

    if args.check:
        if not os.path.exists(RATE_FILE):
            print("NO BACKGROUND RATES RECORDED at %s" % os.path.relpath(RATE_FILE, ROOT))
            print("Run: python eval/background_rate.py")
            return 1
        recorded = json.load(io.open(RATE_FILE, encoding="utf-8"))
        missing = [k for k in lenses if k not in recorded.get("lenses", {})]
        if missing:
            print("LENSES WITH NO BACKGROUND RATE: %s" % ", ".join(sorted(missing)))
            print("Run: python eval/background_rate.py")
            return 1
        # A DECLARED BUCKET THAT CONTRIBUTES NOTHING MUST NOT PASS.
        #
        # Added 2026-09-04 after review. `corpus/news-control.manifest.jsonl` was declared here
        # as `role: background, recomputable: True` and contributes ZERO documents -- it is a
        # manifest of revision ids with no `text` field, so corpus_docs skips every row. The
        # gate said "all 16 lenses have a recorded background firing rate" and exited 0 against
        # a rates file that predated the declaration entirely. Declaring a background bucket
        # and measuring nothing from it is the vacuous pass this project holds to be worse than
        # a failure, and the flag is load-bearing: `recomputable` is what lets a public surface
        # print an MDR.
        # Count through bucket_of, which is the one place that knows a ROLES key can be a
        # directory prefix and that Doc.origin arrives with the platform's separator. A second
        # implementation of that mapping here would be a second thing to keep in step.
        present = collections.Counter(
            bucket_of(d.origin) for d in documents(min_words=MIN_WORDS))

        # ABSENT IS NOT EMPTY, and conflating them makes this gate fire on a clean checkout.
        # `corpus/_news-control` and `corpus/_calibration-cache` are gitignored, so CI has
        # neither directory at all -- and the first pipeline to run this check reported both as
        # "declared corpus entries with zero documents", which is a true sentence about a
        # situation that is not a defect. The defect this gate exists for is a bucket that IS
        # in the tree and yields nothing (a manifest of ids declared as a corpus). A bucket
        # that is simply not in this checkout is unverifiable here, and saying so beats both
        # failing and going quiet -- the same distinction tools/freshness_gate.py draws
        # between "stale" and "cannot be verified without the mirror".
        # "IS IT HERE" IS ABOUT THE DATA, NOT ABOUT THE PATH.
        #
        # This was `os.path.exists(origin)`, which is right for a declared FILE and wrong for a
        # declared DIRECTORY the moment anything at all is committed into it. `_news-control` is
        # gitignored; on 2026-09-05 its `.truncation.json` was force-added -- correctly, the
        # declaration is documentation -- and from then on CI saw a directory that exists, holds
        # none of its 95 .txt files, and got reported as "declared bucket with zero documents",
        # failing the pipeline over a bucket that is simply not checked out.
        #
        # The defect this gate exists for is a bucket whose data IS here and yields nothing --
        # a manifest of ids declared as a corpus. So: a path holding no file this loader would
        # even attempt is ABSENT; a path holding candidate data files that produce zero
        # documents is EMPTY, and still fails. news-control.manifest.jsonl is a file, exists,
        # and yields nothing, so it fails exactly as before.
        empty, absent = [], []
        for origin in sorted(ROLES):
            if present.get(origin):
                continue
            (empty if has_candidates(os.path.join(ROOT, origin))
             else absent).append(origin)

        if absent:
            print("not in this checkout, so not verifiable here: %s" % ", ".join(absent))
        if empty:
            print("DECLARED CORPUS ENTR%s WITH ZERO DOCUMENTS:"
                  % ("Y" if len(empty) == 1 else "IES"))
            for origin in empty:
                rec = ROLES[origin]
                print("  %-46s role=%s recomputable=%s"
                      % (origin, rec["role"], rec["recomputable"]))
            print()
            print("A declared bucket that measures nothing is not a bucket. Either it holds")
            print("text this loader can read, or it should not be in ROLES claiming a role --")
            print("a manifest of ids is a RECIPE for a corpus, not the corpus.")
            return 1

        # THE PROSE MUST MATCH THE NUMBERS. The RESULTS document's rate table was hand-typed
        # and drifted twice over without anything noticing: pre-refetch rates, and a lens
        # labelled receipts-only after it became index-bearing.
        blocks = [(doc_block(), render_table(recorded["lenses"]), "rate table"),
                  (doc_block(begin=XT_BEGIN, end=XT_END),
                   render_crosstab(recorded["crosstab_fired_by_bucket"],
                                   recorded.get("corpus_roles") or ROLES), "cross-tab")]
        block = blocks[0][0]
        for got, want, what in blocks:
            if got is None:
                print("NOTE: %s carries no generated %s markers; run --sync-doc"
                      % (os.path.relpath(DOC, ROOT), what))
            elif got != want:
                print("THE RESULTS DOCUMENT'S %s IS STALE: %s"
                      % (what.upper(), os.path.relpath(DOC, ROOT)))
                print("Run: python eval/background_rate.py --sync-doc")
                return 1

        print("all %d lens(es) have a recorded background firing rate" % len(lenses))
        print("all %d declared corpus entr%s present in this checkout contribute documents"
              % (len(ROLES) - len(absent), "y" if len(ROLES) - len(absent) == 1 else "ies"))
        if block is not None:
            print("the RESULTS document's rate table and cross-tab match the recorded rates")
        return 0

    if args.sync_doc:
        if not os.path.exists(RATE_FILE):
            print("no recorded rates yet; run the tool with no flags first")
            return 1
        recorded = json.load(io.open(RATE_FILE, encoding="utf-8"))
        write_doc_block(render_table(recorded["lenses"]))
        write_doc_block(render_crosstab(recorded["crosstab_fired_by_bucket"],
                                        recorded.get("corpus_roles") or ROLES),
                        begin=XT_BEGIN, end=XT_END)
        print("synced the generated rate table and cross-tab in %s"
              % os.path.relpath(DOC, ROOT))
        return 0

    every = documents(min_words=MIN_WORDS)
    if not every:
        print("no corpus documents found under corpus/")
        return 1

    # Classify before measuring. An undeclared corpus file stops the run: the alternative is a
    # silent default, and a silent default is how a recall fixture ends up inside a background.
    undeclared = sorted({d.origin for d in every if role_of(d.origin) is None})
    if undeclared:
        print("UNDECLARED CORPUS FILE(S) -- classify in ROLES before measuring:")
        for origin in undeclared:
            print("  %s" % origin)
        print("\nA background rate must know which of its documents were selected on the")
        print("phenomenon. Add each file to ROLES in eval/background_rate.py as either")
        print("'background' (not gathered for any lens) or 'recall-fixture' (gathered because")
        print("the move is in it).")
        return 1

    background = [d for d in every if role_of(d.origin)["role"] == "background"]
    fixtures = [d for d in every if role_of(d.origin)["role"] == "recall-fixture"]
    recomputable = [d for d in background if role_of(d.origin)["recomputable"]]

    cells = collect(every, lenses)

    floors = {}
    if os.path.exists(FLOOR_FILE):
        floors = json.load(io.open(FLOOR_FILE, encoding="utf-8")).get("lenses", {})

    def rate_block(pool, lens_id):
        seen = [cells[(lens_id, d.name)] for d in pool if (lens_id, d.name) in cells]
        n = len(seen)
        fired = sum(1 for v in seen if v > 0)
        notable = sum(1 for v in seen if v >= NOTABLE)
        lo, hi = wilson(fired, n)
        p0_hi = hi  # a subject must clear the UPPER bound of the background, not its point
        block = {
            "n_docs": n,
            "fired": fired,
            "notable": notable,
            "rate": round(fired / n, 4) if n else None,
            "wilson95": [round(lo, 4), round(hi, 4)],
            "mdr": {},
        }
        for size in SUBJECT_SIZES:
            mdr = minimum_detectable_rate(size, p0_hi)
            block["mdr"][str(size)] = None if mdr is None else round(mdr, 3)
            block.setdefault("critical_count", {})[str(size)] = critical_count(size, p0_hi)
        return block

    results = {}
    for lens_id in sorted(lenses):
        full = rate_block(background, lens_id)
        recomp = rate_block(recomputable, lens_id)
        fixture = rate_block(fixtures, lens_id)
        has_floor = lens_id in floors
        results[lens_id] = {
            "background_full_pool": full,
            "background_recomputable_only": recomp,
            "recall_fixtures": fixture,
            "has_index_floor": has_floor,
            # The state a lens is ELIGIBLE for from measurement alone. The actual ruling is a
            # per-lens genre-and-sourcing decision (the plan's CP2) and is the author's, not
            # this script's. "index-bearing" here means only that the index floor exists.
            "eligible_state": "index-bearing" if has_floor else "receipts-only",
        }

    bucket_names = sorted({bucket_of(d.origin) for d in every})
    buckets = {}
    for name in bucket_names:
        rec = ROLES[name]
        buckets[name] = {
            "role": rec["role"],
            "recomputable": rec["recomputable"],
            "n_docs": sum(1 for d in every if bucket_of(d.origin) == name),
            "what": rec["what"],
            "why": rec["why"],
        }

    crosstab = {}
    for lens_id in sorted(lenses):
        row = {}
        for name in bucket_names:
            pool = [d for d in every if bucket_of(d.origin) == name]
            seen = [cells[(lens_id, d.name)] for d in pool if (lens_id, d.name) in cells]
            row[name] = {
                "fired": sum(1 for v in seen if v > 0),
                "n": len(seen),
            }
        crosstab[lens_id] = row

    # The shared floors contract (the plan's section 2a). One record shape, emitted by every
    # instrument, consumed by the observatory, export_web, score.py and the paper's floor table.
    # A number with no record beside it does not publish.
    contract = []
    for lens_id in sorted(lenses):
        r = results[lens_id]
        for scope, key, recomp_flag in (
            ("full-pool", "background_full_pool", False),
            ("recomputable-only", "background_recomputable_only", True),
        ):
            b = r[key]
            contract.append({
                "claim": "%s fires above background (%s)" % (lens_id, scope),
                "instrument": "lens",
                "state": r["eligible_state"],
                "statistic": "firing-rate",
                "null": "background-rate",
                "n": b["n_docs"],
                "threshold_p95": round(b["wilson95"][1], 4),
                "mde": b["mdr"].get("100"),
                "measured": DATE,
                "recomputable": recomp_flag,
                "source": "eval/background_rate.py",
            })

    payload = {
        "_note": ("Per-lens BACKGROUND FIRING RATE: how often a lens fires on documents not "
                  "gathered for it. The resolution object for a rare lens, which cannot hold an "
                  "index floor. A subject's firing rate is a finding only when it clears the "
                  "UPPER Wilson bound of this background at the subject's own document count. "
                  "Recall fixtures (selected on the phenomenon) are measured and reported but "
                  "never feed a background. Regenerate with python eval/background_rate.py"),
        "measured": DATE,
        "definitions": {
            "fires": "lens index > 0 on the document (same definition lens_floor uses for live)",
            "notable": "lens index >= %.1f" % NOTABLE,
            "min_words": MIN_WORDS,
            "alpha": ALPHA,
            "power": POWER,
            "mdr": ("smallest TRUE firing rate a subject corpus of N documents can distinguish "
                    "from the background's upper Wilson bound, exact binomial, one-sided"),
        },
        "corpus_roles": buckets,
        "pool_sizes": {
            "all_documents": len(every),
            "background": len(background),
            "background_recomputable": len(recomputable),
            "recall_fixtures": len(fixtures),
        },
        "lenses": results,
        "crosstab_fired_by_bucket": crosstab,
        "floor_records": contract,
    }
    io.open(RATE_FILE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, indent=2) + "\n")

    if args.crosstab:
        print(render_crosstab(crosstab, ROLES))
        return 0

    if args.markdown:
        print(render_table(results))
        return 0

    print("BACKGROUND FIRING RATES -- how often each lens fires when the move is not there")
    print("cues backend, %d document(s) >= %d words" % (len(every), MIN_WORDS))
    print("  background pool      %3d  (%d reader-recomputable)"
          % (len(background), len(recomputable)))
    print("  recall fixtures      %3d  (measured, never a ruler)" % len(fixtures))
    print("")
    print("%-28s %-14s %10s %9s %9s" % ("lens", "eligible", "bg fired", "95% up", "MDR@100"))
    for lens_id in sorted(lenses):
        r = results[lens_id]
        f = r["background_full_pool"]
        b = r["background_recomputable_only"]
        mdr = b["mdr"].get("100")
        print("%-28s %-14s %10s %9.3f %9s"
              % (lens_id, r["eligible_state"],
                 "%d/%d" % (f["fired"], f["n_docs"]), f["wilson95"][1],
                 "--" if mdr is None else "%.2f" % mdr))
    print("")
    print("Read this as: a subject corpus of 100 documents can only demonstrate a lens is")
    print("firing above background if its TRUE rate is at least the MDR column. A lens with a")
    print("high background needs a much louder subject before anything is resolvable.")
    print("")
    print("wrote %s" % os.path.relpath(RATE_FILE, ROOT))
    return 0


#: Stamped once per run so every emitted record carries the same date, and so a re-run that
#: changes nothing produces a byte-identical file except for this line.
DATE = __import__("datetime").date.today().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
