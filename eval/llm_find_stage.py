#!/usr/bin/env python3
"""The LLM find stage, measured at scale on PTC -- per lens AND per detection, resumable.

WHY THIS EXISTS
---------------
The barometer plan (2026-09-02) names one measurement as deciding whether the detector has a
future past its three demonstrated detections: run detect.py's LLM find stage over the PTC
benchmark on the local 14B and see whether it finds what the cue floor cannot. The cue stage is
at a measured ceiling (97% of cues never appear in PTC; 3 of 140 detections beat chance --
`RESULTS-2026-09-03-detection-census.md`) and the embedding stage measured AT CHANCE
(`RESULTS-2026-08-27-embedding-find-stage.md`). The LLM arm is the only find stage never put
on this benchmark at scale.

`compare_find_stages.py --llm` already runs the arm but reports per LENS only, keeps no cache
(so an hour-per-lens run that dies at article 300 is an hour lost), and drops LLM hits whose
quoted span cannot be located in the text without counting them. This script keeps the same
statistic -- in-span precision over the LENGTH-MATCHED permutation null, Wilson interval, the
absolute count of annotated spans recovered -- and adds what the decision needs:

  * per-DETECTION rows with the census's own judgeability rule (>= JUDGEABLE_HITS firings)
    and Wilson interval, so "the detector grows" means "a detection the cue census did not
    have is now demonstrated above chance", not "a lens average moved";
  * the CUE arm on the same articles as the baseline, so lift is read against the floor that
    already exists and annotated-span recovery is compared in absolute terms (the 2026-08-26
    lesson: a better ratio of a smaller pool is not a gain);
  * unlocatable spans COUNTED (the model quoted text that is not in the document), because a
    hit that cannot be placed is a fabrication rate, not nothing;
  * a per-(model, prompt-hash, lens, article) cache under eval/cache/, so the run resumes and
    the RESULTS file recomputes from the cache byte-for-byte.

THE PRE-REGISTERED RULE lives in PREREG-2026-09-07-llm-find-stage.md, committed before the
first full-lens run. This script computes; it does not decide. It changes nothing in
floors.json or the lens states -- a state change is a separate, reviewed edit that cites the
RESULTS file, and CP2 (which lenses may ever print an index) is the author's call.

    python eval/llm_find_stage.py --lens institutional_permeation --limit 3   # smoke the rig
    python eval/llm_find_stage.py --lens inevitability_framing                # one lens, full PTC
    python eval/llm_find_stage.py --report                                    # tables from cache only
    python eval/llm_find_stage.py --report --markdown                         # for the RESULTS file
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # tradecraft/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from ptc_precision import load_corpus, covered                      # noqa: E402
from compare_find_stages import chance_for                          # noqa: E402
from detection_census import wilson, load_techniques, techniques_at, JUDGEABLE_HITS  # noqa: E402
from tradecraft.detect import detect, detect_cues, build_user_prompt, _system  # noqa: E402
from tradecraft.loader import load_lenses                           # noqa: E402
from tradecraft.local_llm import LOCAL_MODEL                        # noqa: E402

CACHE_DIR = HERE / "cache"
OUT_JSON = HERE / "llm-find-stage.json"

#: Pre-registered lens order (PREREG-2026-09-07-llm-find-stage.md). Model-only lenses first --
#: the LLM find stage is the ONLY find stage they can have -- then the receipts-only cue
#: lenses, then the five index-bearing ones. revolving_door is a graph lens with no text
#: markers and is excluded by pre-registration.
LENS_ORDER = [
    "inevitability_framing", "distributed_accountability", "cognitive_capture",
    "counterproductivity", "legibility",
    "narrative_management", "militant_mobilization", "rollback_asymmetry", "adept_speech",
    "costly_signal", "network_brokerage",
    "institutional_permeation", "sourcing_asymmetry", "reference_capture", "subculture_register",
]
EXCLUDED = {"revolving_door"}

#: Fixed permutation seed: the null must not move between runs (same as compare_find_stages).
SEED = 20260907


def prompt_hash(tax) -> str:
    """Keys the cache on the exact prompt the model saw. A change to the find prompt or to the
    taxonomy text invalidates the cache for that lens instead of mixing two prompts' answers."""
    h = hashlib.sha256()
    h.update(_system().encode("utf-8"))
    h.update(build_user_prompt(tax, "").encode("utf-8"))
    return h.hexdigest()[:12]


def cache_path(model: str, lens: str) -> Path:
    safe = model.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"llm-find__{safe}__{lens}.jsonl"


