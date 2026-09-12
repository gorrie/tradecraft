#!/usr/bin/env python3
"""Fetch a camp's public-domain canon from Wikisource, for the shibboleth study.

WHY THIS EXISTS
---------------
`BACKLOG-shibboleth-corpus-study.md` step 1 is "assemble the canon": 2-4 primary works the camp
itself treats as foundational. For camps whose canon is out of copyright that is a fetch, and on
2026-09-03 doing it for `georgist` cost most of a session in avoidable ways. This is that path,
written down, so the next camp pays none of it.

**Project Gutenberg is not the source.** Its pages say, verbatim, "DON'T USE THIS PAGE FOR
SCRAPING. Seriously. You'll only get your IP blocked", and point at a full catalog dump instead.
Wikisource has a MediaWiki API built for programmatic access, so that is what this uses.

THE TWO TRAPS, both of which fail QUIETLY
-----------------------------------------
1. **Proofread books keep their text in the `Page:` namespace and transclude it.** So
   `prop=revisions` returns the transclusion stub, not the book: 28 chapters of *Progress and
   Poverty* came back as **189 words total** and looked like a successful fetch. `action=parse`
   renders the transclusion. This tool tries the cheap batched call first, then re-fetches any
   page that came back suspiciously short.
2. **`titles=` does not follow redirects** unless `redirects=1`. Without it, 7 of 8 requested
   Henry George works returned nothing at all, again with a clean exit.

Both are why `--report` prints per-page word counts rather than a total: a stub is only visible
per page.

FETCH DISCIPLINE
----------------
Batched (up to 40 titles per request, so a 28-chapter book is one call), serial, 1.5-2s between
requests, descriptive User-Agent with a contact address, and it stops rather than hammering on
failure. The corpus is written OUTSIDE the repo by default -- `tools/harvest_tells.py`'s
precedent is that only the tool is committed, and a fetched canon is reproducible from the
manifest of titles, which is the part worth keeping.

    # list a work's chapter subpages, write them as a title manifest
    python corpus/fetch_wikisource.py --list "Progress and Poverty (George, unsourced)/" \
        --manifest ~/canon/georgist.titles

    # fetch them (JSONL: one record per page, with its title as provenance)
    python corpus/fetch_wikisource.py --manifest ~/canon/georgist.titles \
        --out ~/canon/georgist.jsonl --report

    # a single work that is not split into subpages, redirects followed
    python corpus/fetch_wikisource.py --title "The Condition of Labour" --out ~/canon/x.jsonl
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import html
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request

#: NO PRIVATE COPY. Every function below used to live here and now lives in
#: corpus/mediawiki.py, because a second wiki (Wikinews, for the reader-recomputable
#: background pool) needed the same API handling and the choice was between two copies of the
#: wikitext stripper or one. The stripper is exactly the part that must not fork: the
#: brace-matching in strip_templates and the ws-noexport drop are the difference between a
#: corpus of prose and a corpus of navigation furniture, both measured, and a divergent second
#: implementation would move idiom counts that are already published in results files.
#:
#: Verified behaviour-identical at extraction: 14 synthetic cases and 256 real corpus
#: documents through both implementations, zero divergence. See tests/test_mediawiki.py.
from mediawiki import (  # noqa: E402,F401
    API,
    BATCH,
    DELAY,
    UA,
    _DROP_CLASSES,
    _get,
    fetch_batched,
    fetch_rendered,
    list_subpages,
    plain,
    strip_elements,
    strip_templates,
)

#: A page shorter than this is almost certainly a transclusion stub rather than a short chapter,
#: so it gets re-fetched through action=parse. 189 words spread over 28 chapters is what this
#: threshold exists to catch.
STUB_WORDS = 200


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", metavar="PREFIX",
                    help="list mainspace subpages under this prefix")
    ap.add_argument("--manifest", help="file of page titles, one per line")
    ap.add_argument("--title", action="append", default=[],
                    help="a single page title; repeatable")
    ap.add_argument("--out", help="JSONL destination (keep it OUTSIDE the repo)")
    ap.add_argument("--report", action="store_true",
                    help="print per-page word counts -- a stub is only visible per page")
    args = ap.parse_args(argv)

    if args.list:
        titles = list_subpages(args.list)
        if args.manifest:
            io.open(args.manifest, "w", encoding="utf-8", newline="\n").write(
                "\n".join(titles) + "\n")
            print("%d subpage(s) -> %s" % (len(titles), args.manifest))
        else:
            for t in titles:
                print(t)
        if not titles:
            print("no subpages under %r. The work may be a single page, or the exact title "
                  "differs -- try --title, which follows redirects." % args.list)
        return 0

    titles = list(args.title)
    if args.manifest:
        titles += [t.strip() for t in io.open(args.manifest, encoding="utf-8") if t.strip()]
    if not titles:
        print("nothing to fetch: pass --manifest, --title, or --list")
        return 1
    if not args.out:
        print("--out is required (write the corpus OUTSIDE the repo)")
        return 1

    got = fetch_batched(titles)
    missing = [t for t in titles if t not in got]

    # Trap 1: re-fetch anything that came back stub-sized through the renderer.
    stubs = [t for t, text in got.items() if len(text.split()) < STUB_WORDS]
    for i, title in enumerate(stubs + missing):
        try:
            text = fetch_rendered(title)
        except Exception as exc:
            print("  skip %s (%s)" % (title, type(exc).__name__))
            continue
        if text and len(text.split()) >= STUB_WORDS:
            got[title] = text
        if i + 1 < len(stubs) + len(missing):
            time.sleep(DELAY)

    kept = {t: x for t, x in got.items() if len(x.split()) >= STUB_WORDS}
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        for title in sorted(kept):
            fh.write(json.dumps({"title": title, "text": kept[title],
                                 "source_url": "https://en.wikisource.org/wiki/"
                                               + urllib.parse.quote(title.replace(" ", "_")),
                                 "note": "Public domain, fetched from Wikisource."},
                                ensure_ascii=False) + "\n")

    words = sum(len(x.split()) for x in kept.values())
    print("%d of %d page(s) kept, %d words -> %s"
          % (len(kept), len(titles), words, args.out))
    if len(stubs):
        print("  %d page(s) arrived as transclusion stubs and were re-fetched rendered"
              % len(stubs))
    dropped = [t for t in titles if t not in kept]
    if dropped:
        print("  %d page(s) yielded nothing usable: %s%s"
              % (len(dropped), ", ".join(dropped[:4]),
                 " ..." if len(dropped) > 4 else ""))
    if args.report:
        for title in sorted(kept):
            print("  %7d  %s" % (len(kept[title].split()), title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
