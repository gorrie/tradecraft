#!/usr/bin/env python3
"""Measure a proposed CUE REPAIR before and after it is applied -- the discipline for editing the taxonomy.

WHY A TOOL AND NOT AN EDIT
--------------------------
The collateral evaluation (RESULTS-2026-09-07-collateral-eval.md) read 51 fired spans and found
the construct behind 10. The other 41 were mostly one shape: a cue written for one register
firing in another -- `existential` (a research field's name), `training pipeline` (ML jargon),
`high score` (a benchmark), `you haven` (a prefix of "haven't"). The temptation is to delete
them. Deleting a cue because one corpus dislikes it is how a detector is tuned to its last
complaint, so a cue leaves only through a rule fixed in advance and measured on the corpora the
detector is calibrated against, with what it would cost stated first:

    PTC          the cue's own in-span precision and lift against the corpus chance rate
                 (ptc_precision.py's statistic, per cue instead of per lens)
    PTC-bg       occurrences in the 1.81M chars of PTC news six annotators declined to mark
                 (the CUT-CANDIDATES-2026-08-26 criterion)
    background   occurrences per 1,000 words in the general-prose pool (occurrence_rate.py)
    fixtures     every positive fixture of the lens re-run with the cue removed: does it still
                 fire, does it still show an expected marker
    census       the cue's DETECTION on PTC with and without the cue: does a demonstrated
                 detection (>= JUDGEABLE_HITS locatable hits, lift lower bound > 1) stay demonstrated
    collateral   the cue's occurrences on texts.jsonl and the hand-read classes of its read spans

A cue is CUT only when the pre-registered rule says so from those numbers, and `--apply` removes
exactly the cues the rule selected -- never a cue the rule kept, never by hand. The RESULTS
file records both tables. A cue the rule keeps because removing it would demote a demonstrated
detection or break a fixture is reported as kept, with the number that kept it.

THE MATCHER RULE
----------------
`you haven` matched inside "you haven't" because the apostrophe is not a word character, so the
bounded matcher saw a word boundary. A boundary inside a contraction is not a boundary. The
repair is a matcher rule (detect.py + engine.js, parity-gated): a match whose end is followed by
an apostrophe and a letter is rejected unless the tail is an accepted suffix ('s). `--boundary`
measures how many matches that rule removes on every corpus, across ALL cues, so its blast
radius is a number and not a guess.

    python eval/cue_repair_eval.py --plan CUE-REPAIR-2026-09-07.json            # measure, print verdicts
    python eval/cue_repair_eval.py --plan CUE-REPAIR-2026-09-07.json --json out.json
    python eval/cue_repair_eval.py --plan CUE-REPAIR-2026-09-07.json --apply    # remove the CUT cues from the YAML
    python eval/cue_repair_eval.py --boundary                                   # the contraction rule's blast radius
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SERIES = os.path.dirname(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft import detect as D  # noqa: E402
from tradecraft.grader import grade_document_for_lens  # noqa: E402
import ptc_precision as P  # noqa: E402
import detection_census as DC  # noqa: E402
import occurrence_rate as OR  # noqa: E402
from background_rate import tokens, wilson  # noqa: E402

DETECTORS = os.path.join(REPO, "detectors")
FIXTURES = os.path.join(HERE, "fixtures.json")
PTC_BG = os.path.join(HERE, "ptc-background", "bg_ptc_unannotated.txt")
TEXTS = os.path.join(SERIES, "research", "ratchet-mcp", "server", "data", "texts.jsonl")
COLLATERAL = os.path.join(HERE, "collateral-eval.json")
HAND_A = os.path.join(HERE, "collateral-eval-hand-read.json")
HAND_B = os.path.join(HERE, "collateral-eval-hand-read-B.json")


def jsonl(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def occurrences(cue, text):
    return D._find_all_bounded(cue.strip(), text)


# ── the corpora, loaded once ──────────────────────────────────────────────────

class Corpora:
    def __init__(self):
        self.ptc = P.load_corpus()                       # [{id, text, spans}]
        self.ptc_chars = sum(len(a["text"]) for a in self.ptc)
        self.ptc_annot = sum(sum(b - a for a, b in art["spans"]) for art in self.ptc)
        self.chance = self.ptc_annot / self.ptc_chars if self.ptc_chars else 0.0
        with open(PTC_BG, encoding="utf-8", errors="replace") as fh:
            self.ptc_bg = fh.read()
        # occurrence_rate.background_docs() yields (Document, role-record) pairs; the rate's
        # denominator is exactly these documents, so the tool measures on the same pool.
        self.bg_docs = [{"text": d.text, "origin": d.origin} for d, _rec in OR.background_docs()]
        self.bg_kwords = sum(tokens(d["text"]) for d in self.bg_docs) / 1000.0
        self.fixtures = json.load(open(FIXTURES, encoding="utf-8"))
        self.texts = jsonl(TEXTS) if os.path.exists(TEXTS) else []


def cue_on_ptc(cue, C):
    hits = inspan = 0
    for art in C.ptc:
        for lo, hi in occurrences(cue, art["text"]):
            hits += 1
            if P.covered(art["spans"], lo, hi):
                inspan += 1
    prec = inspan / hits if hits else None
    lo, hi = wilson(inspan, hits) if hits else (None, None)
    return {"hits": hits, "in_span": inspan, "precision": None if prec is None else round(prec, 3),
            "lift": None if prec is None or not C.chance else round(prec / C.chance, 2),
            "lift_ci95": None if lo is None or not C.chance else [round(lo / C.chance, 2), round(hi / C.chance, 2)]}


def detection_on_ptc(taxonomy, det_id, C):
    """Detection-level hits / in-span / lift on PTC for one taxonomy state -- the census's
    statistic, so 'demonstrated' means what it means there."""
    hits = inspan = 0
    for art in C.ptc:
        for h in D.detect_cues(art["text"], taxonomy):
            if h.detection_id != det_id:
                continue
            hits += 1
            if P.covered(art["spans"], h.char_start, h.char_end):
                inspan += 1
    lo, hi = wilson(inspan, hits) if hits else (0.0, 1.0)
    lift_lo = lo / C.chance if C.chance else None
    return {"hits": hits, "in_span": inspan,
            "lift": round(inspan / hits / C.chance, 2) if hits and C.chance else None,
            "lift_ci95": [round(lo / C.chance, 2), round(hi / C.chance, 2)] if C.chance else None,
            "demonstrated": bool(hits >= DC.JUDGEABLE_HITS and lift_lo is not None and lift_lo > 1.0)}


def with_change(taxonomy, cand):
    """The taxonomy AFTER one candidate change, in memory. Three actions:
    cut      -- remove the cue
    exclude  -- keep the cue, add match-local `excludes` phrases to its detection
    replace  -- remove the cue, add the gold-attested narrower cue(s)"""
    # The schema's dataclasses are frozen (a taxonomy is not mutated after load, by design), so
    # the after-state is rebuilt with dataclasses.replace at each level rather than assigned.
    from dataclasses import replace as _replace

    def new_det(d):
        if d.id != cand["detection"]:
            return d
        cues = list(d.cues)
        excludes = list(getattr(d, "excludes", None) or [])
        if cand["action"] in ("cut", "replace"):
            cues = [c for c in cues if c.strip().lower() != cand["cue"].strip().lower()]
        if cand["action"] == "replace":
            cues += [c for c in cand["add"] if c.lower() not in {x.strip().lower() for x in cues}]
        if cand["action"] == "exclude":
            excludes += list(cand["excludes"])
        return _replace(d, cues=cues, excludes=excludes)

    return _replace(taxonomy, markers=[_replace(m, detections=[new_det(d) for d in m.detections])
                                       for m in taxonomy.markers])


def gold_text(det):
    return " ".join((g.get("text") or "") for g in (getattr(det, "gold", None) or [])).lower()


def cp_spans_suppressed(cand, C):
    """For an `exclude` candidate: would the exclusion silence a span a reader marked CP?
    Checked on the collateral texts themselves (the exclusion window is EXCLUDE_WINDOW chars)."""
    if not os.path.exists(COLLATERAL) or not os.path.exists(HAND_A):
        return []
    col = json.load(open(COLLATERAL, encoding="utf-8"))
    A = {v["n"]: v["class"] for v in json.load(open(HAND_A, encoding="utf-8")).get("verdicts", [])}
    B = {v["n"]: v["class"] for v in json.load(open(HAND_B, encoding="utf-8")).get("verdicts", [])} if os.path.exists(HAND_B) else {}
    texts = {t.get("id"): t for t in C.texts}
    hit = []
    for r in col["precision_sample"]["rows"]:
        if r["lens"] != cand["lens"] or r["cue"].strip("'\"").lower() != cand["cue"].lower():
            continue
        if A.get(r["n"]) != "CP" and B.get(r["n"]) != "CP":
            continue
        t = texts.get(r["text_id"])
        if not t:
            continue
        pos = t["text"].find(r["span"])
        win = t["text"][max(0, pos - D.EXCLUDE_WINDOW):pos + len(r["span"]) + D.EXCLUDE_WINDOW].lower()
        if any(x.lower() in win for x in cand["excludes"]):
            hit.append(r["n"])
    return hit


def fixtures_after(lens_id, taxonomy, taxonomy_after, C):
    """Positive fixtures of this lens: fires before / after, expected marker kept / lost."""
    broke = []
    for fx in C.fixtures:
        if fx.get("lens") != lens_id or not fx.get("should_fire"):
            continue
        before = grade_document_for_lens(taxonomy, D.detect_cues(fx["text"], taxonomy), tokens(fx["text"]))
        after = grade_document_for_lens(taxonomy_after, D.detect_cues(fx["text"], taxonomy_after), tokens(fx["text"]))
        fired_b, fired_a = before.index > 0, after.index > 0
        exp = fx.get("expect_any") or []
        exp_b = (not exp) or any(m in before.markers_present for m in exp)
        exp_a = (not exp) or any(m in after.markers_present for m in exp)
        if (fired_b and not fired_a) or (exp_b and not exp_a):
            broke.append({"fixture": fx["id"], "fired_before": fired_b, "fired_after": fired_a,
                          "expected_marker_before": exp_b, "expected_marker_after": exp_a})
    return broke


def collateral_for(cue, lens_id):
    """The cue's occurrences on texts.jsonl (a direct scan) and the hand-read classes of the
    frozen-sample spans that carry it, by both readers."""
    out = {"occurrences": 0, "read": {}}
    if not os.path.exists(COLLATERAL):
        return out
    C = json.load(open(COLLATERAL, encoding="utf-8"))
    out["occurrences"] = sum(len(occurrences(cue, t["text"])) for t in (jsonl(TEXTS) if os.path.exists(TEXTS) else []))
    A = {v["n"]: v["class"] for v in (json.load(open(HAND_A, encoding="utf-8")).get("verdicts", []) if os.path.exists(HAND_A) else [])}
    B = {v["n"]: v["class"] for v in (json.load(open(HAND_B, encoding="utf-8")).get("verdicts", []) if os.path.exists(HAND_B) else [])}
    read = Counter()
    for r in C["precision_sample"]["rows"]:
        if r["lens"] == lens_id and r["cue"].strip("'\"").lower() == cue.strip().lower():
            read[A.get(r["n"], "?")] += 1
            if B:
                read["B:" + B.get(r["n"], "?")] += 1
    out["read"] = dict(read)
    return out


def measure_plan(plan, C):
    lenses = load_lenses(DETECTORS)
    rule = plan["rule"]
    rows = []
    for cand in plan["candidates"]:
        lid, det_id, cue = cand["lens"], cand["detection"], cand["cue"]
        cand.setdefault("action", "cut")
        tax = lenses[lid]
        det = next(d for m in tax.markers for d in m.detections if d.id == det_id)
        assert any(c.strip().lower() == cue.lower() for c in det.cues), f"{cue!r} not in {lid}/{det_id}"
        tax_after = with_change(tax, cand)
        ptc = cue_on_ptc(cue, C)
        bg_ptc = len(occurrences(cue, C.ptc_bg))
        bg_occ = sum(len(occurrences(cue, d["text"])) for d in C.bg_docs)
        det_before = detection_on_ptc(tax, det_id, C)
        det_after = detection_on_ptc(tax_after, det_id, C)
        broke = fixtures_after(lid, tax, tax_after, C)
        col = collateral_for(cue, lid)
        read_a = {k: v for k, v in col["read"].items() if not k.startswith("B:")}
        read_b = {k[2:]: v for k, v in col["read"].items() if k.startswith("B:")}
        n_read = sum(read_a.values())
        cp_read = max(read_a.get("CP", 0), read_b.get("CP", 0))      # EITHER reader: the recall-protecting direction
        # ── the pre-registered rule, applied mechanically ────────────────────
        reasons = []
        extra = {}
        if broke:
            reasons.append(f"KEEP: breaks {len(broke)} positive fixture(s): " + ", ".join(b["fixture"] for b in broke))
        if det_before["demonstrated"] and not det_after["demonstrated"]:
            reasons.append("KEEP: the change demotes a demonstrated detection")
        if cand["action"] in ("cut", "replace"):
            own_lift_ok = ptc["lift_ci95"] is not None and ptc["lift_ci95"][0] > 1.0
            if own_lift_ok:
                reasons.append(f"KEEP: its own PTC lift interval clears 1 ({ptc['lift_ci95']}) -- a working cue")
            if n_read and cp_read > 0:
                reasons.append(f"KEEP: {cp_read} of {n_read} read span(s) carried the construct (either reader)")
            benign = (bg_ptc >= rule["ptc_bg_min"]) or (bg_occ >= rule["bg_min_occurrences"]) or cand.get("defective")
            if not benign:
                reasons.append(f"KEEP: not shown benign-ubiquitous (PTC-bg {bg_ptc} < {rule['ptc_bg_min']}, "
                               f"background {bg_occ} < {rule['bg_min_occurrences']}) and not marked defective")
            if n_read == 0 and not cand.get("defective"):
                reasons.append("KEEP: no read span to judge the construct against")
            if cand["action"] == "replace":
                adds = {}
                for a_cue in cand["add"]:
                    a_ptc_bg = len(occurrences(a_cue, C.ptc_bg))
                    a_bg = sum(len(occurrences(a_cue, d["text"])) for d in C.bg_docs)
                    in_gold = a_cue.lower() in gold_text(det)
                    adds[a_cue] = {"in_gold": in_gold, "ptc_bg_occurrences": a_ptc_bg, "background_occurrences": a_bg}
                    if not in_gold:
                        reasons.append(f"KEEP: replacement `{a_cue}` is not in the detection's gold text")
                    if a_ptc_bg >= rule["ptc_bg_min"] or a_bg >= rule["bg_min_occurrences"]:
                        reasons.append(f"KEEP: replacement `{a_cue}` is itself benign-ubiquitous ({a_ptc_bg} / {a_bg})")
                extra["add"] = adds
        else:  # exclude
            n_pattern = sum(v for k, v in read_a.items() if k in ("CO", "QA"))
            if n_pattern < rule["exclude_min_read"]:
                reasons.append(f"KEEP: only {n_pattern} read cue-only/quoted span(s) attest the false-fire pattern "
                               f"(< {rule['exclude_min_read']})")
            silenced = cp_spans_suppressed(cand, C)
            extra["cp_spans_suppressed"] = silenced
            if silenced:
                reasons.append(f"KEEP: the exclusion would silence construct-present span(s) {silenced}")
        verdict = ("APPLY" if cand["action"] != "cut" else "CUT") if not reasons else "KEEP"
        if verdict != "KEEP":
            reasons.append({"cut": "CUT: every read span cue-only or quoted; no own PTC lift; benign-ubiquitous or defective; "
                                   "no fixture broken; no demonstrated detection demoted",
                            "replace": "REPLACE: the generic form fails the cut rule's guards and the gold-attested "
                                       "narrower form is not itself ubiquitous",
                            "exclude": "EXCLUDE: the false-fire pattern is attested in the read, silences no "
                                       "construct-present span, breaks nothing"}[cand["action"]]
                           + (" (defective: " + cand["defective"] + ")" if cand.get("defective") else ""))
        rows.append({"lens": lid, "detection": det_id, "cue": cue, "action": cand["action"],
                     "excludes": cand.get("excludes"), "add": cand.get("add"),
                     "verdict": verdict, "reasons": reasons,
                     "ptc": ptc, "ptc_bg_occurrences": bg_ptc,
                     "background_occurrences": bg_occ, "background_per_1k": round(bg_occ / C.bg_kwords, 4) if C.bg_kwords else None,
                     "detection_before": det_before, "detection_after": det_after,
                     "fixtures_broken": broke, "collateral": col, **extra,
                     "cues_left_in_detection": len([c for c in det.cues if c.strip().lower() != cue.lower()])})
    return rows


def apply_cuts(rows):
    """Write the CUT / APPLY verdicts into the taxonomy files by exact line, reload, verify.

    cut / replace: the cue's own `- cue` line inside its detection's cues list is removed;
    replace also inserts the added cue(s) right after the detection's `cues:` line.
    exclude: an `excludes:` block (or new items on an existing one) is inserted right after the
    detection's `- id:` line -- YAML mapping order is free, and this keeps the edit to lines
    that can be verified by reloading. Anything the rule KEPT is not touched."""
    by_lens = defaultdict(list)
    for r in rows:
        if r["verdict"] in ("CUT", "APPLY"):
            by_lens[r["lens"]].append(r)
    changed = []
    for lid, changes in by_lens.items():
        p = os.path.join(DETECTORS, lid, "taxonomy.yaml")
        with open(p, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        out, done = [], []
        det_now, indent = None, "    "
        for line in lines:
            m = re.match(r"^(\s*)-\s*id:\s*(\S+)\s*$", line)
            if m:
                det_now, indent = m.group(2), m.group(1) + "  "
                out.append(line)
                for c in changes:
                    if c["detection"] == det_now and c["action"] == "exclude":
                        # merge into an existing excludes block if the detection has one
                        has_block = any(re.match(r"^\s*excludes:\s*$", l) for l in _detection_block(lines, det_now))
                        if not has_block:
                            out.append(f"{indent}excludes:")
                            for x in c["excludes"]:
                                out.append(f"{indent}- {x}")
                            done.append(("exclude", det_now, tuple(c["excludes"])))
                continue
            if det_now and re.match(r"^\s*excludes:\s*$", line):
                out.append(line)
                for c in changes:
                    if c["detection"] == det_now and c["action"] == "exclude" and ("exclude", det_now, tuple(c["excludes"])) not in done:
                        for x in c["excludes"]:
                            out.append(f"{indent}- {x}")
                        done.append(("exclude", det_now, tuple(c["excludes"])))
                continue
            if det_now and re.match(r"^\s*cues:\s*$", line):
                out.append(line)
                for c in changes:
                    if c["detection"] == det_now and c["action"] == "replace":
                        for x in c["add"]:
                            out.append(f"{indent}- {x}")
                        done.append(("add", det_now, tuple(c["add"])))
                continue
            cm = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if det_now and cm and not line.strip().startswith("- id:"):
                cue = cm.group(1).strip().strip("'\"")
                dropped = False
                for c in changes:
                    if (c["detection"] == det_now and c["action"] in ("cut", "replace")
                            and cue.lower() == c["cue"].lower() and ("cut", det_now, cue.lower()) not in done):
                        done.append(("cut", det_now, cue.lower()))
                        dropped = True
                        break
                if dropped:
                    continue
            out.append(line)
        expected = sum(1 for c in changes if c["action"] in ("cut", "replace")) \
            + sum(1 for c in changes if c["action"] == "replace") \
            + sum(1 for c in changes if c["action"] == "exclude")
        if len(done) != expected:
            raise SystemExit(f"{lid}: applied {len(done)} of {expected} edits -- nothing written: {done}")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out))
        changed.append({"lens": lid, "file": os.path.relpath(p, REPO),
                        "edits": [{"action": c["action"], "detection": c["detection"], "cue": c["cue"],
                                   "add": c.get("add"), "excludes": c.get("excludes")} for c in changes]})
    # verify by reloading: cut cues gone, added cues present, exclusions present
    lenses = load_lenses(DETECTORS)
    for r in rows:
        if r["verdict"] == "KEEP":
            continue
        det = next(d for m in lenses[r["lens"]].markers for d in m.detections if d.id == r["detection"])
        live = {c.strip().lower() for c in det.cues}
        if r["action"] in ("cut", "replace"):
            assert r["cue"].lower() not in live, f"{r['cue']} still live"
        if r["action"] == "replace":
            assert all(a.lower() in live for a in r["add"]), f"{r['add']} not added"
        if r["action"] == "exclude":
            ex = {x.lower() for x in (getattr(det, "excludes", None) or [])}
            assert all(x.lower() in ex for x in r["excludes"]), f"{r['excludes']} not excluded"
    return changed


def _detection_block(lines, det_id):
    """The lines of one detection's mapping, from its `- id:` to the next `- id:` at the same depth."""
    out, on, depth = [], False, None
    for line in lines:
        m = re.match(r"^(\s*)-\s*id:\s*(\S+)\s*$", line)
        if m:
            if on and len(m.group(1)) <= depth:
                break
            if m.group(2) == det_id:
                on, depth = True, len(m.group(1))
                continue
        if on:
            out.append(line)
    return out


