#!/usr/bin/env python3
"""Export the detector to the browser WITHOUT hand-copying anything.

Why this exists
---------------
capture-scanner/scanner.js and receipt-collector/collector.js each hand-ported the
same wordlists into JS. They drifted, and on 2026-08-02 one copy was found carrying a
dead regex the other did not have -- an attribution detector that could never match
"characterized" or "accused". Any design where a human retypes a marker definition
into JavaScript will drift again.

So: this loads the taxonomies through the SAME `tradecraft.loader.load_lenses` the
Python detector uses, and emits them as data. `engine.js` ports only the two
deterministic FUNCTIONS -- cue matching and per-lens grading -- and carries zero
embedded vocabulary. Drift is then structurally impossible: there is one definition of
every marker, in YAML, and both runtimes read it.

Three gates back that up:
  1. this exporter is re-run in CI and the output must be identical (--check)
  2. the payload ships FIXTURES with their expected Python output; engine.js re-runs
     them in the browser on every page load and shows a loud banner if they disagree
  3. engine.js has no fallback wordlist. If the payload fails to load there is no
     silent degraded mode -- the page says so.

Also exported: the cut ledger (markers killed for firing on benign text, currently
buried in eval/RESULTS-*.md) and a precomputed self-audit of the author's own books.

    python tools/export_web.py           # write
    python tools/export_web.py --check   # exit 1 if the output is stale
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent                      # tradecraft/
SERIES = Path(os.environ.get("SERIES_ROOT") or REPO.parent)
OUT = SERIES / "website" / "static" / "tech" / "instrument"
BOOKS = SERIES.parent / "books"

sys.path.insert(0, str(REPO))
from tradecraft.loader import load_lenses            # noqa: E402
from tradecraft.detect import detect                 # noqa: E402
from tradecraft.grader import grade_document_for_lens  # noqa: E402

# Lenses whose markers cannot be judged by literal cue matching at all -- exported so the UI
# can grey them out and say why, rather than reporting a misleading 0.
#
# THIS WAS A HARDCODED SET AND IT COST US A GATE. On 2026-09-01 cue exclusions were added to
# detect.py and not to engine.js, and test_engine_parity stayed green: the only lens carrying
# an `excludes` entry was `legibility`, which was in this set, so no exported fixture exercised
# the feature. A capability recorded away from the lens decided what got tested. Each taxonomy
# now declares `cue_matching`, and this is derived from it.
def llm_only(lenses):
    return {lid for lid, tax in lenses.items() if not tax.cues_usable}


def taxonomies():
    lenses = load_lenses(str(REPO / "detectors"))
    out = {}
    for lid, tax in sorted(lenses.items()):
        cfg = tax.config
        out[lid] = {
            "id": tax.id, "name": tax.name,
            "description": (tax.description or "").strip(),
            "llm_only": not tax.cues_usable,
            "config": {
                "marker_present_threshold": cfg.marker_present_threshold,
                "w_breadth": cfg.w_breadth, "w_intensity": cfg.w_intensity,
                "w_density": cfg.w_density, "density_cap_per_1k": cfg.density_cap_per_1k,
                "tiers": cfg.tiers,
            },
            "markers": [{
                "id": m.id, "name": m.name, "base_weight": m.base_weight,
                "detections": [{
                    "id": d.id, "weight": d.weight,
                    "definition": (d.definition or "").strip(),
                    "cues": list(d.cues),
                    # Exported even when empty, so a browser engine that has the field can
                    # never silently disagree with Python about a suppressed firing. The
                    # parity gate could not have caught that on its own: no exported fixture
                    # exercised an exclusion, so parity passed over a genuine divergence.
                    "excludes": list(getattr(d, "excludes", []) or []),
                    "gold": [{"text": g.get("text"), "source": g.get("source")}
                             for g in (d.gold or [])],
                } for d in m.detections],
            } for m in tax.markers],
        }
    return out


# Two shapes appear across the RESULTS files and both matter:
#   marker verdicts  | lens / `marker` | **CUT** | evidence |
#   cue sweeps       | lens | `cue`, `cue`, ... | kept... | notes |
VERDICT_RE = re.compile(
    r"^\|\s*([^|]*?)\s*\|\s*\*\*(CUT|FIXED[^*]*)\*\*\s*\|\s*(.+?)\s*\|\s*$", re.M)


def cut_ledger():
    """Markers and cues killed for firing on benign text.

    This is the most credible material the project has and it is currently invisible
    to readers -- buried in eval prose. A detector that publishes what it got wrong is
    worth more than one that only publishes hits.
    """
    items, seen = [], set()
    for p in sorted((REPO / "eval").glob("RESULTS-*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        # 1. per-marker verdicts
        for m in VERDICT_RE.finditer(text):
            subject = re.sub(r"[`*]", "", m.group(1)).strip()
            key = ("marker", subject)
            if not subject or key in seen:
                continue
            seen.add(key)
            items.append({
                "kind": "marker", "subject": subject,
                "verdict": m.group(2).split()[0],
                "evidence": re.sub(r"\s+", " ", re.sub(r"[*]", "", m.group(3))).strip()[:600],
                "source": p.name,
            })
        # 2. cue-level sweeps: a table whose header declares a cut column
        for block in re.split(r"\n\s*\n", text):
            rows = [l.strip() for l in block.split("\n")
                    if l.strip().startswith("|") and not l.strip().startswith("|--")]
            if len(rows) < 2:
                continue
            head = [h.strip().lower() for h in rows[0].strip("|").split("|")]
            cut_col = next((i for i, h in enumerate(head) if h.startswith("cut")), None)
            if cut_col is None:
                continue
            for row in rows[1:]:
                cells = [c.strip() for c in row.strip("|").split("|")]
                if len(cells) <= cut_col:
                    continue
                cues = re.findall(r"`([^`]+)`", cells[cut_col])
                for cue in cues:
                    key = ("cue", cells[0], cue)
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append({
                        "kind": "cue", "subject": cue, "lens": re.sub(r"[`*]", "", cells[0]).strip(),
                        "verdict": "CUT",
                        "evidence": re.sub(r"\s+", " ", cells[-1])[:300],
                        "source": p.name,
                    })

    # A cue cannot be both cut and live. The ledger is scraped from historical RESULTS
    # prose, which is immutable by design -- so when a cut is REVERSED the old table still
    # says CUT and the Morgue goes on publishing a cue the detector is actively using.
    # That happened on 2026-08-26: four labels cut in the morning were restored in the
    # afternoon under a pre-registered test. Derive the correction instead of editing
    # history: anything still in the taxonomy is not in the morgue.
    live = set()
    for lid, tax in load_lenses(str(REPO / "detectors")).items():
        for m in tax.markers:
            for d in m.detections:
                for c in d.cues:
                    live.add((lid, c.strip().lower()))
    lens_ids = {lid for lid, _ in live}
    kept, revived = [], []
    for it in items:
        if it["kind"] == "cue":
            lens = (it.get("lens") or "").strip().lower()
            cue = it["subject"].strip().lower()
            # the ledger's lens cell is prose; match on any lens carrying the cue when it
            # does not name one cleanly, which is the conservative direction (do not
            # publish a cue as dead while some lens still fires it).
            if (lens, cue) in live or (lens not in lens_ids
                                       and any(c == cue for _, c in live)):
                revived.append(it["subject"])
                continue
        kept.append(it)
    if revived:
        print(f"  cut-ledger: {len(revived)} entr(ies) dropped -- back in the taxonomy: "
              f"{', '.join(sorted(set(revived))[:8])}", file=sys.stderr)
    return kept


def mechanism():
    """Engine-semantics fixtures on synthetic taxonomies, with Python's own answers.

    WHY THESE ARE NOT ORDINARY FIXTURES
    -----------------------------------
    Cue exclusions were added to detect.py and engine.js knew nothing about them -- and
    `test_engine_parity.py` PASSED. The only lens carrying an `excludes` entry was
    `legibility`, one of the five in LLM_ONLY, so no exported fixture exercised the feature.
    Parity was green over a divergence that would have had the browser firing on Executive
    Order 12988 boilerplate while Python did not.

    Word boundaries, suffix absorption and exclusion windows are properties of the ENGINE,
    not of any lens. Testing them through whichever real lens happens to be cues-capable both
    misplaces the check and leaves it hostage to the LLM_ONLY list. These carry their own
    two-detection taxonomy and assert detection ids directly.
    """
    from tradecraft.schema import Taxonomy, Marker, Detection, GradingConfig

    tax = Taxonomy(
        id="_mechanism", name="engine mechanism", description="synthetic",
        markers=[Marker(id="m", name="m", base_weight=1.0, detections=[
            Detection(id="plain", weight=1.0, definition="a bare cue",
                      cues=["needle"]),
            Detection(id="guarded", weight=1.0, definition="a cue with an exclusion",
                      cues=["eliminate ambiguity"],
                      excludes=["executive order 12988"]),
        ])],
        config=GradingConfig(),
    )
    tax_json = {
        "id": tax.id, "name": tax.name,
        "markers": [{"id": m.id, "name": m.name, "base_weight": m.base_weight,
                     "detections": [{"id": d.id, "weight": d.weight,
                                     "definition": d.definition,
                                     "cues": list(d.cues),
                                     "excludes": list(d.excludes)}
                                    for d in m.detections]}
                    for m in tax.markers],
        "config": {"marker_present_threshold": tax.config.marker_present_threshold,
                   "w_breadth": tax.config.w_breadth,
                   "w_intensity": tax.config.w_intensity,
                   "w_density": tax.config.w_density,
                   "density_cap_per_1k": tax.config.density_cap_per_1k,
                   "tiers": list(tax.config.tiers or [])},
    }

    boiler = ("Executive Order 12988 (Civil Justice Reform): This rulemaking meets applicable "
              "standards to minimize litigation, eliminate ambiguity, and reduce burden.")
    real = ("The council argued the local patchwork was indefensible and that we must "
            "eliminate ambiguity between parishes.")
    cases = [
        ("mech_plain_fires", "a needle in the record", None),
        ("mech_boundary_refuses_midword", "the needlework was fine", None),
        ("mech_exclusion_suppresses", boiler, None),
        ("mech_exclusion_is_match_local", boiler + (" " * 260) + real, None),
        ("mech_exclusion_absent_still_fires", real, None),
        # Occurrence counting, added 2026-09-02 with the density repair. expect_detections is
        # a LIST, so three firings of one detection appear three times and a runtime that
        # reverts to first-match-only fails here. Both engines stopped at the first match
        # until this change, which is what made density an inverse-length term.
        ("mech_counts_every_occurrence",
         "a needle here, a needle there, and a third needle", None),
        ("mech_counts_across_cues_and_occurrences",
         "a needle and a needle, plus eliminate ambiguity twice: eliminate ambiguity", None),
        # The contraction guard, added 2026-09-07 (PREREG-2026-09-07-cue-repair.md): a match
        # followed by an apostrophe and a letter is not at a boundary ("needle't" fires
        # nothing), while the possessive still does ("needle's"). expect_detections is one
        # "plain", so an engine that lets the contraction through fails with two.
        ("mech_contraction_is_not_a_boundary",
         "a needle's point, but a needle't fires nothing", None),
    ]
    out = []
    for fid, text, _ in cases:
        hits = detect(text, tax, backend="cues")
        out.append({"id": fid, "text": text, "taxonomy": tax_json,
                    "expect_detections": sorted(h.detection_id for h in hits)})
    out.extend(_script_mechanism(tax_json))
    return out


#: Cues and probes per writing system, as \u escapes so this file stays ASCII and no editor or
#: pipeline can silently transcode a test case. Each entry:
#:   (detection id, cue, text where the cue stands alone, text where it is embedded or None)
#: `embedded` is None for scripts written WITHOUT spaces, where matching a substring is the
#: correct semantics and there is no "embedded" case to refuse.
_SCRIPT_PROBES = [
    # Cyrillic: "russkiy mir" alone, then inside "mirovoy".
    ("cyrillic", "русский мир",
     "идея русский мир "
     "жива",
     "русский мировой"),
    # Arabic: "dar al-harb" alone, then inside its adjectival form.
    ("arabic", "دار الحرب",
     "في دار الحرب اليوم",
     "دار الحربية"),
    # Hebrew: "eretz yisrael" alone, then with a suffixed yod.
    ("hebrew", "ארץ ישראל",
     "בתוך ארץ ישראל "
     "היום",
     "ארץ ישראלי"),
    # Devanagari: "hindu rashtra" alone, then inside "rashtravad".
    ("devanagari",
     "हिन्दू राष्ट्र",
     "यह हिन्दू "
     "राष्ट्र है",
     "हिन्दू "
     "राष्ट्रवाद"),
    # Greek.
    ("greek", "μεγάλη ιδέα",
     "η μεγάλη ιδέα ήταν",
     "μεγάλη ιδέας"),
    # Latin with diacritics -- the case the old ASCII class got wrong in the other direction:
    # a cue followed by an accented letter used to look like a boundary and matched.
    ("latin_diacritic", "regime", "the regime fell", "Regimeänderung was the goal"),
    # CJK: no spaces, so the cue is always flanked by letters. Applying the boundary rule here
    # rejected EVERY match -- the regression this fixture exists to catch.
    ("cjk", "天下为公",
     "他们说天下为公很重要", None),
    # Japanese kana, same property.
    ("kana", "あの世", "それはあの世です", None),
]


def _script_mechanism(_unused_tax_json):
    """Per-script boundary fixtures, one synthetic taxonomy carrying a cue in each script.

    WHY THIS IS A MECHANISM FIXTURE AND NOT A LENS FIXTURE
    -----------------------------------------------------
    2026-09-03. The boundary rule went Unicode-aware on both sides (Python `\\w`, JS
    `/[\\p{L}\\p{N}_]/u`, measured equivalent over 47 characters across nine scripts). Before
    that, every non-Latin cue was a PREFIX match: `dar al-harb` fired inside its own adjective.
    The lens-fixture arm could not have caught it, because no real lens carries a non-Latin cue
    and none should until the engine is trusted -- which is circular unless the engine is tested
    on synthetic ones.

    It also pins the regression that the Unicode fix itself introduced and that only measuring
    revealed: in a script with no spaces every occurrence is flanked by letters, so the new rule
    refused all of CJK. Going from "fires but leaks" to "never fires" is worse, and it would
    have shipped as a Unicode improvement.
    """
    from tradecraft.schema import Taxonomy, Marker, Detection, GradingConfig

    dets = [Detection(id=name, weight=1.0, definition="script boundary probe: %s" % name,
                      cues=[cue])
            for name, cue, _pos, _neg in _SCRIPT_PROBES]
    tax = Taxonomy(id="_mechanism_scripts", name="engine script boundaries",
                   description="synthetic",
                   markers=[Marker(id="s", name="s", base_weight=1.0, detections=dets)],
                   config=GradingConfig())
    tax_json = {
        "id": tax.id, "name": tax.name,
        "markers": [{"id": m.id, "name": m.name, "base_weight": m.base_weight,
                     "detections": [{"id": d.id, "weight": d.weight,
                                     "definition": d.definition,
                                     "cues": list(d.cues),
                                     "excludes": list(d.excludes)}
                                    for d in m.detections]}
                    for m in tax.markers],
        "config": {"marker_present_threshold": tax.config.marker_present_threshold,
                   "w_breadth": tax.config.w_breadth,
                   "w_intensity": tax.config.w_intensity,
                   "w_density": tax.config.w_density,
                   "density_cap_per_1k": tax.config.density_cap_per_1k,
                   "tiers": list(tax.config.tiers or [])},
    }

    rows = []
    for name, _cue, positive, embedded in _SCRIPT_PROBES:
        rows.append(("mech_script_%s_fires" % name, positive))
        if embedded is not None:
            rows.append(("mech_script_%s_refuses_embedded" % name, embedded))
    out = []
    for fid, text in rows:
        hits = detect(text, tax, backend="cues")
        out.append({"id": fid, "text": text, "taxonomy": tax_json,
                    "expect_detections": sorted(h.detection_id for h in hits)})
    return out


def fixtures():
    """Fixtures + their Python-computed output. engine.js re-runs these in the browser
    and screams if it disagrees; that is the parity gate."""
    fx_path = REPO / "eval" / "fixtures.json"
    raw = json.load(open(fx_path, encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("fixtures", [])
    lenses = load_lenses(str(REPO / "detectors"))
    out = []
    for f in rows:
        lid = f.get("lens")
        tax = lenses.get(lid)
        if not tax or not tax.cues_usable or f.get("min_backend") == "llm":
            continue
        hits = detect(f["text"], tax, backend="cues")
        tok = max(1, len(f["text"].split()))
        r = grade_document_for_lens(tax, hits, token_count=tok)
        out.append({
            "id": f.get("id"), "lens": lid, "text": f["text"],
            "expect": {"index": r.index, "tier": r.tier,
                       "markers_present": sorted(r.markers_present),
                       "n_hits": len(hits)},
        })
    return out


def mirror():
    """The detector pointed at the author's own books, precomputed so the manuscripts
    never ship to a browser. Rendered as a calibration exhibit: a book ABOUT
    institutional permeation quoting Fabian and Powell-memo language SHOULD fire the
    permeation lens, and the point is that the reader can see which hits are quotes,
    which are topic, and which are the author's own voice."""
    lenses = load_lenses(str(REPO / "detectors"))
    scoreable = {k: v for k, v in lenses.items() if v.cues_usable}
    out = []
    # All four Evil Robots books. It was two, under prose saying "the author's own
    # books" -- the page's signature honesty move, run on half the corpus.
    for slug, title in (("evil-robots", "The Secret Life of Evil Robots"),
                        ("the-ratchet", "The Ratchet"),
                        ("quiet-autocomplete", "Quiet Autocomplete"),
                        ("the-last-antibodies", "The Last Antibodies")):
        d = BOOKS / slug / "chapters"
        if not d.exists():
            continue
        chapters = []
        for f in sorted(d.glob("*.md")):
            text = f.read_text(encoding="utf-8", errors="replace")[:200000]
            tok = max(1, len(text.split()))
            per_lens = []
            for lid, tax in scoreable.items():
                hits = detect(text, tax, backend="cues")
                if not hits:
                    continue
                r = grade_document_for_lens(tax, hits, token_count=tok)
                per_lens.append({
                    "lens": lid, "index": r.index, "tier": r.tier,
                    "hits": [{"detection": h.detection_id, "span": h.span,
                              "start": h.char_start} for h in hits[:12]],
                })
            per_lens.sort(key=lambda x: -x["index"])
            chapters.append({"file": f.name, "tokens": tok, "lenses": per_lens,
                             "total_hits": sum(len(x["hits"]) for x in per_lens)})
        out.append({"slug": slug, "title": title, "chapters": chapters})
    return out