def load_cache(path: Path, phash: str) -> dict:
    """article id -> record. Records from a different prompt hash are ignored, not reused."""
    out = {}
    if not path.is_file():
        return out
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("prompt_hash") == phash:
            out[rec["article"]] = rec
    return out


def append_cache(path: Path, rec: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_lens(lens: str, tax, corpus, model: str, limit: int, log) -> dict:
    """Run (or resume) the LLM arm for one lens over the corpus. Returns article -> record."""
    phash = prompt_hash(tax)
    path = cache_path(model, lens)
    cache = load_cache(path, phash)
    todo = [d for d in corpus if d["id"] not in cache]
    if limit:
        todo = [d for d in corpus[:limit] if d["id"] not in cache]
    log(f"[{lens}] cached {len(cache)}, to run {len(todo)}, model {model}, prompt {phash}")
    t0 = time.time()
    for i, d in enumerate(todo, 1):
        t1 = time.time()
        err = None
        raw = []
        try:
            hits = detect(d["text"], tax, backend="local", model=model)
            for h in hits:
                raw.append({"detection_id": h.detection_id, "span": h.span,
                            "confidence": h.confidence,
                            "char_start": h.char_start, "char_end": h.char_end})
        except Exception as exc:                                    # noqa: BLE001
            err = f"{type(exc).__name__}: {str(exc)[:200]}"
        rec = {"article": d["id"], "lens": lens, "model": model, "prompt_hash": phash,
               "seconds": round(time.time() - t1, 1), "error": err, "hits": raw}
        append_cache(path, rec)
        cache[d["id"]] = rec
        if i % 10 == 0 or i == len(todo):
            el = time.time() - t0
            log(f"[{lens}] {i}/{len(todo)}  {el / i:.1f}s/article  ~{(el / i) * (len(todo) - i) / 60:.0f}m left")
    return cache


def tally(lens: str, tax, corpus, records: dict, tech: dict) -> dict:
    """Per-lens and per-detection statistics for the LLM arm, with the cue arm beside it."""
    rng = random.Random(SEED)
    articles = [d for d in corpus if d["id"] in records]
    chance_chars = (sum(e - s for d in articles for s, e in d["spans"])
                    / max(1, sum(len(d["text"]) for d in articles)))

    def fresh():
        return {"hits": 0, "inside": 0, "chance_sum": 0.0, "len_sum": 0, "spans": set(),
                "techniques": {}}

    arms = {"llm": fresh(), "cues": fresh()}
    per_det = {}
    unlocatable = 0
    errors = 0
    for d in articles:
        rec = records[d["id"]]
        if rec.get("error"):
            errors += 1
        staged = []
        for h in rec["hits"]:
            if h["char_start"] is None:
                unlocatable += 1
                continue
            staged.append(("llm", h["detection_id"], h["char_start"], h["char_end"]))
        for h in detect_cues(d["text"], tax):
            staged.append(("cues", h.detection_id, h.char_start, h.char_end))
        for arm, det, a, b in staged:
            b = b if b is not None else a + 1
            hl = max(1, b - a)
            t = arms[arm]
            t["hits"] += 1
            t["len_sum"] += hl
            t["chance_sum"] += chance_for(d["spans"], len(d["text"]), hl, rng)
            inside = covered(d["spans"], a, b)
            if inside:
                t["inside"] += 1
                for s, e in d["spans"]:
                    if a < e and b > s:
                        t["spans"].add((d["id"], s, e))
                for tq in techniques_at(tech.get(d["id"], []), a, b):
                    t["techniques"][tq] = t["techniques"].get(tq, 0) + 1
            if arm == "llm":
                pd = per_det.setdefault(det, {"hits": 0, "inside": 0, "chance_sum": 0.0, "techniques": {}})
                pd["hits"] += 1
                pd["chance_sum"] += chance_for(d["spans"], len(d["text"]), hl, rng)
                if inside:
                    pd["inside"] += 1
                    for tq in techniques_at(tech.get(d["id"], []), a, b):
                        pd["techniques"][tq] = pd["techniques"].get(tq, 0) + 1

    def summarise(t):
        n, k = t["hits"], t["inside"]
        if not n:
            return {"hits": 0, "inside": 0, "precision": None, "chance": None, "lift": None,
                    "lift_ci": None, "mean_hit_chars": None, "spans_recovered": 0, "techniques": {}}
        prec = k / n
        chance = t["chance_sum"] / n
        lo, hi = wilson(k, n)
        return {"hits": n, "inside": k, "precision": round(prec, 4),
                "chance": round(chance, 4),
                "lift": round(prec / chance, 3) if chance else None,
                "lift_ci": [round(lo / chance, 3), round(hi / chance, 3)] if chance else None,
                "mean_hit_chars": round(t["len_sum"] / n),
                "spans_recovered": len(t["spans"]),
                "techniques": dict(sorted(t["techniques"].items(), key=lambda kv: -kv[1]))}

    llm, cues = summarise(arms["llm"]), summarise(arms["cues"])
    llm_only_spans = arms["llm"]["spans"] - arms["cues"]["spans"]

    dets = []
    for det, pd in sorted(per_det.items(), key=lambda kv: -kv[1]["hits"]):
        n, k = pd["hits"], pd["inside"]
        chance = pd["chance_sum"] / n if n else None
        lo, hi = wilson(k, n)
        judgeable = n >= JUDGEABLE_HITS
        lift = (k / n) / chance if (n and chance) else None
        ci = [lo / chance, hi / chance] if chance else None
        if not judgeable:
            verdict = "too thin to judge"
        elif ci and ci[0] > 1.0:
            verdict = "above chance, interval excludes it"
        elif ci and ci[1] < 1.0:
            verdict = "below chance, interval excludes it"
        else:
            verdict = "interval spans chance"
        dets.append({"detection": det, "hits": n, "inside": k,
                     "lift": round(lift, 2) if lift is not None else None,
                     "lift_ci": [round(ci[0], 2), round(ci[1], 2)] if ci else None,
                     "judgeable": judgeable, "verdict": verdict,
                     "techniques": dict(sorted(pd["techniques"].items(), key=lambda kv: -kv[1]))})

    def lens_verdict(s):
        if s["hits"] < JUDGEABLE_HITS:
            return "untestable on PTC (fewer than %d locatable hits)" % JUDGEABLE_HITS
        if s["lift_ci"] and s["lift_ci"][0] > 1.0:
            return "above chance, interval excludes it"
        if s["lift_ci"] and s["lift_ci"][1] < 1.0:
            return "below chance, interval excludes it"
        return "interval spans chance"

    return {
        "lens": lens, "llm_only": not tax.cues_usable,
        "articles": len(articles), "of": len(corpus), "errors": errors,
        "chance_chars": round(chance_chars, 4),
        "llm": llm, "cues": cues,
        "llm_unlocatable_spans": unlocatable,
        "llm_unlocatable_rate": round(unlocatable / (unlocatable + llm["hits"]), 3)
                                if (unlocatable + llm["hits"]) else None,
        "spans_recovered_llm_only": len(llm_only_spans),
        "llm_verdict": lens_verdict(llm),
        "cues_verdict": lens_verdict(cues),
        "detections_demonstrated_llm": sum(1 for x in dets if x["verdict"].startswith("above")),
        "detections": dets,
    }


def report(results: list, markdown: bool) -> str:
    lines = []
    if markdown:
        lines.append("| lens | model-only | articles | LLM hits | in-span | LLM lift [95% CI] | "
                     "cues hits | cues lift [95% CI] | spans recovered LLM / cues / LLM-only | "
                     "unlocatable | detections demonstrated (LLM) | LLM verdict |")
        lines.append("|---|---|---:|---:|---:|---|---:|---|---|---:|---:|---|")
        for r in results:
            L, C = r["llm"], r["cues"]
            fmt = lambda s: ("%.2f [%.2f, %.2f]" % (s["lift"], s["lift_ci"][0], s["lift_ci"][1])) if s["lift"] is not None else "-"
            lines.append("| `%s` | %s | %d/%d | %d | %d | %s | %d | %s | %d / %d / %d | %d (%s) | %d | %s |" % (
                r["lens"], "yes" if r["llm_only"] else "no", r["articles"], r["of"],
                L["hits"], L["inside"], fmt(L), C["hits"], fmt(C),
                L["spans_recovered"], C["spans_recovered"], r["spans_recovered_llm_only"],
                r["llm_unlocatable_spans"],
                ("%.0f%%" % (100 * r["llm_unlocatable_rate"])) if r["llm_unlocatable_rate"] is not None else "-",
                r["detections_demonstrated_llm"], r["llm_verdict"]))
        lines.append("")
        lines.append("| lens | detection | hits | in-span | lift | 95% CI | verdict | techniques landed on |")
        lines.append("|---|---|---:|---:|---:|---|---|---|")
        for r in results:
            for x in r["detections"]:
                if not x["judgeable"]:
                    continue
                ci = "[%.2f, %.2f]" % tuple(x["lift_ci"]) if x["lift_ci"] else "-"
                tq = ", ".join("%s %d" % kv for kv in list(x["techniques"].items())[:3])
                lines.append("| `%s` | `%s` | %d | %d | %s | %s | %s | %s |" % (
                    r["lens"], x["detection"], x["hits"], x["inside"],
                    ("%.2f" % x["lift"]) if x["lift"] is not None else "-", ci, x["verdict"], tq))
        return "\n".join(lines)
    for r in results:
        L, C = r["llm"], r["cues"]
        lines.append("%-28s %s articles %d/%d  errors %d" % (
            r["lens"], "(model-only)" if r["llm_only"] else "", r["articles"], r["of"], r["errors"]))
        for name, s in (("llm", L), ("cues", C)):
            if s["hits"]:
                lines.append("   %-5s hits %4d inside %4d prec %.3f chance %.3f lift %.2f [%.2f, %.2f] spans %d"
                             % (name, s["hits"], s["inside"], s["precision"], s["chance"], s["lift"],
                                s["lift_ci"][0], s["lift_ci"][1], s["spans_recovered"]))
            else:
                lines.append("   %-5s hits    0" % name)
        lines.append("   unlocatable LLM spans %d  spans only the LLM recovered %d  detections demonstrated %d"
                     % (r["llm_unlocatable_spans"], r["spans_recovered_llm_only"], r["detections_demonstrated_llm"]))
        lines.append("   LLM verdict: %s" % r["llm_verdict"])
        for x in r["detections"]:
            if x["judgeable"]:
                lines.append("      %-36s hits %3d inside %3d lift %5s  %s" % (
                    x["detection"], x["hits"], x["inside"],
                    ("%.2f" % x["lift"]) if x["lift"] is not None else "-", x["verdict"]))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lens", action="append", help="lens id (repeatable); default: LENS_ORDER")
    ap.add_argument("--limit", type=int, default=0, help="first N articles only (smoke test)")
    ap.add_argument("--model", default=LOCAL_MODEL)
    ap.add_argument("--report", action="store_true", help="tally from cache only; run nothing")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    def log(msg):
        print(msg, file=sys.stderr, flush=True)

    corpus = load_corpus()
    tech = load_techniques()
    lenses = load_lenses(str(ROOT / "detectors"))
    order = a.lens or LENS_ORDER
    bad = [l for l in order if l not in lenses or l in EXCLUDED]
    if bad:
        sys.exit("unknown or excluded lens: %s" % ", ".join(bad))

    results = []
    for lens in order:
        tax = lenses[lens]
        if a.report:
            records = load_cache(cache_path(a.model, lens), prompt_hash(tax))
            if not records:
                continue
        else:
            records = run_lens(lens, tax, corpus, a.model, a.limit, log)
        results.append(tally(lens, tax, corpus, records, tech))

    payload = {"model": a.model, "corpus_articles": len(corpus), "seed": SEED,
               "judgeable_hits": JUDGEABLE_HITS, "lenses": results,
               "note": ("Lift is in-span precision over the length-matched permutation null "
                        "(compare_find_stages.chance_for). Intervals are Wilson 95%. A lens with "
                        "fewer than judgeable_hits locatable LLM hits is untestable on PTC, not "
                        "failed. Nothing here changes a lens state; see the PREREG.")}
    # Write the aggregate payload ONLY when this run covered every lens.
    #
    # It used to write on any non---limit run, so `--lens adept_speech` replaced the whole
    # 15-lens file with a ONE-lens payload. Nothing said so, and the file is the artifact the
    # RESULTS doc recomputes from -- so between per-lens runs (the documented way to work
    # through the corpus, ~50 min each) anyone reading it saw a single lens and no indication
    # the rest had been dropped. Caught 2026-09-11 while running four lenses back to back:
    # each completion silently clobbered the file the previous three were recorded in.
    #
    # Partial runs still print their report to stdout; they just no longer overwrite the
    # aggregate. Re-run `--report` (no --lens) to rebuild it from the caches.
    covered_all = set(order) >= (set(LENS_ORDER) - EXCLUDED)
    if not a.limit and covered_all:
        OUT_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    elif not a.limit:
        log(f"[note] {len(results)} of {len(LENS_ORDER)} lenses this run — "
            f"{OUT_JSON.name} left alone; re-run --report to rebuild it")
    if a.json:
        print(json.dumps(payload, indent=1, ensure_ascii=False))
    else:
        print(report(results, a.markdown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
