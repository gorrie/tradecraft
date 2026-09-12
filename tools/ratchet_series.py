#!/usr/bin/env python3
"""Count one-way movement over a series of documents about one measure.

The administrative ratchet, as distinct from the rhetorical one. See
detectors/ratchet_series/README.md for why the two are different objects.

    python tools/ratchet_series.py --measure "telemedicine flexibilities"
    python tools/ratchet_series.py --measure "Investigatory Powers" --since 2016
    python tools/ratchet_series.py --measure "..." --json          # machine-readable
    python tools/ratchet_series.py --self-test                     # no network

Every output is marked provisional. The detector has no measured floor yet: its nuisance
factors are docket-matching errors, coverage gaps and ambiguous movements, none of which
eval/lens_floor.py addresses. Backlog item 30.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(ROOT, "detectors", "ratchet_series", "movements.yaml")
API = "https://www.federalregister.gov/api/v1/documents.json"
UA = "tradecraft-ratchet-series/1.0 (research; github.com/gorrie/tradecraft)"
DELAY = 2.0


def load_spec():
    import yaml
    with io.open(SPEC, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def classify(title, spec):
    """Return (direction, matched_pattern, note). Ambiguity resolves to neither, on purpose."""
    t = " ".join((title or "").lower().split())
    # Procedural first, then ambiguous, then direction. A title containing both a procedural
    # and a directional pattern is procedural: "Notice of Extension of Time Limit" contains
    # "extension of", and letting that win counts the agency's own filing deadline as a click.
    for entry in spec.get("procedural", []):
        if entry["pattern"] in t:
            return "neither", entry["pattern"], entry.get("note", "procedural by rule")
    # Ambiguous next: a title containing both an ambiguous and a directional pattern is
    # ambiguous. Letting `extension` win over `technical correction` would invent movement.
    for entry in spec.get("ambiguous", []):
        if entry["pattern"] in t:
            return "neither", entry["pattern"], entry.get("note", "ambiguous by rule")
    for direction in ("forward", "back"):
        for entry in spec.get(direction, []):
            if entry["pattern"] in t:
                return direction, entry["pattern"], entry.get("note", "")
    return "neither", None, "no pattern matched"


def fetch_series(measure, since, per_page):
    params = [
        ("per_page", str(per_page)),
        # newest, not oldest: with a per_page cap, ordering oldest returns the START of the
        # record and a ratchet accumulates toward the present. The first live run fetched
        # 1996-1999 documents for a measure whose extensions all fall in 2021-2025 and
        # reported 0 forward, 0 back -- a coverage gap presented as an absence of movement,
        # which is the worst failure this detector could have.
        ("order", "newest"),
        ("conditions[term]", measure),
        ("fields[]", "title"),
        ("fields[]", "document_number"),
        ("fields[]", "publication_date"),
        ("fields[]", "html_url"),
        ("fields[]", "type"),
        ("fields[]", "docket_ids"),
        ("fields[]", "regulation_id_numbers"),
    ]
    if since:
        params.append(("conditions[publication_date][gte]", "%s-01-01" % since))
    url = API + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.loads(fh.read().decode("utf-8", errors="replace")).get("results", [])


def fetch_docket(docket, since, per_page):
    """Every document on one published docket, oldest first.

    WHY THIS PATH EXISTS (2026-09-01, measured)
    -------------------------------------------
    Term search seeds the series and then picks the dominant docket out of the seeds. That
    works for a measure with one rulemaking behind it and fails silently for a PROGRAM. Asked
    for "continued dumping duty" -- the negative pole of this project's discrimination claim --
    the seeds came back as 100 documents carrying 95 DISTINCT DOCKETS, the most common of them
    appearing twice. Every antidumping case is its own rulemaking, one per product per country,
    so the term names a program under which hundreds of unrelated series each publish. The
    original "10 back, p = 0.002" was computed across those strangers.

    And the seed window is volume-dependent. 5,760 documents match that term since 2010; with
    order=newest and per_page=100 the seeds spanned ten weeks. For any common term the search
    cannot reach far enough back to see a series at all, which is a coverage gap at the recent
    end exactly mirroring the one the newest-ordering was introduced to fix at the old end.

    Seeding by docket removes both failures: membership is the published identifier, ordering
    is oldest-first because a series is read from its beginning, and A-549-502 -- one Thai
    steel-pipe case -- returns 102 documents spanning 1994 to 2026, an order of magnitude more
    than any series this detector has measured.
    """
    params = [
        ("per_page", str(per_page)),
        ("order", "oldest"),
        ("conditions[docket_id]", docket),
        ("fields[]", "title"),
        ("fields[]", "document_number"),
        ("fields[]", "publication_date"),
        ("fields[]", "html_url"),
        ("fields[]", "type"),
        ("fields[]", "docket_ids"),
        ("fields[]", "regulation_id_numbers"),
    ]
    if since:
        params.append(("conditions[publication_date][gte]", "%s-01-01" % since))
    url = API + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.loads(fh.read().decode("utf-8", errors="replace")).get("results", [])


def series_keys(docs):
    """Docket ids carried by the documents a term search returned, most common first.

    The seeds are whatever the full-text search found. Their dockets are the candidate series.
    Taking the most common one avoids letting a single stray document define the series.
    """
    counts = {}
    for d in docs:
        for k in (d.get("docket_ids") or []):
            counts[k] = counts.get(k, 0) + 1
    return sorted(counts, key=lambda k: -counts[k])


def in_series(doc, keys):
    """Membership by published docket identifier, not by words in a title.

    Title matching was tried both ways and both were wrong. Requiring ANY distinctive word
    admitted a Medicare hospice rule into a suspicious-activity-report series. Requiring ALL of
    them deleted an 83-document series outright and cut telemedicine from 12 documents to 4,
    taking its p from 0.0078 to 0.125 and destroying the only Axis-3 result this project had.

    The Federal Register publishes docket_ids on every document and they are what identify a
    rulemaking series. The two COVID telemedicine extensions share Docket DEA-407; the
    buprenorphine expansion that inflated the original count carries DEA-948 and is correctly
    excluded now.
    """
    if not keys:
        return False
    return any(k in (doc.get("docket_ids") or []) for k in keys)


def binom_p(k, n):
    """Two-sided exact binomial p for k one-way movements out of n directional ones, null 0.5.

    An asymmetry ratio of +1.000 is the same number for 2 forward 0 back as for 8 forward 0
    back, and they are not the same claim: p = 0.500 against p = 0.008. Reporting the ratio
    alone would let a two-document series carry the weight of an eight-document one, which is
    this detector's version of quoting an effect without its resolution -- the exact defect the
    sibling bias study spent three days documenting in other people's work.
    """
    if n == 0:
        return None
    from math import comb
    tail = sum(comb(n, i) for i in range(0, min(k, n - k) + 1))
    p = 2.0 * tail / (2 ** n)
    return round(min(1.0, p), 4)


def ambiguity_bound(moves):
    """Asymmetry if every ambiguous document were forced forward, and if forced back.

    The ambiguous bucket in movements.yaml is counted as neither, which is the honest default
    and also a choice. If the sign of the asymmetry survives forcing every ambiguous document
    the other way, the result is robust to that choice. If it does not, the result is a
    classification decision wearing the costume of a measurement.
    """
    fwd = sum(1 for m in moves if m["direction"] == "forward")
    back = sum(1 for m in moves if m["direction"] == "back")
    amb = sum(1 for m in moves if m["direction"] == "neither")
    def ratio(f, b):
        return None if (f + b) == 0 else round((f - b) / (f + b), 3)
    return {"all_ambiguous_forward": ratio(fwd + amb, back),
            "all_ambiguous_back": ratio(fwd, back + amb),
            "ambiguous_count": amb}


def analyse(docs, spec, measure=None, keys=None):
    moves = []
    if keys is None and measure:
        keys = series_keys(docs)[:1]
    for d in docs:
        if keys and not in_series(d, keys):
            continue
        direction, pattern, note = classify(d.get("title"), spec)
        moves.append({
            "date": d.get("publication_date"),
            "document_number": d.get("document_number"),
            "title": d.get("title"),
            "url": d.get("html_url"),
            "direction": direction,
            "matched": pattern,
            "note": note,
        })
    fwd = sum(1 for m in moves if m["direction"] == "forward")
    back = sum(1 for m in moves if m["direction"] == "back")
    neither = sum(1 for m in moves if m["direction"] == "neither")
    dated = [m["date"] for m in moves if m["date"]]
    return {
        "provisional": True,
        "provisional_reason": ("no measured floor: docket-matching, coverage gaps and "
                              "ambiguous movements are unquantified (backlog item 30)"),
        "documents": len(moves),
        "discarded_not_in_series": len(docs) - len(moves),
        "series_dockets": list(keys or []),
        "forward": fwd,
        "back": back,
        "neither": neither,
        "asymmetry": None if (fwd + back) == 0 else round((fwd - back) / (fwd + back), 3),
        "p_value": binom_p(max(fwd, back), fwd + back),
        "resolvable": bool((fwd + back) >= 5 and (binom_p(max(fwd, back), fwd + back) or 1) < 0.05),
        "ambiguity_bound": ambiguity_bound(moves),
        "span": ("%s to %s" % (min(dated), max(dated))) if dated else None,
        "receipts": moves,
    }


SELF_TEST = [
    ("Fourth Temporary Extension of COVID-19 Telemedicine Flexibilities", "forward"),
    ("ALP Express Pilot to Permanent Status", "forward"),
    ("Extension of Postponement of Effectiveness for Certain Provisions", "forward"),
    ("Rescission of Conservation and Landscape Health Rule", "back"),
    ("Revocation of Authorization for Use of Brominated Vegetable Oil", "back"),
    ("Removal of Regulations for Renewal Communities Designation", "back"),
    ("Increase of Monetary Thresholds and Other Matters", "neither"),
    ("Cost of Living Adjustment to Satellite Carrier Compulsory License", "neither"),
    ("Conformance of Cost Accounting Standards to GAAP for CAS 407", "neither"),
]


def self_test(spec):
    """The two documents that defeated the rhetorical lens must classify correctly here."""
    bad = 0
    print("SELF-TEST — the titles rollback_asymmetry scored 0.0 on")
    for title, want in SELF_TEST:
        got, pattern, _ = classify(title, spec)
        ok = got == want
        bad += 0 if ok else 1
        print("  %-7s want %-8s got %-8s  %s" % ("ok" if ok else "FAIL", want, got, title[:56]))
    print()
    if bad:
        print("%d of %d misclassified." % (bad, len(SELF_TEST)))
        return 1
    print("All %d classify correctly, including the two that scored 0.0 on the text lens:" % len(SELF_TEST))
    print("  'Fourth Temporary Extension...' and 'ALP Express Pilot to Permanent Status'.")
    print("A count sees what a cue list cannot, because the pattern was never written down.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--measure", help="search term identifying one measure")
    ap.add_argument("--docket", help="published docket id, e.g. DEA-407 or A-549-502. "
                                     "Skips term search: membership is the identifier itself")
    ap.add_argument("--since", help="earliest year, e.g. 2016")
    ap.add_argument("--per-page", type=int, default=100)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    spec = load_spec()
    if args.self_test:
        return self_test(spec)
    if not (args.measure or args.docket):
        ap.error("--measure or --docket is required (or use --self-test)")

    label = args.docket or args.measure
    try:
        if args.docket:
            docs = fetch_docket(args.docket, args.since, args.per_page)
        else:
            docs = fetch_series(args.measure, args.since, args.per_page)
    except Exception as exc:
        print("fetch failed: %s" % exc)
        return 1
    time.sleep(DELAY)

    result = analyse(docs, spec, label)
    result["measure"] = label
    result["seeded_by"] = "docket" if args.docket else "term"

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print("MEASURE: %s" % label)
    if args.docket:
        print("SERIES:  %s   (seeded BY docket -- membership is the identifier itself)"
              % args.docket)
    elif result.get("series_dockets"):
        print("SERIES:  %s   (membership by published docket, not by title)"
              % ", ".join(result["series_dockets"]))
    print("PROVISIONAL — %s" % result["provisional_reason"])
    print()
    print("%d document(s), %s" % (result["documents"], result["span"] or "no dates"))
    print("  forward (the click):   %d" % result["forward"])
    print("  back (the un-click):   %d" % result["back"])
    print("  neither:               %d" % result["neither"])
    if result["asymmetry"] is not None:
        print("  asymmetry:             %+.3f  (+1 = only ever forward, -1 = only ever back)"
              % result["asymmetry"])
        print("  exact binomial p:      %s" % result["p_value"])
        b = result["ambiguity_bound"]
        print("  if all %d ambiguous went forward: %s   back: %s"
              % (b["ambiguous_count"], b["all_ambiguous_forward"], b["all_ambiguous_back"]))
        print()
        if result["resolvable"]:
            print("  RESOLVABLE: at least 5 directional movements and p < 0.05.")
        else:
            print("  NOT RESOLVABLE. Too few directional movements, or the one-way run is")
            print("  what chance produces at this count. The ratio is reported because it is")
            print("  what the documents say; it is not yet a finding.")
    print()
    print("RECEIPTS — every directional movement, with its document number")
    for m in result["receipts"]:
        if m["direction"] == "neither":
            continue
        print("  %s  %-7s  %-14s %s" % (m["date"], m["direction"], m["document_number"],
                                        (m["title"] or "")[:56]))
    print()
    print("Direction only. Whether any of these movements was WISE is not a question this")
    print("detector asks; two readers who disagree about that must get the same counts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