def resolution():
    """CP6 — ship the RULER beside the reading.

    The page currently shows an index with nothing that says how big a difference has to be
    before it means anything. That is the exact defect this project indicts in the ten studies
    it critiques: an effect reported without the resolution of the instrument producing it.

    So each lens carries its state and its floor object, read from `eval/floors_contract.py`'s
    normalised records:

      index          a measured index floor, and the smallest difference it can resolve
      receipts-only  no index, ever. A firing rate against a measured background, and the
                     minimum rate a subject corpus of a given size could distinguish
      graph          edge-perturbation floor (CP5, unbuilt -- these appear as receipts-only)

    `publishable_mde` is the one a surface may print. It is true only when the corpus behind
    the number is one a reader can rebuild -- and it is FALSE for every lens index floor,
    because 95 of the background documents are vendored news text with no manifest. Publishing
    those MDEs would put a figure nobody outside can check on a page whose whole argument is
    recompute-it-yourself.
    """
    sys.path.insert(0, str(REPO / "eval"))
    import floors_contract as FC       # noqa: E402  (path set immediately above)
    import background_rate as BR       # noqa: E402  (its sidecar loader and verdict text)

    lens_ids = sorted(load_lenses(str(REPO / "detectors")))
    per_lens = {}
    for rec in FC.collect():
        for lens_id in lens_ids:
            if not rec["claim"].startswith(lens_id + " "):
                continue
            slot = per_lens.setdefault(lens_id, {"state": "receipts-only", "floors": []})
            if rec["state"] == "index":
                slot["state"] = "index"
            slot["floors"].append({
                "statistic": rec["statistic"],
                "null": rec["null"],
                "n": rec["n"],
                "threshold_p95": rec["threshold_p95"],
                "mde": rec["mde"],
                "publishable_mde": bool(rec["recomputable"]),
                "source": rec["source"],
            })

    # THE LENGTH-INVARIANT UNIT (issue #7, plan 1.3). The firing-rate floors above are
    # fired-documents over documents, on a pool spanning 140 to 57,458 words -- a null that
    # moves with the page count of its control corpus. eval/occurrence_rate.py measures the
    # background as OCCURRENCES PER 1,000 WORDS with an exact Poisson interval, and tests each
    # lens for length homogeneity with an exact conditional test that is valid at any count.
    # Shipped beside the old record, not instead of it, so every public rate carries its unit
    # and its verdict: "yes (could detect 2.6x)", "no evidence, and no power", or "no --
    # varies by SOURCE TYPE". A lens the test could not check is never printed as checked.
    # The pool includes 95 vendored news documents a reader cannot rebuild, so this is not
    # recomputable in the publishable_mde sense -- the UI says so.
    occ = BR._occurrence_sidecar()
    for lens_id, slot in per_lens.items():
        o = occ.get(lens_id)
        if not o:
            continue
        slot["occurrence_rate"] = {
            "statistic": "occurrences-per-1k-words",
            "null": "background-rate",
            "occurrences": o.get("occurrences"),
            "kwords": o.get("kwords"),
            "rate_per_1k": o.get("rate_per_1k"),
            "ci95": o.get("ci95"),
            "length_invariance": BR._invariance_note(o).replace("**", ""),
            "detectable_rate_ratio": o.get("detectable_rate_ratio"),
            "kwords_for_4x": o.get("kwords_for_4x"),
            "recomputable": False,
            "source": "eval/occurrence_rate.py",
        }
    return {
        "_note": ("Per-lens resolution. A reading without its ruler is the defect this "
                  "project exists to indict, so the page must not render an index without "
                  "the floor beside it. Print an MDE only where publishable_mde is true."),
        "lenses": per_lens,
        "states": {
            "index": "Holds a measured index floor; a difference below its MDE is not a finding.",
            "receipts-only": ("No index and no leaderboard rank. Each firing ships as a "
                              "receipt, read against a measured background rate."),
            "graph": "Edge-perturbation floor. Harness unbuilt (CP5).",
        },
    }


