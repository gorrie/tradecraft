#!/usr/bin/env python3
"""Collateral, second pass: the detectors on each board institution's OWN public output.

The first pass (collateral_eval.py) read what the record already held -- verbatim texts of
persons -- and could reach one of 36 board institutions. This pass reads the institutions
themselves: every ledger receipt URL that receipt_url_ruling.py ruled `own` (the institution's
own host) or `own-archived` (a primary text of its principals or organs hosted by a documentary
archive). Third-party reporting is never graded here; printing a critic's rhetoric on the
institution's row would be the attribution error this project indicts elsewhere.

TWO STEPS, ONE NETWORK
----------------------
`--fetch` pulls the ruled URLs ONCE, under the project's fetch discipline (serial, 2 s apart,
descriptive User-Agent, hard cap, non-text skipped and counted, a short page counted as a stub),
and stores the extracted text with its sha256 and fetch date in collateral-own-output.jsonl.
Wikipedia pages come through the MediaWiki parse API and the same `plain()` extraction the
corpus tools use, so the text is the article and not the site chrome. Everything after that --
grading, rulers, the frozen hand-read sample, `--check` -- reads the stored file and touches no
network, so the gate is reproducible in CI and the measured text is the committed text.

Grading is the same as pass 1 (the functions are imported from it): cues on every text lens,
the shipped scanner through node, both rulers, interval verdicts, a fixed-seed hand-read sample
frozen after the first run. Pre-registered in PREREG-2026-09-07-collateral-pass2.md.

    python eval/collateral_pass2.py --fetch      # network, once; writes collateral-own-output.jsonl
    python eval/collateral_pass2.py              # grade the stored texts, write collateral-pass2.json
    python eval/collateral_pass2.py --check      # exit 1 if collateral-pass2.json is stale (no network)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SERIES = os.path.dirname(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "corpus"))

import collateral_eval as P1  # noqa: E402
from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft.subject import GRAPH_LENSES  # noqa: E402
import fetch_manifest as FM  # noqa: E402

RULING = os.path.join(HERE, "receipt-url-ruling.json")
STORE = os.path.join(HERE, "collateral-own-output.jsonl")
OUT = os.path.join(HERE, "collateral-pass2.json")
FROZEN = os.path.join(HERE, "collateral-pass2-sample-frozen.json")
PREREG = "PREREG-2026-09-07-collateral-pass2.md"
SEED = 20260908
GRADABLE = ("own", "own-archived")
CAP = 60
DELAY = 2.0


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def ruled_urls():
    R = json.load(open(RULING, encoding="utf-8"))
    rows = [r for r in R["rows"] if r["class"] in GRADABLE]
    # one fetch per URL; an URL shared by two institutions (the EIP report, for SIO and EIP) is
    # fetched once and graded on both rows
    by_url = {}
    for r in rows:
        by_url.setdefault(r["url"], {"url": r["url"], "class": r["class"], "rule": r["rule"], "why": r["why"],
                                     "institutions": []})["institutions"].append(r["institution"])
    return [by_url[u] for u in sorted(by_url)], R


def fetch_wikipedia(url):
    import mediawiki as MW
    title = urllib.parse.unquote(urllib.parse.urlparse(url).path.split("/wiki/", 1)[1])
    MW.API = "https://en.wikipedia.org/w/api.php"
    return MW.fetch_rendered(title), "text/html (MediaWiki parse API)"


def fetch(items):
    today = dt.date.today().isoformat()
    out = []
    for n, it in enumerate(items[:CAP]):
        if n:
            time.sleep(DELAY)
        rec = {"url": it["url"], "institutions": it["institutions"], "class": it["class"], "fetched": today}
        try:
            if "en.wikipedia.org/wiki/" in it["url"]:
                text, ctype = fetch_wikipedia(it["url"])
            else:
                text, ctype = FM.fetch_one(it["url"])
            rec["content_type"] = ctype
            if text is None:
                rec.update({"status": "non-text", "words": 0, "text": ""})
            else:
                words = len(text.split())
                if words < FM.MIN_WORDS:
                    rec.update({"status": "stub", "words": words, "text": text})
                else:
                    rec.update({"status": "ok", "words": words, "sha256_16": sha(text), "text": text})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)          # back off; do not retry in a loop
            rec.update({"status": f"http {e.code}", "words": 0, "text": ""})
        except Exception as e:  # noqa: BLE001 -- recorded, never retried
            rec.update({"status": f"error: {type(e).__name__}", "words": 0, "text": ""})
        out.append(rec)
        print(f"  {rec['status']:12} {rec.get('words', 0):>6}w  {it['url'][:90]}", flush=True)
    with open(STORE, "w", encoding="utf-8", newline="\n") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out


def load_store():
    if not os.path.exists(STORE):
        return []
    with open(STORE, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def build():
    lenses = {lid: tax for lid, tax in load_lenses(P1.DETECTORS).items() if lid not in GRAPH_LENSES}
    store = load_store()
    ruled, R = ruled_urls()
    # one graded doc per (institution, url) so each institution's row is read on its own texts
    texts = []
    for rec in store:
        if rec.get("status") != "ok":
            continue
        for inst in rec["institutions"]:
            texts.append({"id": f"{P1.board_institutions().get(inst) or inst}|{rec['url']}", "person_id": inst,
                          "text": rec["text"], "url": rec["url"], "date": rec.get("fetched")})
    texts.sort(key=lambda t: (t["person_id"], t["id"]))
    texts_by_id = {t["id"]: t for t in texts}
    rul = P1.rulers()
    docs = P1.run_tradecraft(texts, lenses)
    scan = P1.run_scanner(texts)
    inst_ids = P1.board_institutions()
    per_inst = {}
    for inst in sorted({t["person_id"] for t in texts}):
        mine = [d for d in docs if d["person_id"] == inst]
        tab = P1.lens_table(mine, lenses, rul)
        sp = (P1.scanner_table([m for m in scan if m["person_id"] == inst], mine) if scan else None)
        per_inst[inst] = {
            "id": inst_ids.get(inst), "docs": len(mine), "words": sum(d["words"] for d in mine),
            "urls": [d["url"] for d in mine],
            "lenses": {lid: {k: v for k, v in row.items()
                             if k in ("docs_fired", "occurrences", "per_1k", "per_1k_ci95", "verdict",
                                      "detections", "in_quotes", "min_detectable_ratio", "one_cue", "top_detection")}
                       for lid, row in tab.items() if row["occurrences"]},
            "lenses_zero": sorted(lid for lid, row in tab.items() if not row["occurrences"]),
            "scanner": ({"asserted": sp["asserted_total"], "attributed": sp["attributed_total"],
                         "bands": sp["bands"], "scored_texts": sp["scored_texts"]} if sp else None),
            "caveat": "The institution's own published text, graded by the literal cue matcher against each "
                      "lens's general-prose background. What the text exhibits; not a finding about intent.",
        }
    fetched = {s: sum(1 for r in store if r.get("status") == s) for s in sorted({r.get("status") for r in store})}
    not_graded = [{"url": r["url"], "institutions": r["institutions"], "status": r.get("status"),
                   "words": r.get("words", 0)} for r in store if r.get("status") != "ok"]
    landing = [r for r in R["rows"] if r["class"] == "own-landing"]
    return {
        "meta": {
            "prereg": PREREG, "seed": SEED,
            "ruling": {"file": "receipt-url-ruling.json", "by_class": R["by_class"],
                       "institutions_with_own_output": R["institutions_with_own_output"],
                       "institutions_total": R["institutions_total"]},
            "store": {"file": os.path.basename(STORE), "urls": len(store), "by_status": fetched,
                      "fetched": sorted({r.get("fetched") for r in store})},
            "graded": {"docs": len(docs), "institutions": len(per_inst), "words": sum(d["words"] for d in docs)},
            "taxonomy_sha256_16": P1.taxonomy_hash(),
            "detectors": {"tradecraft_cues": "ran", "capture_scanner": "ran" if scan is not None else "NOT RUN: node missing",
                          "tradecraft_llm_find_stage": "NOT RUN (GPU held; fabrication rate open)"},
            "what": "each board institution's OWN public output -- own-host pages and archived primary texts "
                    "of its principals, per receipt-url-ruling.json; never third-party reporting",
        },
        "lenses": P1.lens_table(docs, lenses, rul),
        "institutions": per_inst,
        "not_graded": not_graded,
        "own_landing_not_graded": [{"institution": r["institution"], "url": r["url"], "why": r["why"]} for r in landing],
        "scanner": P1.scanner_table(scan, docs) if scan else None,
        "precision_sample": P1.precision_sample(docs, texts_by_id, frozen=FROZEN),
    }


def render(R):
    m = R["meta"]
    L = [f"## Pass 2: {m['graded']['docs']} own-output documents / {m['graded']['institutions']} institutions / "
         f"{m['graded']['words']:,} words; store {m['store']['by_status']}; taxonomy {m['taxonomy_sha256_16']}", "",
         "| lens | occ | per 1k [95%] | bg per 1k [95%] | verdict | top detection | in quotes |", "|---|---:|---|---|---|---|---:|"]
    for lid, r in R["lenses"].items():
        if not r["occurrences"]:
            continue
        bg = r["background"]
        L.append(f"| `{lid}` | {r['occurrences']} | {r['per_1k']} {r['per_1k_ci95']} | {bg.get('per_1k')} {bg.get('per_1k_ci95')} | "
                 f"**{r['verdict']}** | {r['top_detection']['id']} ({r['top_detection']['share']}) | {r['in_quotes']} |")
    L += ["", "## Per institution", ""]
    for inst, v in R["institutions"].items():
        fired = ", ".join(f"`{lid}` {r['occurrences']} ({r['per_1k']}, {r['verdict']})" for lid, r in v["lenses"].items())
        L.append(f"- **{inst}** ({v['id']}): {v['docs']} docs / {v['words']:,} words. {fired or 'nothing fired'}.")
    L += ["", f"## Not graded: {len(R['not_graded'])} fetched URLs " +
          str([(n['status'], n['url'][:60]) for n in R['not_graded']]),
          f"## Own-landing (text not on page): {len(R['own_landing_not_graded'])}",
          f"## Hand-read sample: {len(R['precision_sample']['rows'])} spans"]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args(argv)
    if a.fetch:
        items, _ = ruled_urls()
        print(f"fetching {min(len(items), CAP)} ruled URLs, {DELAY}s apart")
        fetch(items)
        return 0
    R = build()
    if a.check:
        if not os.path.exists(OUT):
            print("DRIFT: collateral-pass2.json missing", file=sys.stderr)
            return 1
        have = json.load(open(OUT, encoding="utf-8"))
        if R["scanner"] is None and have.get("scanner") is not None:
            R["scanner"] = have["scanner"]
            R["meta"]["detectors"]["capture_scanner"] = have["meta"]["detectors"]["capture_scanner"]
            for inst in R["institutions"]:
                R["institutions"][inst]["scanner"] = have["institutions"].get(inst, {}).get("scanner")
            if json.loads(json.dumps(R, sort_keys=True)) == have:
                print("node missing: tradecraft half verified, scanner half NOT verified", file=sys.stderr)
                return 2
        if json.loads(json.dumps(R, sort_keys=True)) != have:
            # Name the keys, same reason as pass 1: this failed in CI for hours behind a
            # message that said only "differs", while passing locally, and the Pages deploy
            # is gated on it.
            for path, mine, theirs in P1._drift_paths(
                    json.loads(json.dumps(R, sort_keys=True)), have):
                print(f"  DRIFT {path}: fresh={mine!r} stored={theirs!r}"[:300], file=sys.stderr)
            print("DRIFT: collateral-pass2.json differs from a fresh grading of the stored texts", file=sys.stderr)
            return 1
        return 0
    if a.markdown:
        print(render(R))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(R, fh, indent=1, sort_keys=True, ensure_ascii=False)
    print(render(R))
    print(f"\nwrote {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
