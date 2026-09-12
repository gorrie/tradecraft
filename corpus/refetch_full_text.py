#!/usr/bin/env python3
"""Refetch the specimen corpora at full length, BY ID, keeping the same documents.

WHY NOT JUST RE-RUN THE FETCHERS
--------------------------------
`fetch_federal_register.py` and `fetch_govinfo.py` retrieve by SEARCH TERM. Re-running them
would return whatever those searches return today, so the corpus membership would change along
with the truncation -- and every measurement resting on these files would move for two reasons
at once, with no way to separate them. This project spent two days finding exactly that
confound in other people's work and its own.

So this refetches the documents ALREADY IN THE CORPUS, addressed by their own identifiers, at
full length. Same documents, same order, one thing different: how much of each one is kept.

WHAT IS WRONG WITH THE CURRENT FILES
------------------------------------
Measured by tools/truncation_scan.py:

    method-specimens.jsonl     84 of 155 documents are EXACTLY 6,000 characters
    advocacy-specimens.jsonl   15 of 18 are EXACTLY 30,000 characters

Both were cut by their fetcher's `--chars` default, on a character boundary, mid-word in at
least one case (`...%20DEA%20SAMHSA%20buprenorphine%20telemedi`). The fetchers were fixed on
2026-09-04 to cut on a word boundary and to record `truncated` / `truncated_at_chars` /
`full_words` -- but they skip ids they already hold, so no re-run can retrofit the existing
records. Only a refetch can, and only a by-id refetch can do it without changing the corpus.

    python corpus/refetch_full_text.py --plan            # what it would fetch, no network
    python corpus/refetch_full_text.py --run             # fetch into *.full.jsonl (resumable)
    python corpus/refetch_full_text.py --compare         # paired: what the cut cost
    python corpus/refetch_full_text.py --promote         # swap the full text in, once verified

Nothing is overwritten until `--promote`, and `--promote` refuses unless every id in the
original is present in the refetch. Serial, delayed, identified.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

UA = "tradecraft-research/1.0 (+https://github.com/gorrie/tradecraft)"
DELAY = 1.0

#: (corpus file, id prefix, what fetches it). Both are US government works, public domain.
TARGETS = {
    "method-specimens.jsonl": "fr_",
    "advocacy-specimens.jsonl": "gi_",
}

FR_API = "https://www.federalregister.gov/api/v1/documents/%s.json?fields[]=raw_text_url"
GOVINFO_HTM = "https://api.govinfo.gov/packages/%s/htm?api_key=%s"


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def govinfo_key():
    """The key lives outside the repo. Absent means say so, never fetch half a corpus."""
    for path in (os.environ.get("TRADECRAFT_ENV_FILE", ""),):
        if not os.path.exists(path):
            continue
        for line in io.open(path, encoding="utf-8"):
            if line.strip().startswith("GOVINFO_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return os.environ.get("GOVINFO_API_KEY", "")


def fetch_fr(doc_id):
    """Full raw text of one Federal Register document, by its document number."""
    number = doc_id[3:] if doc_id.startswith("fr_") else doc_id
    meta = json.loads(_get(FR_API % urllib.parse.quote(number)))
    url = meta.get("raw_text_url")
    if not url:
        return None
    return _get(url)


def fetch_gi(doc_id, key):
    """Full text of one govinfo package, by package id."""
    package = doc_id[3:] if doc_id.startswith("gi_") else doc_id
    if not key:
        raise SystemExit("GOVINFO_API_KEY not found (environment, or an env file named by TRADECRAFT_ENV_FILE)")
    import re
    html = _get(GOVINFO_HTM % (urllib.parse.quote(package), key), timeout=180)
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    body = re.sub(r"<[^>]+>", " ", body)
    return " ".join(body.split())


def load(path):
    return [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]


def out_path(name):
    return os.path.join(HERE, name.replace(".jsonl", ".full.jsonl"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--promote", action="store_true")
    ap.add_argument("--only", default="", help="one corpus file name")
    ap.add_argument("--allow-partial", action="store_true",
                    help="promote the refetched records and MARK the rest as still cut")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=DELAY)
    args = ap.parse_args(argv)

    names = [args.only] if args.only else sorted(TARGETS)
    key = govinfo_key()

    for name in names:
        src = os.path.join(HERE, name)
        if not os.path.exists(src):
            print("%s: not present" % name)
            continue
        recs = load(src)
        dst = out_path(name)
        have = {r["id"]: r for r in load(dst)} if os.path.exists(dst) else {}

        if args.plan or not (args.run or args.compare or args.promote):
            cut = sum(1 for r in recs if r.get("truncated") is not False
                      and len(r.get("text") or "") >= 5999)
            print("%s: %d record(s), %d already refetched, %d look cut"
                  % (name, len(recs), len(have), cut))
            continue

        if args.compare:
            rows = [(r["id"], len(r.get("text") or ""), len(have[r["id"]].get("text") or ""))
                    for r in recs if r["id"] in have]
            if not rows:
                print("%s: nothing refetched yet" % name)
                continue
            grew = sum(1 for _, a, b in rows if b > a)
            import statistics as st
            print("%s: %d compared, %d longer at full length" % (name, len(rows), grew))
            print("   median chars  %d -> %d" % (st.median([r[1] for r in rows]),
                                                 st.median([r[2] for r in rows])))
            print("   total  chars  %d -> %d" % (sum(r[1] for r in rows),
                                                 sum(r[2] for r in rows)))
            continue

        if args.promote:
            missing = [r["id"] for r in recs if r["id"] not in have]
            if missing and not args.allow_partial:
                print("%s: REFUSING to promote -- %d id(s) not refetched, e.g. %s"
                      % (name, len(missing), missing[:3]))
                print("   A partial promote would silently shorten the corpus. Pass")
                print("   --allow-partial to promote the rest and MARK these as still cut.")
                continue
            merged = []
            for r in recs:
                full = have.get(r["id"])
                if full is None:
                    # NOT SILENTLY LEFT ALONE. A record that could not be refetched keeps its
                    # truncated text and now SAYS SO, which is the whole point of the
                    # `truncated` field: the corpus describes itself instead of leaving a
                    # statistical test to reveal how it was built.
                    #
                    # These are Congressional RECORD issues. The corpus stored a granule's
                    # title against the package's id, and the package exposes no granules
                    # through the API (count 0), so there is no identifier that addresses the
                    # text actually held. Refetching by search would return whatever the search
                    # returns today and change WHICH documents are in the corpus -- the exact
                    # confound this tool exists to avoid. So they stay, declared.
                    merged.append(dict(r, truncated=True,
                                       truncated_at_chars=len(r.get("text") or ""),
                                       full_words=None,
                                       refetch_blocked="CREC package exposes no granules; the "
                                                       "stored id addresses an issue, not the "
                                                       "granule whose title is recorded"))
                    continue
                merged.append(dict(r, text=full["text"], truncated=False,
                                   truncated_at_chars=None,
                                   full_words=len((full["text"] or "").split()),
                                   refetched_at_full_length="2026-09-05"))
            with io.open(src, "w", encoding="utf-8", newline="\n") as fh:
                for r in merged:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("%s: promoted %d record(s) to full length" % (name, len(merged)))
            continue

        # --run
        todo = [r for r in recs if r["id"] not in have]
        n = 0
        for r in todo:
            if args.limit and n >= args.limit:
                break
            try:
                text = fetch_fr(r["id"]) if r["id"].startswith("fr_") else fetch_gi(r["id"], key)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
                print("   FAILED %s: %s -- left for a retry" % (r["id"], str(exc)[:70]))
                time.sleep(args.delay * 3)
                continue
            if not text or not text.strip():
                print("   EMPTY  %s -- not recorded" % r["id"])
                continue
            text = " ".join(text.split())
            with io.open(dst, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"id": r["id"], "text": text}, ensure_ascii=False) + "\n")
            n += 1
            print("   %-26s %7d -> %8d chars" % (r["id"], len(r.get("text") or ""), len(text)))
            time.sleep(args.delay)
        print("%s: refetched %d, %d remain" % (name, n, len(todo) - n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