def build():
    return {
        "generated_by": "tradecraft/tools/export_web.py",
        "note": ("Emitted from the same taxonomy loader the Python detector uses. "
                 "engine.js contains no marker vocabulary of its own; if this payload "
                 "is absent the page reports it instead of degrading silently."),
        "taxonomies": taxonomies(),
        "cut_ledger": cut_ledger(),
        "fixtures": fixtures(),
        "mechanism": mechanism(),
        "mirror": mirror(),
        "resolution": resolution(),
        "limits": {
            "no_verify_layer": "Every hit here is a raw, unverified cue match. There is "
                               "no model judging whether the cue means what it looks "
                               "like -- which is exactly why the author's own books "
                               "light up.",
            "llm_only_lenses": sorted(llm_only(load_lenses(str(REPO / "detectors")))),
            "single_document": "One document at a time. No subject profile, no timeline.",
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    payload = build()
    tx, fx = payload["taxonomies"], payload["fixtures"]
    n_markers = sum(len(t["markers"]) for t in tx.values())
    n_llm_only = sum(1 for t in tx.values() if t.get("llm_only"))
    print(f"lenses {len(tx)} ({n_llm_only} llm-only) · markers {n_markers} · "
          f"fixtures {len(fx)} · cut-ledger {len(payload['cut_ledger'])} · "
          f"books {len(payload['mirror'])}")
    for b in payload["mirror"]:
        print(f"  mirror {b['slug']}: {sum(c['total_hits'] for c in b['chapters'])} hits "
              f"across {len(b['chapters'])} chapters")
    dest = OUT / "instrument.json"
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if a.check:
        if not dest.exists():
            print("DRIFT: instrument.json missing", file=sys.stderr); return 1
        committed = dest.read_text(encoding="utf-8")
        if committed == blob:
            return 0
        # The mirror section is built by reading the MANUSCRIPTS, which live in sibling
        # repos (books/<slug>/chapters). mirror() skips a book whose chapters it cannot
        # find, so in CI — where only this repo is checked out — a fresh export always has
        # "mirror": [] while the committed payload has both books. That made this check fail
        # on every pipeline forever, for an environment difference rather than staleness, and
        # regenerating locally could never fix it. Compare everything the environment can
        # actually reproduce, and say plainly that the manuscript-derived part went unchecked.
        if not payload["mirror"]:
            try:
                a_no_mirror = {k: v for k, v in json.loads(committed).items() if k != "mirror"}
                b_no_mirror = {k: v for k, v in payload.items() if k != "mirror"}
                if json.dumps(a_no_mirror, ensure_ascii=False, sort_keys=True) == \
                   json.dumps(b_no_mirror, ensure_ascii=False, sort_keys=True):
                    print("instrument.json matches apart from the mirror section, which "
                          "needs books/<slug>/chapters (not checked out here) -- "
                          "manuscript mirror UNVERIFIED", file=sys.stderr)
                    return 0
            except Exception:
                pass
        print("DRIFT: instrument.json differs from a fresh export -- "
              "run tradecraft/tools/export_web.py", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    dest.write_text(blob, encoding="utf-8", newline="")
    print(f"wrote {dest.relative_to(SERIES)}  {dest.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
