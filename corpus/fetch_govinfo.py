#!/usr/bin/env python3
"""Fetch advocacy prose from govinfo: congressional hearings and the Congressional Record.

WHY THIS SOURCE
---------------
The lenses were written for prose that ARGUES and were tested against prose that ADMINISTERS.
Measured 2026-09-01: 38 Federal Register documents fetched specifically for the subjects
`legibility` and `institutional_permeation` exist for produced ONE additional gold candidate,
and `rollback_asymmetry` scored 0.0 on "Fourth Temporary Extension of COVID-19 Telemedicine
Flexibilities" -- a textbook ratchet that argues for nothing because regulations do not argue.

Congressional hearings and floor debate are the opposite. A witness is there to persuade, a
member is there to make a case, and the moves these lenses detect -- inevitability framing,
asymmetric repeal burden, credential demands, sourcing asymmetry, dehumanising reframes -- are
made out loud and on the record.

Public domain as United States government works, full text available, and the API is open with
a demo key at low rates.

DISCIPLINE
----------
Serial, delayed, capped, descriptive user agent, stop on failure rather than retry. The demo
key is shared infrastructure and this corpus is not urgent.

Nothing fetched here is labelled. These are documents, not specimens: the harvester finds
candidates in them and a human decides. A fetcher that assigned labels would be building a
corpus that teaches the lenses whatever the search terms encoded.

    python corpus/fetch_govinfo.py --dry-run
    python corpus/fetch_govinfo.py --per-term 3
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
OUT = os.path.join(HERE, "advocacy-specimens.jsonl")
API = "https://api.govinfo.gov"
KEY = os.environ.get("GOVINFO_API_KEY", "DEMO_KEY")
UA = "tradecraft-corpus/1.0 (research corpus build; github.com/gorrie/tradecraft)"
DELAY = 3.0
CAP = 40

# Subjects where these lenses should have something to find. Terms choose what to LOOK at.
TERMS = [
    "surveillance oversight reform",
    "digital identity verification",
    "content moderation platform accountability",
    "emergency powers renewal",
    "encryption lawful access",
    "financial surveillance reporting",
]


def get(path, params):
    params = dict(params)
    params["api_key"] = KEY
    url = "%s%s?%s" % (API, path, urllib.parse.urlencode(params, doseq=True))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return fh.read().decode("utf-8", errors="replace")


def fetch_content(package_id):
    """Full text from the public content path. No API key, no shared rate limit."""
    url = ("https://www.govinfo.gov/content/pkg/%s/html/%s.htm"
           % (package_id, package_id))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as fh:
        return fh.read().decode("utf-8", errors="replace")


# Where the masthead stops and a person starts talking. A GPO hearing opens with 1,500-2,500
# words of committee roster, printing-office boilerplate and serial numbers before anyone makes
# an argument -- so a head-slice of the document is a slice of the masthead. Measured 2026-09-01:
# all 18 documents in the first fetch were front matter, truncated mid-sentence at the point the
# chair began speaking, and the rhetorical lenses fired on almost none of them. That looked like
# a register mismatch in the lenses and was a defect in this fetcher.
FRONT_MATTER_END = (
    "The Committee met",
    "The Subcommittee met",
    "The committee met",
    "The subcommittee met",
    "OPENING STATEMENT OF",
    "STATEMENT OF HON.",
    "PREPARED STATEMENT OF",
)


def body_window(body, chars):
    """Skip the masthead, then take `chars` of what follows.

    Returns (text, skipped_chars, was_cut, full_words).

    `was_cut` and `full_words` were added 2026-09-04. This function already recorded what it
    skipped at the FRONT -- `front_matter_chars_skipped` is in every record -- and said nothing
    about what it cut at the END. A hearing runs to tens of thousands of words and the window
    is 30,000 characters, so every specimen is a fragment, and the only way to discover that
    was to notice that 78% of the corpus sits within 10% of a 5,202-word maximum. A corpus
    should not need a statistical test to reveal how it was built.

    The window itself is right and stays: a head-slice of a hearing is a slice of the
    masthead, which is what the first fetch produced and what FRONT_MATTER_END exists to
    prevent. This only makes the record say so.
    """
    full_words = len(body.split())
    start = -1
    for marker in FRONT_MATTER_END:
        i = body.find(marker)
        if i >= 0 and (start < 0 or i < start):
            start = i
    if start < 0:
        # No marker: a Congressional Record item or a layout this does not know. Keep the head
        # rather than dropping the document, and record that nothing was skipped so the corpus
        # says which of its documents are windows and which are whole.
        return body[:chars], 0, len(body) > chars, full_words
    window = body[start:start + chars]
    # Cut on a word boundary when the tail is being dropped anyway: a severed token can match
    # a cue by accident and can never match one it would have matched whole.
    if len(body) > start + chars:
        window = window.rsplit(" ", 1)[0]
        return window, start, True, full_words
    return window, start, False, full_words


def search(term, limit):
    body = json.dumps({
        "query": '%s collection:(CHRG OR CREC)' % term,
        "pageSize": limit,
        "offsetMark": "*",
        "sorts": [{"field": "score", "sortOrder": "DESC"}],
    }).encode("utf-8")
    url = "%s/search?api_key=%s" % (API, KEY)
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.loads(fh.read().decode("utf-8", errors="replace")).get("results", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-term", type=int, default=3)
    # 8000 was the whole document's head and therefore the whole masthead. This is measured
    # from where a person starts talking, so it buys opening statements and the first
    # exchanges -- the part of a hearing that argues.
    ap.add_argument("--chars", type=int, default=30000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

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
            pid = h.get("packageId")
            if not pid or ("gi_%s" % pid) in existing:
                continue
            planned.append((("gi_%s" % pid), term, h))
        time.sleep(DELAY)

    seen, unique = set(), []
    for item in planned:
        if item[0] in seen:
            continue
        seen.add(item[0])
        unique.append(item)
    unique = unique[:CAP]

    print("%d document(s) to fetch (cap %d, %.1fs apart)" % (len(unique), CAP, DELAY))
    for sid, term, h in unique[:8]:
        print("  %-34s %s" % (term[:34], (h.get("title") or "")[:60]))
    if args.dry_run or not unique:
        return 0

    written = 0
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as out:
        for sid, term, h in unique:
            pid = h["packageId"]
            try:
                # Keyless content path, not the API. The shared DEMO_KEY rate-limits at around
                # 30 requests an hour and returned 429 after eight documents; the same files
                # are served from www.govinfo.gov/content without a key. Search still uses the
                # API because there is no keyless equivalent, and search is one call per term.
                text = fetch_content(pid)
            except Exception as exc:
                print("  fetch failed %s: %s -- stopping rather than retrying"
                      % (sid, str(exc)[:70]))
                break
            # Was a local `<[^>]+> -> space` plus a whitespace join, which left every entity
            # in place and split `H<INF>2</INF>O` into three tokens. Same normaliser as the
            # other two fetchers now, so all three corpora are cleaned identically -- they are
            # pooled into one background and were being cleaned three different ways.
            body = textnorm.clean(text)
            body, skipped, was_cut, full_words = body_window(body, args.chars)
            if len(body.split()) < 200:
                continue
            out.write(json.dumps({
                "id": sid,
                "register": "advocacy",
                "found_by_term": term,
                "source_url": "https://www.govinfo.gov/app/details/%s" % pid,
                "collection": h.get("collectionCode"),
                "date": h.get("dateIssued"),
                "title": h.get("title"),
                "note": ("US government work, public domain. Congressional hearing or record: "
                         "prose written to persuade, which is the register these lenses were "
                         "authored for and the Federal Register corpus is not."),
                # This is a WINDOW, not the document. A hearing runs to tens of thousands of
                # words; anything measured over this is measured over the opening statements.
                "excerpt": True,
                "front_matter_chars_skipped": skipped,
                # What was cut at the END, to match what is already recorded about the front.
                "truncated": was_cut,
                "truncated_at_chars": args.chars if was_cut else None,
                "full_words": full_words,
                "text": body,
            }, ensure_ascii=False) + "\n")
            written += 1
            print("  + %s  %s" % (sid[:22], (h.get("title") or "")[:52]))
            time.sleep(DELAY)

    print()
    print("wrote %d advocacy document(s) to %s" % (written, os.path.relpath(OUT, HERE)))
    print("Unlabelled by design. Run tools/harvest_gold.py to find candidates in them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
