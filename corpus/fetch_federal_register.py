#!/usr/bin/env python3
"""Build a domain-matched corpus for rollback_asymmetry from the US Federal Register.

WHY THIS SOURCE
---------------
The hard control for a method-lens is not off-topic text. It is text in the SAME register and
subject matter that does not exhibit the method. Asking `rollback_asymmetry` not to fire on
sports reporting proves nothing; asking it to separate a rule that ratchets from a rule that
genuinely winds a programme down is the actual test.

The Federal Register supplies both arms from one publisher, in one house style, with one
vocabulary: agencies impose, extend, and make permanent — and they also revoke, rescind, sunset
and remove. Public domain as a US government work, and a JSON API, so the corpus can be rebuilt
by anyone rather than trusted from a file we shipped.

WHAT IT DOES NOT DO
-------------------
It does not decide which arm a document belongs to. Search terms are recorded as
`candidate_arm` and every record carries `arm: null` and `labeled_by: null` until a human reads
it. Letting the query assign the label would build a corpus that teaches the lens to detect the
search terms — the same failure as tuning a detector on adversarial characterisation of a
group, and the same failure as the PTC background that measured a different construct and drove
a cue cut that damaged this instrument.

REQUEST DISCIPLINE
------------------
Serial. One request at a time, a delay between each, a descriptive user agent, and a hard cap.
On a 429 it stops rather than retrying. The Federal Register is a public service run for
everyone and this corpus is not urgent.

    python corpus/fetch_federal_register.py --dry-run     # show what it would fetch
    python corpus/fetch_federal_register.py --per-arm 10  # fetch and write specimens
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
sys.path.insert(0, HERE)

import textnorm  # noqa: E402  -- needs HERE on sys.path first
OUT = os.path.join(HERE, "method-specimens.jsonl")
API = "https://www.federalregister.gov/api/v1/documents.json"
UA = "tradecraft-corpus/1.0 (research corpus build; github.com/gorrie/tradecraft)"
DELAY = 2.0
CAP = 60

# Search terms only. These choose what to LOOK at, never what a document IS.
# Broadened 2026-09-01 for gold harvesting. The first six terms build the rollback_asymmetry
# arms; the rest widen the pool into the registers where legibility, institutional_permeation
# and sourcing_asymmetry actually operate -- registration schemes, data collection, standards
# setting, comment processes. Public domain throughout.
ARMS = {
    "registration-and-identity": [
        "mandatory registration requirement",
        "identity verification requirement",
        "enrollment in the system",
    ],
    "data-and-visibility": [
        "collection of information requirement",
        "reporting and recordkeeping requirements",
        "data sharing agreement",
    ],
    "standards-and-uniformity": [
        "uniform national standard",
        "preemption of state law",
    ],
    # Added 2026-09-03 for CP4a. `legibility` fires on 6 of 244 documents and an index floor
    # needs 8, so the pool needs more of the register it actually operates in: the apparatus
    # of administrative visibility -- registries, identifiers, standardised records.
    #
    # NONE of these is one of the lens's cues, and that is the whole constraint. Searching for
    # `visibility into` or `complete picture of` would build a corpus that teaches the lens to
    # detect its own search terms, which is the failure this file's header already warns about.
    # These name the MACHINERY; whether a document argues for making a population readable is
    # a separate question the lens answers, or does not.
    "registries-and-identifiers": [
        "central registry",
        "unique identifier",
        "standardized data elements",
        "national database",
        "beneficial ownership information",
        "records management requirements",
        "interoperability requirements",
    ],
    "comment-and-consultation": [
        "comments received from the public",
        "form letters received",
    ],
    "likely-ratchet": [
        "extension of temporary provisions",
        "made permanent",
        "removal of sunset provision",
    ],
    "likely-winddown": [
        "removal of regulations",
        "rescission of rule",
        "revocation of authorization",
    ],
}


def get(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return fh.read().decode("utf-8", errors="replace")


def search(term, per_page):
    params = [
        ("per_page", str(per_page)),
        ("order", "relevance"),
        ("conditions[term]", term),
        ("conditions[type][]", "RULE"),
        ("fields[]", "title"),
        ("fields[]", "document_number"),
        ("fields[]", "publication_date"),
        ("fields[]", "raw_text_url"),
        ("fields[]", "html_url"),
        ("fields[]", "agencies"),
    ]
    return json.loads(get(API, params)).get("results", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-arm", type=int, default=6,
                    help="documents per search term (kept small on purpose)")
    ap.add_argument("--chars", type=int, default=6000,
                    help="characters of body text to keep per specimen")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    existing = set()
    if os.path.exists(OUT):
        for line in io.open(OUT, encoding="utf-8"):
            line = line.strip()
            if line:
                existing.add(json.loads(line)["id"])

    planned = []
    for arm, terms in ARMS.items():
        for term in terms:
            try:
                hits = search(term, args.per_arm)
            except Exception as exc:
                print("search failed for %r: %s" % (term, exc))
                return 1
            for h in hits:
                doc = h.get("document_number")
                if not doc or not h.get("raw_text_url"):
                    continue
                sid = "fr_%s" % doc
                if sid in existing:
                    continue
                planned.append((sid, arm, term, h))
            time.sleep(DELAY)

    # De-duplicate: a document matching two terms is one document.
    seen, unique = set(), []
    for item in planned:
        if item[0] in seen:
            continue
        seen.add(item[0])
        unique.append(item)
    unique = unique[:CAP]

    print("%d new document(s) to fetch (cap %d, %.1fs apart)" % (len(unique), CAP, DELAY))
    for sid, arm, term, h in unique[:8]:
        print("  %-16s %-16s %s" % (sid, arm, h["title"][:70]))
    if len(unique) > 8:
        print("  ... and %d more" % (len(unique) - 8))
    if args.dry_run or not unique:
        return 0

    written = 0
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as out:
        for sid, arm, term, h in unique:
            try:
                text = get(h["raw_text_url"])
            except Exception as exc:
                print("  fetch failed %s: %s -- stopping rather than retrying" % (sid, exc))
                break
            # SLICE ON A WORD BOUNDARY, and record that the slice happened.
            #
            # This was `[:args.chars]` on the joined string -- a raw character cut. Measured
            # 2026-09-04 by tools/truncation_scan.py: 117 of 155 stored specimens end
            # mid-sentence and at least one ends mid-URL-token
            # ("...%20DEA%20SAMHSA%20buprenorphine%20telemedi"), which is a fragment that can
            # match a cue by accident and can never match one it would have matched whole.
            #
            # The 6,000-character default is a defensible sample size for a candidate corpus.
            # What was not defensible is that nothing in the record said the text was a
            # fragment, so a reader -- or a later script -- had no way to know these are not
            # whole documents. `truncated` and `full_words` make each record say so itself.
            # NORMALISE BEFORE MEASURING. The Federal Register's raw text carries its own
            # markup -- `<bullet>`, `<INF>`/`<SUP>`, `</a>`, Cloudflare email spans, `&#160;`
            # -- and this was a bare whitespace join, so all 155 stored specimens held tags as
            # words. Cleaning after the character cut would be worse than not cleaning: the cut
            # would be measured against a length that includes markup, so the same `--chars`
            # would keep a different amount of prose per document depending on how marked-up it
            # was.
            full = textnorm.clean(text)
            if len(full) > args.chars:
                body = full[:args.chars].rsplit(" ", 1)[0]
                was_cut = True
            else:
                body = full
                was_cut = False
            agencies = ", ".join(a.get("name", "") for a in (h.get("agencies") or []))
            rec = {
                "id": sid,
                # `instrument`, not `lens`. These are Federal Register MEASURES: the
                # administrative ratchet is read off a SERIES by ratchet_series, not off one
                # document by a prose lens. Every record used to say `lens:
                # rollback_asymmetry`, which made a settled scoping decision look like a
                # capability gap -- that lens fires on 1 of 68 of them because the pattern is
                # not in any single document (detectors/ratchet_series/README.md). Corrected
                # 2026-09-03 by W1.9; corrected HERE too so the next fetch cannot undo it.
                "instrument": "ratchet_series",
                "role": "unadjudicated-candidate",
                "candidate_arm": arm,
                "found_by_term": term,
                # Deliberately unset. A human reads the document and decides.
                "arm": None,
                "labeled_by": None,
                "source_url": h.get("html_url"),
                "date": h.get("publication_date"),
                "author": agencies or "US federal agency",
                "title": h.get("title"),
                "note": ("US Federal Register, public domain. Retrieved for a domain-matched "
                         "corpus: same publisher and register on both arms. candidate_arm is "
                         "the search bucket, NOT a label."),
                "text": body,
                # Self-describing, so nothing downstream has to infer it from a length
                # distribution the way the truncation scan had to.
                "truncated": was_cut,
                "truncated_at_chars": args.chars if was_cut else None,
                "full_words": len(full.split()),
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            print("  + %s  %s" % (sid, (h.get("title") or "")[:64]))
            time.sleep(DELAY)

    print()
    print("wrote %d specimen(s) to %s" % (written, os.path.relpath(OUT, os.path.dirname(HERE))))
    print("Every one has arm=null. Label them by reading, then the positive arm unblocks")
    print("eval/lens_floor.py and the negative arm becomes the domain-matched control.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