def boundary_blast_radius(C):
    """Every match, on every corpus and every cue, that the contraction rule rejects.

    Measured by running the bounded matcher with detect.CONTRACTION_GUARD off and on and
    diffing -- the guard is the only difference, so the diff IS the rule's blast radius. Each
    rejected match is recorded as (lens, cue, the text from the match to the next space) so a
    reader can see exactly what stopped matching."""
    lenses = load_lenses(DETECTORS)
    cues = sorted({(lid, c.strip()) for lid, t in lenses.items() for m in t.markers for d in m.detections for c in d.cues if c.strip()})
    corpora = {"ptc": [a["text"] for a in C.ptc], "background": [d["text"] for d in C.bg_docs],
               "fixtures": [f["text"] for f in C.fixtures], "collateral": [t["text"] for t in C.texts]}
    out = {}
    for name, docs in corpora.items():
        rejected, total = Counter(), 0
        for text in docs:
            for lid, cue in cues:
                D.CONTRACTION_GUARD = False
                before = set(D._find_all_bounded(cue, text))
                D.CONTRACTION_GUARD = True
                after = set(D._find_all_bounded(cue, text))
                total += len(after)
                for lo, hi in before - after:
                    tail = text[lo:min(len(text), hi + 6)].split(" ")[0]
                    rejected[f"{lid} `{cue}` -> {tail!r}"] += 1
        out[name] = {"matches_after": total, "rejected": sum(rejected.values()),
                     "rejected_detail": dict(rejected.most_common(40))}
    return out


