#!/usr/bin/env python3
"""CP3's acquisition pattern: a committed manifest of public URLs, a fetcher, and a hash lock.

WHY THIS SHAPE AND NOT ANOTHER
------------------------------
A floor measured over a corpus a reader cannot rebuild is internal calibration, not a public
statistic. That is not a stylistic preference here -- `eval/floors_contract.py` carries a
`recomputable` flag and public surfaces print an MDE only when it is true, which today is
false for every lens index floor because most of the background corpus is vendored text with
no provenance.

Two lawful patterns already exist in this workspace and this is the general form of the first:

  fetcher-manifest   a committed list of stable public URLs plus a fetcher. The TEXT never
                     enters git; the manifest and the hashes do. A reader rebuilds the exact
                     document set and reruns the measurement. Precedent:
                     bias-study/scripts/fetch_items.py, where the 62 propositions are never in
                     the repo and the reader verifies by hash that they fetched the same ones.
  local-staging      author-supplied material measured locally, never redistributed. Real, but
                     NOT publicly recomputable, so anything measured that way ships as
                     receipts-only. Precedent: tools/harvest_tells.py.

THE HASH IS THE POINT
---------------------
`--fetch` writes a lock file recording, per item, the sha256 of the NORMALISED extracted text
and the date it was fetched. `--verify` re-fetches and compares. A match proves a reader holds
the same corpus this project measured. A mismatch is not a bug to smooth over: the source
changed, that item's contribution to any floor is no longer reproducible, and the honest
response is to say so per item rather than to re-lock silently.

Normalised text rather than raw bytes, deliberately: a site reflowing its markup should not
invalidate a corpus, while an edit to the prose should. That trade is stated because it is a
trade -- a markup-only change that alters extraction WILL show as drift, and correctly.

FETCH DISCIPLINE, the project's standing rules
----------------------------------------------
Serial, one request at a time. 2s between requests. Descriptive User-Agent with a contact
address. A hard cap. Stops on failure rather than retrying in a loop. Honours 429 by backing
off, not by hammering. Attachment-only or non-text responses are skipped and counted, never
half-parsed.

    python corpus/fetch_manifest.py --init ~/manifests/advocacy.jsonl      # template
    python corpus/fetch_manifest.py --manifest ~/manifests/advocacy.jsonl \\
        --out ~/corpora/advocacy.jsonl                                     # fetch + lock
    python corpus/fetch_manifest.py --manifest ~/manifests/advocacy.jsonl --verify
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Descriptive, contactable UA naming the public mirror. Sent on every outbound request, so it
# must not carry a private repo or a personal address.
UA = ("tradecraft-corpus/1.0 (research corpus build; "
      "contact: https://github.com/gorrie/tradecraft)")
DELAY = 2.0
CAP = 200
TIMEOUT = 45

#: A response shorter than this, after extraction, is a redirect stub, a paywall notice or a
#: cookie wall -- not a document. Skipped and counted rather than measured.
MIN_WORDS = 120

TEMPLATE = [
    {"id": "example-1",
     "url": "https://example.org/a-stable-public-page",
     "camp": "which camp's canon this belongs to",
     "note": "why this is primary material and not a critic's summary of it"},
]


def normalise_text(raw, content_type=""):
    """Extract prose. Blunt on purpose: this feeds n-gram counting and cue matching."""
    text = raw
    if "html" in (content_type or "").lower() or re.search(r"(?i)<html|<body|<div", text[:2000]):
        text = re.sub(r"(?is)<(script|style|nav|header|footer|aside|form)\b.*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_one(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        ctype = resp.headers.get("Content-Type", "")
        if not any(t in ctype.lower() for t in ("text/", "html", "xml", "json", "plain")):
            return None, ctype        # a PDF or binary: skipped and counted, never half-read
        charset = "utf-8"
        m = re.search(r"charset=([\w-]+)", ctype, re.IGNORECASE)
        if m:
            charset = m.group(1)
        raw = resp.read().decode(charset, errors="replace")
    return normalise_text(raw, ctype), ctype


def load_manifest(path):
    out = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(json.loads(line))
    return out


def lock_path(manifest):
    return os.path.splitext(manifest)[0] + ".lock.json"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--init", metavar="PATH", help="write a template manifest and stop")
    ap.add_argument("--manifest", help="JSONL of {id, url, camp, note} -- COMMIT this")
    ap.add_argument("--out", help="corpus JSONL destination -- keep it OUTSIDE the repo")
    ap.add_argument("--verify", action="store_true",
                    help="re-fetch and compare hashes against the lock file")
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--delay", type=float, default=DELAY)
    args = ap.parse_args(argv)

    if args.init:
        with io.open(args.init, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Fetcher manifest. COMMIT this file; never commit the fetched text.\n")
            fh.write("# One JSON object per line. Prefer a stable, citable URL over a "
                     "convenience mirror.\n")
            for row in TEMPLATE:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print("wrote template manifest -> %s" % args.init)
        return 0

    if not args.manifest:
        print("--manifest is required (or --init to start one)")
        return 1
    items = load_manifest(args.manifest)
    if not items:
        print("manifest is empty: %s" % args.manifest)
        return 1
    if len(items) > args.cap:
        print("manifest has %d item(s), over the %d cap. Raise --cap deliberately."
              % (len(items), args.cap))
        return 1

    lock_file = lock_path(args.manifest)
    lock = {}
    if os.path.exists(lock_file):
        try:
            lock = json.load(io.open(lock_file, encoding="utf-8")).get("items", {})
        except ValueError:
            lock = {}

    if args.verify:
        if not lock:
            print("no lock file at %s -- run a fetch first" % lock_file)
            return 1
        same = drift = gone = 0
        for i, item in enumerate(items):
            iid = item["id"]
            recorded = lock.get(iid)
            if not recorded:
                print("  %-28s NOT IN LOCK" % iid[:28])
                continue
            try:
                text, _ = fetch_one(item["url"])
            except (urllib.error.URLError, OSError, ValueError) as exc:
                gone += 1
                print("  %-28s UNREACHABLE (%s)" % (iid[:28], type(exc).__name__))
                text = None
            if text:
                if content_hash(text) == recorded.get("sha256"):
                    same += 1
                else:
                    drift += 1
                    print("  %-28s DRIFTED since %s" % (iid[:28], recorded.get("fetched")))
            if i + 1 < len(items):
                time.sleep(args.delay)
        print("")
        print("verify: %d identical, %d drifted, %d unreachable, of %d item(s)"
              % (same, drift, gone, len(items)))
        if drift or gone:
            print("A drifted or unreachable item is no longer reproducible from this manifest.")
            print("Any floor computed over it stops being publicly recomputable -- say so "
                  "rather than re-locking.")
            return 1
        print("Every item still fetches to the text this corpus was measured over.")
        return 0

    if not args.out:
        print("--out is required. Write the corpus OUTSIDE the repo: the manifest and the")
        print("hashes are what get committed, never the third-party text.")
        return 1

    kept = skipped = failed = 0
    new_lock = {}
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        for i, item in enumerate(items):
            iid, url = item["id"], item["url"]
            try:
                text, ctype = fetch_one(url)
            except urllib.error.HTTPError as exc:
                # 429 is the one to respect rather than retry through.
                print("  %-28s HTTP %s -- stopping rather than hammering"
                      % (iid[:28], exc.code))
                failed += 1
                break
            except (urllib.error.URLError, OSError, ValueError) as exc:
                print("  %-28s %s -- stopping" % (iid[:28], type(exc).__name__))
                failed += 1
                break
            if text is None:
                skipped += 1
                print("  %-28s skipped (non-text: %s)" % (iid[:28], ctype[:40]))
            elif len(text.split()) < MIN_WORDS:
                skipped += 1
                print("  %-28s skipped (%d words -- stub or wall)"
                      % (iid[:28], len(text.split())))
            else:
                digest = content_hash(text)
                fh.write(json.dumps({
                    "id": iid, "title": item.get("title") or iid, "text": text,
                    "source_url": url, "camp": item.get("camp"),
                    "note": item.get("note"),
                    "sha256": digest,
                }, ensure_ascii=False) + "\n")
                new_lock[iid] = {"sha256": digest, "url": url,
                                 "words": len(text.split()),
                                 "fetched": time.strftime("%Y-%m-%d")}
                kept += 1
            if i + 1 < len(items):
                time.sleep(args.delay)

    with io.open(lock_file, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"_note": ("Per-item content hashes for a fetcher-manifest corpus. COMMIT "
                             "this; it is what lets a reader prove they fetched the same text "
                             "this project measured. Never commit the text itself."),
                   "manifest": os.path.basename(args.manifest),
                   "items": {**lock, **new_lock}}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("")
    print("kept %d, skipped %d, failed %d of %d item(s)"
          % (kept, skipped, failed, len(items)))
    print("corpus -> %s   (outside the repo, by design)" % args.out)
    print("lock   -> %s   (COMMIT this alongside the manifest)" % lock_file)
    print("")
    print("Adding this corpus to corpus/ requires a role entry in "
          "eval/background_rate.py ROLES;")
    print("an undeclared corpus file is a hard error there, so the decision gets written down.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
