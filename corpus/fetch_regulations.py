#!/usr/bin/env python3
"""Fetch public rulemaking comments from regulations.gov: advocacy prose, written to persuade.

WHY THIS SOURCE
---------------
Twelve of sixteen lenses cannot state a detection floor because nothing in the corpus makes
them fire. Measured 2026-09-01 and 2026-09-02, the reason is register, not cue quality:

  * The Federal Register corpus ADMINISTERS. `rollback_asymmetry` scored 0.0 on "Fourth
    Temporary Extension of COVID-19 Telemedicine Flexibilities" -- a textbook ratchet that
    argues for nothing, because regulations do not argue.
  * Congressional hearings turned out to be procedural too. 74,923 words of testimony, and
    `inevitability_framing` fired on 1 of 206 documents. Searching that text for the move in
    ANY phrasing returns "inevitab" twice and "only option" once. The move is not there in
    other words -- it is not there. A chair asks, a witness answers with qualifications, and
    both argue in institutional voice.

Public comments on a rulemaking are the opposite. Someone filed them to CHANGE AN OUTCOME:
industry associations, advocacy groups, unions, professional bodies and individuals arguing
that a measure must be adopted, widened, or must not be reversed. That is the register
`rollback_asymmetry`, `inevitability_framing`, `costly_signal` and `counterproductivity` were
authored for, and corpus item 28 named it explicitly: "op-eds, speeches, consultation
responses, campaign material arguing that a measure must not be reversed."

Public domain as US government records, freely retrievable, and the API takes the SAME
api.data.gov key as govinfo (`GOVINFO_API_KEY`). 572,881 comments match "surveillance
oversight" alone.

WHAT IT DOES NOT DO
-------------------
No labelling. These are documents, not specimens: `tools/harvest_gold.py` finds candidates and
a human decides. A fetcher that assigned labels would build a corpus that teaches the lenses
whatever the search terms encoded.

No PDF parsing. Many filings say "See attached document" and put the substance in an
attachment; those are SKIPPED rather than half-read, and the count is reported so the gap is
visible. With half a million inline comments available there is no need to guess at a PDF.

DISCIPLINE
----------
Serial, delayed, capped, descriptive user agent, stop on failure rather than retry. The list
endpoint carries no comment text, so the body costs one request per document -- which is
exactly why the cap is low and the delay is real.

    python corpus/fetch_regulations.py --dry-run
    python corpus/fetch_regulations.py --per-term 8 --min-words 150
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
OUT = os.path.join(HERE, "advocacy-comments.jsonl")
API = "https://api.regulations.gov/v4"

KEY = os.environ.get("GOVINFO_API_KEY") or os.environ.get("REGULATIONS_API_KEY", "")
UA = "tradecraft-corpus/1.0 (research corpus build; github.com/gorrie/tradecraft)"
DELAY = 2.0
CAP = 60

# Subjects where these lenses should have something to find. Terms choose what to LOOK at,
# never what to conclude. Matched to the surveillance/legibility/permeation surface the
# taxonomy was written against.
TERMS = [
    "surveillance oversight",
    "digital identity verification",
    "facial recognition rulemaking",
    "data broker registration",
    "know your customer requirement",
    "content moderation transparency",
    "emergency powers extension",
    "encryption lawful access",
]

# "See attached" boilerplate. A filing whose whole inline body is a pointer is not prose.
POINTER_PHRASES = (
    "see attached",
    "see the attached",
    "please see attached",
    "attached please find",
    "see uploaded",
    "comment attached",
)


def get(path, params):
    params = dict(params)
    params["api_key"] = KEY
    url = "%s%s?%s" % (API, path, urllib.parse.urlencode(params, doseq=True))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.loads(fh.read().decode("utf-8", errors="replace"))


def search(term, limit):
    payload = get("/comments", {
        "filter[searchTerm]": term,
        "page[size]": min(limit, 250),
        "sort": "-postedDate",
    })
    return payload.get("data") or []


def detail(comment_id):
    return get("/comments/%s" % comment_id, {}).get("data", {}).get("attributes", {}) or {}


def is_pointer(text):
    low = " ".join((text or "").split()).lower()
    if len(low.split()) > 60:
        return False          # long enough to be substance even if it mentions an attachment
    return any(p in low for p in POINTER_PHRASES)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-term", type=int, default=8,
                    help="candidates to consider per search term")
    ap.add_argument("--min-words", type=int, default=120,
                    help="shortest inline comment worth keeping as a document")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not KEY:
        print("no api.data.gov key. Set GOVINFO_API_KEY (the same key serves govinfo and")
        print("regulations.gov). Free at api.data.gov/signup.")
        return 2

    existing = set()
    if os.path.exists(OUT):
        for line in io.open(OUT, encoding="utf-8"):
            line = line.strip()
            if line:
                existing.add(json.loads(line)["id"])

    planned = []
    for term in TERMS:
        try:
            hits = search(term, args.per_term)
        except Exception as exc:
            print("search failed for %r: %s -- stopping" % (term, str(exc)[:90]))
            break
        for h in hits:
            cid = h.get("id")
            if not cid or ("rg_%s" % cid) in existing:
                continue
            planned.append((("rg_%s" % cid), term, h))
        time.sleep(DELAY)

    seen, unique = set(), []
    for item in planned:
        if item[0] in seen:
            continue
        seen.add(item[0])
        unique.append(item)
    unique = unique[:CAP]

    print("%d candidate(s) to fetch (cap %d, %.1fs apart, one request each)"
          % (len(unique), CAP, DELAY))
    for cid, term, h in unique[:8]:
        print("  %-30s %s" % (term[:30], (h.get("attributes", {}).get("title") or "")[:52]))
    if args.dry_run or not unique:
        return 0

    written = skipped_pointer = skipped_short = 0
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as out:
        for cid, term, h in unique:
            raw_id = cid[3:]
            try:
                a = detail(raw_id)
            except Exception as exc:
                print("  fetch failed %s: %s -- stopping rather than retrying"
                      % (raw_id, str(exc)[:70]))
                break
            # regulations.gov returns the comment body as HTML. This was a bare whitespace
            # join, so `<br/>` and `&rsquo;` went into the corpus as words: 28 of 38 stored
            # comments carry tags and 36 of 38 carry entities. Every one is a token in
            # `text.split()`, and a cue written with a real apostrophe cannot match `&rsquo;`.
            body = textnorm.clean(a.get("comment") or "")
            if is_pointer(body):
                skipped_pointer += 1
                time.sleep(DELAY)
                continue
            if len(body.split()) < args.min_words:
                skipped_short += 1
                time.sleep(DELAY)
                continue
            out.write(json.dumps({
                "id": cid,
                "register": "advocacy",
                "found_by_term": term,
                "source_url": "https://www.regulations.gov/comment/%s" % raw_id,
                "docket_id": a.get("docketId"),
                "agency": a.get("agencyId"),
                # WHO is arguing. The faction dimension the leaderboard needs, straight from
                # the filing rather than inferred: an association, a company, or an individual.
                "organization": a.get("organization"),
                "category": a.get("category"),
                "date": a.get("postedDate"),
                "title": a.get("title"),
                "note": ("US government record, public domain. A public comment filed on a "
                         "federal rulemaking: prose written to change an outcome, which is "
                         "the register these lenses were authored for and neither the Federal "
                         "Register nor congressional hearings supplied."),
                "text": body,
            }, ensure_ascii=False) + "\n")
            written += 1
            print("  + %-26s %4d words  %s"
                  % (raw_id[:26], len(body.split()),
                     (a.get("organization") or a.get("title") or "")[:38]))
            time.sleep(DELAY)

    print()
    print("wrote %d advocacy comment(s) to %s" % (written, os.path.relpath(OUT, HERE)))
    print("skipped: %d pointing at an attachment, %d under %d words"
          % (skipped_pointer, skipped_short, args.min_words))
    print("Unlabelled by design. Run tools/harvest_gold.py to find candidates in them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
