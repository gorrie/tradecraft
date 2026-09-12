"""Enumerate every document in corpus/, whatever file it happens to live in.

WHY THIS EXISTS
---------------
2026-09-01. `corpus/fetch_govinfo.py` fetched 18 congressional hearings and wrote them to
`corpus/advocacy-specimens.jsonl` -- the advocacy prose the rhetorical lenses were written for
and had never been shown. Nothing read it. `eval/lens_floor.py` globbed `corpus/**/*.txt` and
`tools/harvest_gold.py` globbed the same plus one hardcoded JSONL filename, so the corpus that
took an API key to obtain was invisible to both tools that needed it.

That is the same shape as the defect this repository keeps finding in itself: a tool blind to
one input is blind to others. `lens_floor.py` was blind to `method-specimens.jsonl` too, and
had been since it was written -- it measured floors over the Federal Register cache alone and
reported "no floor measurable" for lenses whose material was sitting in a JSONL beside it.

So enumeration lives HERE, once. A new corpus file becomes visible to every consumer the
moment it lands, because no consumer knows what the files are called.

WHAT COUNTS AS A DOCUMENT
-------------------------
Any `.txt` under corpus/, and any record in any `*.jsonl` under corpus/ that carries text.
Nothing here reads labels: a document is text with a provenance, and what it is an example
OF is a human's call downstream. Records with no text are skipped rather than yielded empty.
"""
from __future__ import annotations

import glob
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "corpus")


class Doc(object):
    """One corpus document. `name` is stable and human-readable; it goes in results."""

    __slots__ = ("name", "text", "source_url", "origin")

    def __init__(self, name, text, source_url=None, origin=None):
        self.name = name
        self.text = text
        self.source_url = source_url
        self.origin = origin

    def __iter__(self):
        # So existing `for name, text in docs` call sites keep working.
        return iter((self.name, self.text))

    def __repr__(self):
        return "Doc(%r, %d words)" % (self.name, len(self.text.split()))


def _text_files():
    pattern = os.path.join(CORPUS, "**", "*.txt")
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            text = io.open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rel = os.path.relpath(path, ROOT)
        yield Doc(rel, text, None, rel)


def _jsonl_records():
    pattern = os.path.join(CORPUS, "**", "*.jsonl")
    for path in sorted(glob.glob(pattern, recursive=True)):
        rel = os.path.relpath(path, ROOT)
        try:
            handle = io.open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    # A malformed line is a corpus defect worth seeing, not worth crashing
                    # every consumer over. It shows up as a missing document.
                    continue
                text = rec.get("text") or ""
                if not text.strip():
                    continue
                name = rec.get("title") or rec.get("id") or rel
                yield Doc(name, text, rec.get("source_url"), rel)


def documents(limit=None, min_words=0):
    """Every corpus document, text files first, then JSONL records, both sorted by path.

    `min_words` drops fragments too short to perturb or to quote; callers that measure
    something over a document generally want it, callers that search do not.
    """
    out = []
    for doc in _text_files():
        if len(doc.text.split()) >= min_words:
            out.append(doc)
    for doc in _jsonl_records():
        if len(doc.text.split()) >= min_words:
            out.append(doc)
    if limit is not None:
        return out[:limit]
    return out


def spread(docs, limit):
    """Take `limit` documents round-robin across their origin files, not off the front.

    A plain head-slice is a trap here. Enumeration is path-ordered, so the 115 Federal
    Register text files come first and `--docs 40` never reached a single JSONL record --
    the cap silently decided that the floor would be measured over regulatory prose alone,
    which is the register these lenses are known NOT to fire on. Round-robin means a cap
    costs depth in every corpus rather than the existence of most of them.
    """
    if limit is None or limit >= len(docs):
        return list(docs)
    buckets = {}
    order = []
    for doc in docs:
        key = doc.origin
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(doc)
    out = []
    i = 0
    while len(out) < limit:
        took = False
        for key in order:
            if i < len(buckets[key]):
                out.append(buckets[key][i])
                took = True
                if len(out) == limit:
                    break
        if not took:                      # pragma: no cover - unreachable via the early return
            # Only reachable if the caller asked for more documents than exist, which the
            # `limit >= len(docs)` return at the top of this function already handles. Kept
            # because a future caller could reach it; excluded from coverage because today
            # nothing can, and a test that reached it would have to lie about the API.
            break
        i += 1
    return out


def inventory():
    """Per-file document counts, for reporting what a measurement actually ran over."""
    counts = {}
    for doc in documents():
        counts[doc.origin] = counts.get(doc.origin, 0) + 1
    return counts


if __name__ == "__main__":
    total = 0
    for origin, n in sorted(inventory().items()):
        print("%6d  %s" % (n, origin))
        total += n
    print("%6d  TOTAL" % total)