def render(rows, C):
    L = [f"PTC: {len(C.ptc)} articles, chance {C.chance:.4f}; PTC-bg {len(C.ptc_bg):,} chars; "
         f"background {len(C.bg_docs)} docs / {C.bg_kwords:.1f} kwords", "",
         "| lens / detection | cue (action) | PTC hits / in-span | own lift [95%] | PTC-bg | bg occ (per 1k) | detection before -> after (demonstrated) | fixtures broken | collateral occ / read | verdict |",
         "|---|---|---:|---|---:|---:|---|---:|---|---|"]
    for r in rows:
        p, b, a = r["ptc"], r["detection_before"], r["detection_after"]
        act = r["action"] + (" " + ", ".join("`" + x + "`" for x in (r.get("excludes") or r.get("add") or [])) if r["action"] != "cut" else "")
        L.append(f"| `{r['lens']}` / {r['detection']} | `{r['cue']}` ({act}) | {p['hits']} / {p['in_span']} | "
                 f"{p['lift']} {p['lift_ci95'] or ''} | {r['ptc_bg_occurrences']} | {r['background_occurrences']} ({r['background_per_1k']}) | "
                 f"{b['hits']}/{b['in_span']} lift {b['lift']} ({'yes' if b['demonstrated'] else 'no'}) -> "
                 f"{a['hits']}/{a['in_span']} lift {a['lift']} ({'yes' if a['demonstrated'] else 'no'}) | "
                 f"{len(r['fixtures_broken'])} | {r['collateral']['occurrences']} / {r['collateral']['read']} | **{r['verdict']}** |")
    L.append("")
    for r in rows:
        L.append(f"- `{r['cue']}` ({r['lens']}/{r['detection']}): " + " · ".join(r["reasons"]))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", help="the pre-registered candidate list + rule (JSON)")
    ap.add_argument("--json", help="write the measured rows here")
    ap.add_argument("--apply", action="store_true", help="remove the CUT cues from the taxonomy files")
    ap.add_argument("--boundary", action="store_true", help="measure the contraction rule's blast radius")
    a = ap.parse_args(argv)
    C = Corpora()
    if a.boundary:
        if not hasattr(D, "CONTRACTION_GUARD"):
            raise SystemExit("detect.py has no CONTRACTION_GUARD -- the rule is not implemented")
        res = boundary_blast_radius(C)
        print(json.dumps(res, indent=1))
        if a.json:
            with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(res, fh, indent=1)
        return 0
    if not a.plan:
        ap.error("--plan is required")
    plan = json.load(open(a.plan, encoding="utf-8"))
    rows = measure_plan(plan, C)
    print(render(rows, C))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"plan": os.path.basename(a.plan), "chance": C.chance, "rows": rows}, fh, indent=1)
        print(f"\nwrote {a.json}")
    if a.apply:
        changed = apply_cuts(rows)
        print("\napplied:", json.dumps(changed, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
