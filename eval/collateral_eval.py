#!/usr/bin/env python3
"""The working detectors on the record's real-world COLLATERAL -- the first evaluation.

WHAT "COLLATERAL" IS HERE
-------------------------
The verbatim public statements of persons in the Ratchet dataset:
`research/ratchet-mcp/server/data/texts.jsonl` -- speeches, op-eds, posts, testimony, each
with a source URL, attributed to a `person_id` in `people.jsonl`. It is the material the
texts-by-person lane (`tradecraft.subject`) was built to read and the material THE RECORD
already tracks. It is NOT the author's manuscripts (never a detector corpus; the instrument
page is the one deliberate exception) and it is NOT the PTC benchmark (that is the
detector's calibration corpus, `detection_census.py`).

Two rollups. Per PERSON, because that is the unit the texts are attributed to. Per
LEADERBOARD INSTITUTION, only where the graph affiliates a person-with-texts to a board
institution by an edge -- reported as "what the affiliated persons' words exhibit", never as
the institution's own output. Most board institutions have no collateral on hand and the
output says so per row rather than leaving the cell blank.

WHAT RUNS
---------
* tradecraft, `cues` backend: every TEXT lens (graph lenses excluded, as in `subject.py`),
  the shipped taxonomy unchanged (hash recorded). Deterministic; the same engine
  `/tech/instrument/` and `/tech/tradecraft/` run in the browser (`test_engine_parity.py`).
* the capture scanner: the SHIPPED `scanner.js` + `capture-cats.js`, driven through node by
  `scanner_harness.js` -- no second copy of its wordlist or formula.
* NOT the LLM find/verify stage: the local 14B is held by the detached Phase-1.2
  measurement, and its 37% span-fabrication rate is an open defect (RESULTS-2026-09-07-llm-
  find-stage.md). Recorded as not run, not as null.

RULERS
------
Every rate is printed beside the ruler the public surfaces already print: the lens's
general-prose background from `background-rates.json` (documents fired, Wilson 95%) and
`occurrence-rates.json` (cue occurrences per 1,000 words, exact Poisson; the WIDER of the
exact and quasi-Poisson intervals is the one quoted, per that file's own rule). Verdicts are
interval comparisons, never point comparisons. A lens with zero occurrences prints the
smallest multiple of its background this corpus could have detected -- "no evidence, and no
power" is a different sentence from "absent".

PRE-REGISTERED
--------------
`PREREG-2026-09-07-collateral-eval.md`, committed before the first full run; predictions are
scored in `RESULTS-2026-09-07-collateral-eval.md`. The 40-span hand-read sample is drawn
here with a fixed seed and written into the JSON so the reading can be checked span by span.

    python eval/collateral_eval.py             # run, write collateral-eval.json, print the report
    python eval/collateral_eval.py --markdown  # the report only (recomputed)
    python eval/collateral_eval.py --check     # exit 1 if collateral-eval.json is stale; 2 if node
                                               # is missing and the scanner half cannot be verified
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SERIES = os.path.dirname(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft.detect import detect  # noqa: E402
from tradecraft.subject import GRAPH_LENSES  # noqa: E402
from background_rate import wilson, tokens  # noqa: E402
from occurrence_rate import poisson_ci, _chi2_ppf  # noqa: E402

DATA = os.path.join(SERIES, "research", "ratchet-mcp", "server", "data")
TEXTS = os.path.join(DATA, "texts.jsonl")
PEOPLE = os.path.join(DATA, "people.jsonl")
INSTS = os.path.join(DATA, "institutions.jsonl")
EDGES = os.path.join(DATA, "edges.jsonl")
RECEIPTS = os.path.join(DATA, "receipts.jsonl")
LEADERBOARD = os.path.join(SERIES, "website", "data", "capture_leaderboard.json")
DETECTORS = os.path.join(REPO, "detectors")
BACKGROUND = os.path.join(HERE, "background-rates.json")
OCCURRENCE = os.path.join(HERE, "occurrence-rates.json")
SCANNER = os.path.join(SERIES, "website", "static", "tech", "capture-scanner", "scanner.js")
CATS = os.path.join(SERIES, "website", "static", "tech", "_kit", "capture-cats.js")
HARNESS = os.path.join(HERE, "scanner_harness.js")
OUT = os.path.join(HERE, "collateral-eval.json")
PREREG = "PREREG-2026-09-07-collateral-eval.md"

SEED = 20260907
SAMPLE_N = 40
RARE_LENS_MAX = 3          # every hit from a lens with <= this many hits is read, not sampled
CONTEXT = 120
ONE_CUE_SHARE = 0.80       # a lens whose top detection carries >= this share of its occurrences
ONE_CUE_MIN = 5            # ... given at least this many occurrences, is flagged "one cue"


def jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def _normalise(b: bytes) -> bytes:
    """CRLF -> LF before hashing. Every input hashed here is text.

    WHY: these hashes are a provenance record checked in CI, and they were computed over RAW
    BYTES. The repository stores these files with LF in the index and checks them out with
    CRLF on Windows (`git ls-files --eol` reports `i/lf  w/mixed`), so an artifact generated on
    Windows recorded the CRLF hash and CI, on Linux, computed the LF hash. The two can never
    agree. `collateral-eval` and `collateral-pass2` therefore failed on EVERY push for hours --
    and because the Pages job is gated behind verify, the site stopped deploying entirely,
    including a correction that removed a false factual claim about six named authors.

    Nothing was ever stale. The gate was reporting a line-ending difference as data drift, in
    the only environment where it mattered, and saying only "differs from a fresh run".
    """
    return b.replace(b"\r\n", b"\n")


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(_normalise(fh.read())).hexdigest()[:16]


def taxonomy_hash():
    h = hashlib.sha256()
    for lens in sorted(os.listdir(DETECTORS)):
        p = os.path.join(DETECTORS, lens, "taxonomy.yaml")
        if os.path.exists(p):
            with open(p, "rb") as fh:
                h.update(_normalise(fh.read()))
    return h.hexdigest()[:16]


def r4(x):
    return None if x is None else round(float(x), 4)


# ── the two rulers ────────────────────────────────────────────────────────────

def rulers():
    bg = json.load(open(BACKGROUND, encoding="utf-8"))
    occ = json.load(open(OCCURRENCE, encoding="utf-8"))
    out = {}
    for lid, rec in (bg.get("lenses") or {}).items():
        b = rec.get("background_full_pool") or {}
        out[lid] = {"docs_n": b.get("n_docs"), "docs_fired": b.get("fired"),
                    "docs_rate": b.get("rate"), "docs_wilson95": b.get("wilson95"),
                    "eligible_state": rec.get("eligible_state")}
    for rec in occ.get("lenses") or []:
        lid = rec.get("lens")
        if lid not in out:
            continue
        exact, quasi = rec.get("ci95") or [None, None], rec.get("ci95_quasi") or rec.get("ci95")
        # The wider interval is the one a public surface may quote (occurrence_rate.py).
        wide = quasi if quasi and exact and (quasi[1] - quasi[0]) > (exact[1] - exact[0]) else exact
        out[lid].update({"per_1k": rec.get("rate_per_1k"), "per_1k_ci95": wide,
                         "per_1k_kwords": rec.get("kwords"), "per_1k_occurrences": rec.get("occurrences"),
                         "overdispersed": rec.get("overdispersed")})
    return out


def min_detectable_per_1k(kwords, bg_hi):
    """Smallest per-1k rate whose exact-Poisson LOWER bound clears the background's upper
    bound at this exposure -- the honest statement of what a zero (or small count) can say."""
    if not kwords or bg_hi is None:
        return None
    for c in range(1, 100000):
        lo = _chi2_ppf(0.025, 2 * c) / 2.0 / kwords
        if lo > bg_hi:
            return round(c / kwords, 4)
    return None


# ── collateral ────────────────────────────────────────────────────────────────

def load_collateral():
    texts = jsonl(TEXTS)
    for n, t in enumerate(texts):
        t.setdefault("id", f"{t['person_id']}#{n}")
    texts.sort(key=lambda t: (t["person_id"], t["id"]))
    people = {p["id"]: p for p in jsonl(PEOPLE)}
    return texts, people


RESEARCH_ENTITIES = os.path.join(SERIES, "website", "data", "research-entities.json")


def _entity_index():
    """label -> canonical id and research-entities id -> canonical id, by the rule
    tools/build_record.py uses: the graph id (people/institutions.jsonl) is canonical, a
    research-entities record with the same label resolves to it, otherwise it is its own."""
    by_label = {}
    for rec in jsonl(PEOPLE) + jsonl(INSTS):
        by_label.setdefault((rec.get("label") or "").lower(), rec["id"])
    alias = {}
    re_data = json.load(open(RESEARCH_ENTITIES, encoding="utf-8")) if os.path.exists(RESEARCH_ENTITIES) else {}
    for ent in re_data.get("entities", []):
        name = (ent.get("name") or "").lower()
        alias[ent["id"]] = by_label.get(name, ent["id"])
        by_label.setdefault(name, ent["id"])
    return by_label, alias, re_data.get("edges", [])


def board_institutions():
    """leaderboard institution label -> the entity id the record puts its board row on."""
    by_label, _, _ = _entity_index()
    rows = json.load(open(LEADERBOARD, encoding="utf-8")) if os.path.exists(LEADERBOARD) else []
    return {r["institution"]: by_label.get(r["institution"].lower()) for r in rows}


def affiliations():
    """Undirected adjacency over the graph edges AND the research-entities edges, the latter
    remapped onto canonical ids -- the same edge set THE RECORD traces over."""
    _, alias, re_edges = _entity_index()
    adj = defaultdict(set)
    for e in jsonl(EDGES) + list(re_edges):
        s, t = alias.get(e.get("source"), e.get("source")), alias.get(e.get("target"), e.get("target"))
        if s and t:
            adj[s].add(t)
            adj[t].add(s)
    return adj


# ── the two detectors ─────────────────────────────────────────────────────────

QUOTE_SPAN_MAX = 600      # a quotation longer than this is a block quote, not a phrase in the speaker's mouth


def quoted_ranges(text):
    """Character ranges lying between paired quotation marks (straight or curly), each pair no
    further apart than QUOTE_SPAN_MAX. A MEASUREMENT of how often a fired span sits inside
    someone else's words (pre-registered R9 in PREREG-2026-09-07-cue-repair.md); nothing is
    suppressed on its strength."""
    out = []
    opens = [(m.start(), m.group()) for m in re.finditer(r'[“"]', text)]
    closes = [m.start() for m in re.finditer(r'[”"]', text)]
    used = set()
    for a, ch in opens:
        for b in closes:
            if b > a and b not in used and b - a <= QUOTE_SPAN_MAX:
                # a straight quote closes a straight quote; a curly opener wants a curly closer
                if (ch == '"' and text[b] == '"') or (ch == '“' and text[b] == '”'):
                    out.append((a, b))
                    used.add(b)
                    break
    return out


def in_quotes(ranges, lo, hi):
    return any(a < lo and hi <= b for a, b in ranges)


def run_tradecraft(texts, lenses):
    """Per text, per lens: raw cue occurrences (the receipts) and the detections they fired."""
    out = []
    for t in texts:
        words = tokens(t["text"])
        qr = quoted_ranges(t["text"])
        per_lens = {}
        for lid, tax in lenses.items():
            hits = detect(t["text"], tax, backend="cues")
            per_lens[lid] = {
                "occurrences": len(hits),
                "detections": dict(sorted(Counter(h.detection_id for h in hits).items())),
                "spans": [{"detection": h.detection_id, "start": h.char_start, "end": h.char_end,
                           "span": h.span, "cue": h.rationale.replace("deterministic cue match: ", ""),
                           "in_quotes": in_quotes(qr, h.char_start or 0, h.char_end or 0)}
                          for h in sorted(hits, key=lambda h: (h.char_start or 0, h.detection_id))],
            }
        out.append({"id": t["id"], "person_id": t["person_id"], "url": t.get("url"),
                    "date": t.get("date"), "words": words, "lenses": per_lens})
    return out


def run_scanner(texts):
    node = shutil.which("node")
    if not node or not (os.path.exists(SCANNER) and os.path.exists(CATS)):
        return None
    r = subprocess.run([node, HARNESS, CATS, SCANNER], input=json.dumps([t["text"] for t in texts]),
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
    if r.returncode:
        raise RuntimeError(f"scanner harness failed: {r.stderr.strip()[:300]}")
    res = json.loads(r.stdout)
    return [{"id": t["id"], "person_id": t["person_id"], **m} for t, m in zip(texts, res)]


# ── summaries ─────────────────────────────────────────────────────────────────

def lens_table(docs, lenses, rul):
    n = len(docs)
    kwords = sum(d["words"] for d in docs) / 1000.0
    rows = {}
    for lid in sorted(lenses):
        occ = sum(d["lenses"][lid]["occurrences"] for d in docs)
        fired = sum(1 for d in docs if d["lenses"][lid]["occurrences"])
        dets = Counter()
        for d in docs:
            dets.update(d["lenses"][lid]["detections"])
        ci = poisson_ci(occ, kwords) if kwords else (None, None)
        w = wilson(fired, n)
        ru = rul.get(lid, {})
        bg_ci = ru.get("per_1k_ci95") or [None, None]
        # Interval comparison on the length-invariant unit. Never a point comparison.
        if bg_ci[0] is None or ci[0] is None:
            verdict = "no ruler"
        elif ci[0] > bg_ci[1]:
            verdict = "above background"
        elif ci[1] < bg_ci[0]:
            verdict = "below background"
        else:
            verdict = "indistinguishable from background"
        mdr = min_detectable_per_1k(kwords, bg_ci[1]) if bg_ci[1] is not None else None
        top = dets.most_common(1)[0] if dets else None
        one_cue = bool(top and occ >= ONE_CUE_MIN and top[1] / occ >= ONE_CUE_SHARE)
        quoted = sum(1 for d in docs for s in d["lenses"][lid]["spans"] if s.get("in_quotes"))
        rows[lid] = {
            "in_quotes": quoted, "in_quotes_share": r4(quoted / occ) if occ else None,
            "state": ru.get("eligible_state"),
            "docs_n": n, "docs_fired": fired, "docs_rate": r4(fired / n) if n else None,
            "docs_wilson95": [r4(w[0]), r4(w[1])],
            "kwords": round(kwords, 1), "occurrences": occ,
            "per_1k": r4(occ / kwords) if kwords else None,
            "per_1k_ci95": [r4(ci[0]), r4(ci[1])],
            "background": ru,
            "verdict": verdict,
            "min_detectable_per_1k": mdr,
            "min_detectable_ratio": (round(mdr / ru["per_1k"], 1)
                                     if mdr and ru.get("per_1k") else None),
            "detections": dict(dets.most_common()),
            "top_detection": {"id": top[0], "share": r4(top[1] / occ)} if top else None,
            "one_cue": one_cue,
        }
    return rows


def person_table(docs, lenses, rul):
    out = {}
    for pid in sorted({d["person_id"] for d in docs}):
        mine = [d for d in docs if d["person_id"] == pid]
        tab = lens_table(mine, lenses, rul)
        out[pid] = {
            "texts": len(mine), "words": sum(d["words"] for d in mine),
            "date_range": [min((d["date"] for d in mine if d.get("date")), default=None),
                           max((d["date"] for d in mine if d.get("date")), default=None)],
            "lenses": {lid: {k: v for k, v in row.items()
                             if k in ("docs_fired", "occurrences", "per_1k", "per_1k_ci95",
                                      "verdict", "detections", "min_detectable_ratio")}
                       for lid, row in tab.items()},
        }
    return out


def institution_table(docs, lenses, rul, people):
    adj = affiliations()
    with_texts = {d["person_id"] for d in docs}
    out = {}
    for label, iid in sorted(board_institutions().items()):
        if not iid:
            out[label] = {"id": None, "collateral": "none on hand",
                          "why": "not a graph institution; no affiliated persons to read"}
            continue
        ppl = sorted(p for p in adj.get(iid, ()) if p in with_texts)
        if not ppl:
            out[label] = {"id": iid, "collateral": "none on hand",
                          "why": "no affiliated person in the graph has texts in the store"}
            continue
        mine = [d for d in docs if d["person_id"] in ppl]
        tab = lens_table(mine, lenses, rul)
        out[label] = {
            "id": iid, "collateral": "affiliated persons' words",
            "persons": [{"id": p, "label": (people.get(p) or {}).get("label", p),
                         "texts": sum(1 for d in mine if d["person_id"] == p)} for p in ppl],
            "texts": len(mine), "words": sum(d["words"] for d in mine),
            "lenses": {lid: {k: v for k, v in row.items()
                             if k in ("docs_fired", "occurrences", "per_1k", "per_1k_ci95",
                                      "verdict", "detections")}
                       for lid, row in tab.items() if row["occurrences"]},
            "caveat": "These are the words of people the graph affiliates with the institution, "
                      "graded for what the texts exhibit. Not the institution's output, not a "
                      "finding about anyone's motives.",
        }
    return out


def scanner_table(scan, docs):
    if scan is None:
        return None
    by_id = {d["id"]: d for d in docs}
    bands = Counter(m["band"] for m in scan)
    per_person = {}
    for pid in sorted({m["person_id"] for m in scan}):
        mine = [m for m in scan if m["person_id"] == pid]
        words = sum(m["words"] for m in mine) or 1
        asserted = sum(m["counts"]["judg-asserted"] for m in mine)
        attrib = sum(m["counts"]["judg-attrib"] for m in mine)
        voice = sum(m["counts"]["voice-strip"] for m in mine)
        scored = [m["degree"] for m in mine if m.get("degree") is not None]
        per_person[pid] = {
            "texts": len(mine), "words": words,
            "asserted": asserted, "attributed": attrib, "decorative_emphasis": voice,
            "asserted_per_1k": r4(1000.0 * asserted / words),
            "declared_pct": (round(100.0 * attrib / (attrib + asserted)) if (attrib + asserted) else None),
            "bands": dict(Counter(m["band"] for m in mine)),
            # None when every text sits under the scanner's words floor: no degree was scored.
            "max_degree": max(scored) if scored else None,
            "scored_texts": len(scored),
        }
    # `min_words` is the scanner's own floor, read back from the shipped script; a text under it
    # gets counts but no degree (band "Short"). Before the floor existed every 15-word tweet
    # with one loaded word scored 100/100 -- the first run's whole High band.
    return {"texts": len(scan), "bands": dict(bands),
            "min_words": next((m.get("minWords") for m in scan if m.get("minWords") is not None), None),
            "scored_texts": sum(1 for m in scan if m.get("degree") is not None),
            "asserted_total": sum(m["counts"]["judg-asserted"] for m in scan),
            "attributed_total": sum(m["counts"]["judg-attrib"] for m in scan),
            "per_person": per_person,
            "high_band_texts": sorted([{"id": m["id"], "person_id": m["person_id"], "degree": m["degree"],
                                        "words": m["words"], "url": by_id[m["id"]].get("url")}
                                       for m in scan if m["band"] == "High"],
                                      key=lambda x: (-x["degree"], x["id"]))}


FROZEN = os.path.join(HERE, "collateral-sample-frozen.json")


def span_key(person_id, text_id, lens, s):
    return f"{person_id}|{text_id}|{lens}|{s['detection']}|{s['start']}|{s['end']}"


def precision_sample(docs, texts_by_id, frozen=FROZEN):
    """A fixed-seed sample of fired spans for the hand-read, plus EVERY span from lenses that
    fired <= RARE_LENS_MAX times (a rare lens's three hits are the whole story). Written into
    the JSON so the reading is checkable; the verdicts live beside it in the hand-read files.

    FROZEN AFTER THE FIRST RUN. The first run writes the sampled span keys to
    collateral-sample-frozen.json; every later run reads that file and reports the SAME spans,
    marking which survive the current taxonomy and which no longer fire. A cue repair that
    re-drew the sample would compare two different sets of spans and call the difference an
    improvement; on a frozen set the before/after is the same 51 spans read once by two
    readers. Spans the current taxonomy fires that are not in the frozen set -- the pool's
    unsampled remainder plus anything a taxonomy change added -- are counted (`unsampled_new`)
    and not read here. Delete the frozen file to re-draw, deliberately."""
    hits = []
    per_lens = Counter()
    for d in docs:
        for lid, r in d["lenses"].items():
            for s in r["spans"]:
                hits.append((d["person_id"], d["id"], lid, s))
                per_lens[lid] += 1
    hits.sort(key=lambda h: (h[0], h[1], h[2], h[3]["start"] or 0, h[3]["detection"]))
    by_key = {span_key(h[0], h[1], h[2], h[3]): h for h in hits}

    def ctx(h):
        t = texts_by_id[h[1]]["text"]
        a, b = h[3]["start"] or 0, h[3]["end"] or 0
        return (("…" if a > CONTEXT else "") + t[max(0, a - CONTEXT):a] + "[[" + t[a:b] + "]]" +
                t[b:b + CONTEXT] + ("…" if b + CONTEXT < len(t) else ""))

    def row(n, h, how, key):
        return {"n": n, "how": how, "key": key, "person_id": h[0], "text_id": h[1],
                "url": texts_by_id[h[1]].get("url"), "lens": h[2],
                "detection": h[3]["detection"], "cue": h[3]["cue"], "span": h[3]["span"],
                "context": ctx(h), "fires_now": True}

    if frozen and os.path.exists(frozen):
        F = json.load(open(frozen, encoding="utf-8"))
        rows, dropped = [], []
        for fr in F["rows"]:
            h = by_key.get(fr["key"])
            if h is None:
                dropped.append({**fr, "fires_now": False})
            else:
                rows.append(row(fr["n"], h, fr["how"], fr["key"]))
        frozen_keys = {fr["key"] for fr in F["rows"]}
        new = [k for k in by_key if k not in frozen_keys]
        return {"seed": F["seed"], "sample_n": F["sample_n"], "pool": F["pool"],
                "rare_lens_hits": F["rare_lens_hits"], "frozen_at": F["frozen_at"],
                "frozen_n": len(F["rows"]), "surviving": len(rows), "dropped": dropped,
                "unsampled_new": len(new), "rows": rows}

    rare = [h for h in hits if per_lens[h[2]] <= RARE_LENS_MAX]
    pool = [h for h in hits if per_lens[h[2]] > RARE_LENS_MAX]
    rng = random.Random(SEED)
    picked = rng.sample(pool, min(SAMPLE_N, len(pool))) if pool else []
    picked.sort(key=lambda h: (h[0], h[1], h[2], h[3]["start"] or 0))
    rows = [row(i + 1, h, "sampled", span_key(h[0], h[1], h[2], h[3])) for i, h in enumerate(picked)]
    rows += [row(len(rows) + i + 1, h, "rare-lens: every hit read", span_key(h[0], h[1], h[2], h[3]))
             for i, h in enumerate(rare)]
    if frozen:
        with open(frozen, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"frozen_at": "2026-09-07 (first run; sha of texts.jsonl " + sha(TEXTS) + ")",
                       "seed": SEED, "sample_n": SAMPLE_N, "pool": len(pool),
                       "rare_lens_hits": len(rare),
                       "rows": [{"n": r["n"], "how": r["how"], "key": r["key"]} for r in rows]},
                      fh, indent=1)
        # Same output whether the frozen file existed before this run or was just written --
        # otherwise the writing run and the --check run disagree on their own bookkeeping.
        return precision_sample(docs, texts_by_id, frozen)
    return {"seed": SEED, "sample_n": SAMPLE_N, "pool": len(pool), "rare_lens_hits": len(rare),
            "frozen_at": "unfrozen", "frozen_n": len(rows), "surviving": len(rows), "dropped": [],
            "unsampled_new": 0, "rows": rows}


def receipts_comparison(docs, texts):
    """The 24 receipts in receipts.jsonl are earlier model-read detections on these same
    texts. Does the cue arm fire the same lens on the same text? Does any cue land inside
    the receipt's span? Two questions, two counts."""
    recs = jsonl(RECEIPTS)
    by_url = defaultdict(list)
    for t in texts:
        by_url[(t["person_id"], t.get("url"))].append(t)
    by_id = {d["id"]: d for d in docs}
    rows, same_lens, overlap, located = [], 0, 0, 0
    for rc in recs:
        cands = by_url.get((rc.get("person_id"), rc.get("url"))) or \
            [t for t in texts if t["person_id"] == rc.get("person_id") and (rc.get("span") or "") in t["text"]]
        t = next((c for c in cands if (rc.get("span") or "") in c["text"]), cands[0] if cands else None)
        if t is None:
            rows.append({"person_id": rc.get("person_id"), "lens": rc.get("lens"),
                         "detection": rc.get("detection_id"), "text": None, "cue_same_lens": None,
                         "cue_in_span": None})
            continue
        located += 1
        d = by_id[t["id"]]
        lens_hits = (d["lenses"].get(rc.get("lens")) or {}).get("spans") or []
        pos = t["text"].find(rc.get("span") or "\x00")
        inside = False
        if pos >= 0:
            a, b = pos, pos + len(rc["span"])
            inside = any((s["start"] or 0) < b and (s["end"] or 0) > a for s in lens_hits)
        same_lens += bool(lens_hits)
        overlap += inside
        rows.append({"person_id": rc.get("person_id"), "lens": rc.get("lens"),
                     "detection": rc.get("detection_id"), "text": t["id"],
                     "cue_same_lens": bool(lens_hits), "cue_in_span": inside if pos >= 0 else None})
    return {"receipts": len(recs), "located": located, "cue_fired_same_lens": same_lens,
            "cue_inside_receipt_span": overlap, "rows": rows}


# ── assembly ──────────────────────────────────────────────────────────────────

def build():
    lenses = {lid: tax for lid, tax in load_lenses(DETECTORS).items() if lid not in GRAPH_LENSES}
    texts, people = load_collateral()
    texts_by_id = {t["id"]: t for t in texts}
    rul = rulers()
    docs = run_tradecraft(texts, lenses)
    scan = run_scanner(texts)
    words = sum(d["words"] for d in docs)
    return {
        "meta": {
            "prereg": PREREG,
            "collateral": {"file": os.path.relpath(TEXTS, SERIES).replace(os.sep, "/"),
                           "sha256_16": sha(TEXTS), "texts": len(texts),
                           "persons": len({t["person_id"] for t in texts}), "words": words,
                           "median_words": sorted(d["words"] for d in docs)[len(docs) // 2] if docs else None,
                           "date_range": [min((t.get("date") for t in texts if t.get("date")), default=None),
                                          max((t.get("date") for t in texts if t.get("date")), default=None)],
                           "what": "verbatim public statements attributed to dataset persons; "
                                   "not the author's manuscripts, not the PTC benchmark"},
            "taxonomy_sha256_16": taxonomy_hash(),
            "text_lenses": sorted(lenses),
            "excluded_lenses": sorted(GRAPH_LENSES),
            "detectors": {
                "tradecraft_cues": "ran: deterministic cue matcher, shipped taxonomy, every text lens",
                "capture_scanner": ("ran: shipped scanner.js + capture-cats.js via node" if scan is not None
                                    else "NOT RUN: node or the shipped scanner files unavailable"),
                "instrument_engine_js": "same taxonomy and grader as tradecraft_cues; parity-gated "
                                        "(tools/test_engine_parity.py) -- not a second measurement",
                "tradecraft_llm_find_stage": "NOT RUN: local 14B held by the detached Phase-1.2 "
                                             "measurement; 37% span fabrication unresolved",
                "bias_study": "not applicable: measures models, reads no third-party text",
                "ratchet_series": "not applicable: reads a series of administrative actions",
            },
            "scanner_sha256_16": {"scanner.js": sha(SCANNER) if os.path.exists(SCANNER) else None,
                                  "capture-cats.js": sha(CATS) if os.path.exists(CATS) else None},
            "seed": SEED,
        },
        "lenses": lens_table(docs, lenses, rul),
        "persons": person_table(docs, lenses, rul),
        "institutions": institution_table(docs, lenses, rul, people),
        "scanner": scanner_table(scan, docs),
        "precision_sample": precision_sample(docs, texts_by_id),
        "receipts": receipts_comparison(docs, texts),
    }


def render_md(R):
    m, L = R["meta"], R["lenses"]
    c = m["collateral"]
    out = [f"## Collateral: {c['texts']} texts / {c['persons']} persons / {c['words']:,} words "
           f"(median {c['median_words']} words; {c['date_range'][0]} to {c['date_range'][1]}); "
           f"texts.jsonl `{c['sha256_16']}`, taxonomy `{m['taxonomy_sha256_16']}`", "",
           "| lens | state | docs fired / n | docs Wilson95 | bg docs rate | occ | per 1k [95%] | bg per 1k [95%] | verdict | top detection (share) | one cue? | detectable at |",
           "|---|---|---:|---|---:|---:|---|---|---|---|---|---|"]
    for lid, r in L.items():
        bg = r["background"]
        top = r["top_detection"]
        out.append(
            f"| `{lid}` | {r['state']} | {r['docs_fired']}/{r['docs_n']} | "
            f"[{r['docs_wilson95'][0]}, {r['docs_wilson95'][1]}] | {bg.get('docs_rate')} | "
            f"{r['occurrences']} | {r['per_1k']} [{r['per_1k_ci95'][0]}, {r['per_1k_ci95'][1]}] | "
            f"{bg.get('per_1k')} [{(bg.get('per_1k_ci95') or ['?','?'])[0]}, {(bg.get('per_1k_ci95') or ['?','?'])[1]}] | "
            f"**{r['verdict']}** | {(top['id'] + ' (' + str(top['share']) + ')') if top else '—'} | "
            f"{'YES' if r['one_cue'] else 'no'} | "
            f"{(str(r['min_detectable_ratio']) + 'x bg') if r['min_detectable_ratio'] else '—'} |")
    out += ["", "## Per person (occurrences per 1,000 words; lenses that fired)", "",
            "| person | texts | words | lenses fired (occ, per 1k) |", "|---|---:|---:|---|"]
    for pid, p in R["persons"].items():
        fired = [f"`{lid}` {v['occurrences']} ({v['per_1k']})" for lid, v in p["lenses"].items() if v["occurrences"]]
        out.append(f"| {pid} | {p['texts']} | {p['words']:,} | {', '.join(fired) or '— none —'} |")
    out += ["", "## Board institutions", ""]
    have = {k: v for k, v in R["institutions"].items() if v.get("texts")}
    none = [k for k, v in R["institutions"].items() if not v.get("texts")]
    for k, v in have.items():
        ppl = ", ".join(f"{p['label']} ({p['texts']})" for p in v["persons"])
        fired = [f"`{lid}` {r['occurrences']} ({r['per_1k']}, {r['verdict']})" for lid, r in v["lenses"].items()]
        out.append(f"- **{k}** (`{v['id']}`): {v['texts']} texts / {v['words']:,} words by {ppl}. "
                   f"Fired: {', '.join(fired) or 'nothing'}.")
    out.append(f"- **No collateral on hand: {len(none)} of {len(R['institutions'])}** board institutions.")
    S = R["scanner"]
    if S:
        out += ["", f"## Capture scanner: {S['texts']} texts, bands {S['bands']}, "
                    f"asserted {S['asserted_total']} / attributed {S['attributed_total']}", "",
                "| person | texts | words | asserted | attributed | declared % | asserted per 1k | max degree |",
                "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for pid, p in S["per_person"].items():
            out.append(f"| {pid} | {p['texts']} | {p['words']:,} | {p['asserted']} | {p['attributed']} | "
                       f"{p['declared_pct'] if p['declared_pct'] is not None else '—'} | "
                       f"{p['asserted_per_1k']} | {p['max_degree']} |")
    rc = R["receipts"]
    out += ["", f"## Receipts comparison: {rc['receipts']} model-read receipts, {rc['located']} located in the "
                f"store, cue arm fired the same lens on the same text {rc['cue_fired_same_lens']}, "
                f"a cue lands inside the receipt's span {rc['cue_inside_receipt_span']}"]
    ps = R["precision_sample"]
    out += ["", f"## Hand-read sample: {len(ps['rows'])} spans ({ps['sample_n']} sampled from a pool of "
                f"{ps['pool']} with seed {ps['seed']}, plus {ps['rare_lens_hits']} rare-lens hits read in full)"]
    return "\n".join(out)


def _drift_paths(fresh, stored, path="", out=None, limit=25):
    """Yield (dotted-path, fresh, stored) for the leaves that differ. Bounded, sorted.

    Deliberately reports LEAVES rather than the first differing branch: a top-level "scanner
    differs" tells a reader nothing about whether the cause is one band count or the whole
    detector, and that distinction is the difference between a stale artifact and a broken
    environment.
    """
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if isinstance(fresh, dict) and isinstance(stored, dict):
        for k in sorted(set(fresh) | set(stored)):
            if k not in fresh:
                out.append((path + k, "<absent>", stored[k]))
            elif k not in stored:
                out.append((path + k, fresh[k], "<absent>"))
            else:
                _drift_paths(fresh[k], stored[k], path + k + ".", out, limit)
            if len(out) >= limit:
                break
    elif isinstance(fresh, list) and isinstance(stored, list):
        if len(fresh) != len(stored):
            out.append((path + "[]", "len %d" % len(fresh), "len %d" % len(stored)))
        else:
            for i, (a, b) in enumerate(zip(fresh, stored)):
                if a != b:
                    _drift_paths(a, b, path + "[%d]." % i, out, limit)
                if len(out) >= limit:
                    break
    elif fresh != stored:
        out.append((path.rstrip("."), fresh, stored))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    R = build()
    if a.check:
        if not os.path.exists(OUT):
            print(f"DRIFT: {os.path.relpath(OUT, SERIES)} missing", file=sys.stderr)
            return 1
        have = json.load(open(OUT, encoding="utf-8"))
        if R["scanner"] is None and have.get("scanner") is not None:
            # Do not pass a half-verified file quietly, and do not fail a tree for lacking node.
            R["scanner"] = have["scanner"]
            R["meta"]["detectors"]["capture_scanner"] = have["meta"]["detectors"]["capture_scanner"]
            if json.loads(json.dumps(R, sort_keys=True)) == have:
                print("node missing: tradecraft half verified, scanner half NOT verified", file=sys.stderr)
                return 2
        if json.loads(json.dumps(R, sort_keys=True)) != have:
            # NAME THE KEYS. This printed "differs from a fresh run" and nothing else, which
            # made it unfixable from CI: the job failed for hours, blocking the Pages deploy
            # behind it, while the same --check passed on the developer's machine. A gate has
            # to print WHAT drifted or it is only an alarm.
            for path, mine, theirs in _drift_paths(json.loads(json.dumps(R, sort_keys=True)), have):
                print(f"  DRIFT {path}: fresh={mine!r} stored={theirs!r}"[:300], file=sys.stderr)
            print(f"DRIFT: {os.path.relpath(OUT, SERIES)} differs from a fresh run", file=sys.stderr)
            return 1
        return 0
    if a.json:
        print(json.dumps(R, indent=1, sort_keys=True, ensure_ascii=False))
        return 0
    if a.markdown:
        print(render_md(R))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(R, fh, indent=1, sort_keys=True, ensure_ascii=False)
    print(f"wrote {os.path.relpath(OUT, SERIES)}")
    print(render_md(R))
    return 0


if __name__ == "__main__":
    sys.exit(main())
