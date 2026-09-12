#!/usr/bin/env python3
"""A reader-recomputable background pool: Wikinews articles, pinned to revision ids.

WHAT THIS REPLACES AND WHY IT MATTERS
-------------------------------------
`corpus/_news-control/` holds 95 vendored .txt files of news wire copy. It is 95 of the 171
documents behind every background firing rate in `eval/background_rate.py`, and its ROLES
entry has said `recomputable: False` since the day it was written, for the honest reason that
there is no manifest and no fetcher: the files have no URLs, no dates, no publisher, and one
of them still carries a truncated `","` where a CSV parser broke a quotation.

That single flag is what keeps the index MDEs unpublishable. A detection rate measured against
a background pool a reader cannot rebuild is a number they have to take on trust, and this
project's whole argument is that such numbers rot.

**THIS DOES NOT REPLACE THAT BUCKET, and an earlier version of this paragraph said it did** --
"Replacing the bucket removes the last non-recomputable input" -- while the ROLES entry and the
results file said the opposite in the same commit. The pool built here is 49k words against
302k, and it differs in content as well as unit: `reference_capture` fires 8.4% in
`_news-control` and 0% here at either chunk size. Swapping would move every background rate
while confounding packaging with content.

Worse, pooling them would LOOSEN the null. These articles run ~300 words against 3,200-word
chunks, and a per-document firing rate falls with length, so adding them drops the
recomputable-only background and makes every lens easier to claim above it -- no detector
changed, no subject changed, just a shorter denominator. `background_rate.ROLES` therefore does
not declare this manifest at all, and says why. What this file is for is a corpus that CAN be
rebuilt by a reader; making it comparable to the bucket it stands beside needs a
length-invariant rate unit first.

WHY WIKINEWS AND NOT A NEWS API
-------------------------------
Three properties, all required:

  1. **News register.** A background pool for a prose lens has to be the same KIND of writing
     the lens reads, or the rate measures genre rather than accident. Public-domain literature
     is the wrong register; Federal Register notices are already the other background bucket
     and would make the pool monolithic.
  2. **Fetchable by a reader, with no key.** Every commercial news API gates behind an
     account, which makes "recomputable" mean "recomputable if you pay".
  3. **Redistributable, and pinned.** Wikinews is CC-BY 2.5. And the MediaWiki API returns
     revision ids, so the manifest pins a REVISION rather than a title -- a wiki page changes
     under you, and a pool that rebuilds to the same titles but different text is not
     recomputable, it is approximately recomputable, which is a different claim.

SELECTION MUST NOT TOUCH A LENS CUE
-----------------------------------
This is the property that makes the pool a background pool rather than a fixture. Documents
are drawn from Wikinews' own dated archive categories -- every article published in a given
month -- and never from a topic search. If the pool were assembled by searching for
"surveillance" or "oversight" or any lens term, the resulting rate would measure how often the
lens fires on text selected for containing its own cues, which is not a background rate and is
the exact defect `background_rate.ROLES` exists to keep out of the corpus.

`--category` accepts only a dated archive by default; passing a topical one requires
`--allow-topical`, which stamps the manifest so the choice is visible downstream rather than
inferred.

    # 1. build a manifest: titles + pinned revision ids. COMMIT THIS.
    python corpus/fetch_wikinews.py --month 2024/January --out corpus/news-control.manifest.jsonl

    # 2. fetch the text a reader would fetch, into an UNCOMMITTED corpus file
    python corpus/fetch_wikinews.py --manifest corpus/news-control.manifest.jsonl \\
        --fetch ~/corpora/news-control.jsonl

    # 3. verify a rebuild matches, byte for byte, by content hash
    python corpus/fetch_wikinews.py --manifest corpus/news-control.manifest.jsonl --verify

The manifest is committed and the text is not, which is the same split
`corpus/fetch_manifest.py` uses: the repository carries the recipe and the hashes, the reader
builds the corpus. That is what `recomputable: True` is allowed to mean.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mediawiki as MW  # noqa: E402

#: Wikinews dated archives, as the wiki actually names them: "March 2014" (a month, whose
#: members are day subcategories) or "March 6, 2014" (a day, whose members are articles).
#: Anything else is topical and needs --allow-topical. The first draft of this pattern was
#: "2024/January", which matches nothing on Wikinews and produced "no articles in Category:
#: 2024/January" -- a message that reads like an empty month rather than a wrong guess.
_DATED = re.compile(r"^[A-Z][a-z]+ (?:\d{1,2}, )?\d{4}$")

#: A Wikinews article shorter than this is a stub, a redirect leftover, or a deletion notice.
#: Background rates are per-document, so a pool padded with 40-word fragments understates the
#: rate by inflating the denominator with text too short to fire on.
MIN_WORDS = 120

#: DELETED, not tuned. There were two boilerplate patterns here:
#:     r"(?i)\bhave an opinion on this story\b.*"
#:     r"(?i)\bthis (?:article|page) (?:is|has been) (?:a )?(?:stub|archived)\b.*"
#: plus a third, `r"^\s*\{\{.*?\}\}"`, that was dead on arrival because strip_templates has
#: already run by then.
#:
#: Both live ones ran AFTER MW.plain() collapsed the article to a single line, so `.*` reached
#: the END OF THE DOCUMENT. Measured: "First para. A spokesman said this article has been
#: archived by the museum, and the rest of the story continues..." came out as "First para. A
#: spokesman said." A silent truncation to EOF, well-formed, no error -- the exact signature
#: tools/truncation_scan.py exists to find, sitting inside the tool built to replace a
#: truncated corpus.
#:
#: The first repair attempt bounded them with `[^.]{0,80}\.` and STILL ate 80 characters of
#: real prose on that same input, because the boilerplate wording is not distinguishable from
#: a sentence quoting it. So the question became whether they were needed at all: measured
#: across all 94 fetched articles, with `_TAIL` and template stripping in place, **each
#: pattern matches zero documents.** They were dead code whose only live effect was the
#: truncation risk. Wikinews' real boilerplate lives in templates and in the tail sections,
#: both already removed.
#:
#: If a future fetch does surface boilerplate, add a pattern anchored to a line start on the
#: RAW wikitext, before plain() flattens it -- never an unbounded `.*` on flattened text.
_BOILER = ()


#: `{{w|Kunming}}` and `{{w|Ministry of Public Security of the PRC|Ministry of Public Security}}`
#: are how Wikinews links to Wikipedia, and the linked text IS the article's prose. The shared
#: stripper removes templates whole, which deleted them: the first fetch produced "attacked a
#: train station in , China yesterday" -- a hole where the place name was, in 95 of 95
#: documents. Proper nouns are precisely what these templates carry, so the damage lands on the
#: words a prose lens is most likely to key on, and the corpus would have looked fine at a
#: glance while being systematically missing its subjects.
_WIKI_LINK_TEMPLATE = re.compile(r"\{\{\s*[wW]\s*\|([^{}]*?)\}\}")

#: Image and media markup, whose CAPTION is not article prose. `[[File:x.jpg|thumb|left|Daniel
#: Ricciardo, pictured here in 2011...]]` came through as "thumb left Daniel Ricciardo,
#: pictured here in 2011..." -- layout directives and a caption spliced into the body.
#:
#: Bracket-BALANCED rather than pattern-matched, because a caption routinely contains its own
#: wikilink ("A file photo of [[Ardlui railway station]], showing...") and a regex that stops
#: at the first `]]` leaves the rest of the caption in the body. A first version did exactly
#: that and left `thumb|left|A file photo of Ardlui railway station, showing a typical...` in
#: 6 of 95 documents -- few enough to miss by sampling, which is why this is counted.
_MEDIA_OPEN = re.compile(r"(?is)\[\[\s*(?:File|Image|Media)\s*:")

#: `[[Category:X]]` links. Wikinews puts five to ten at the foot of every article, and the
#: shared stripper turns them into the bare words "Category:China Category:Asia
#: Category:Crime and law" -- present in 95 of 95 documents, so every background document
#: carried a tail of topic labels. Those labels are the closest thing in the file to a
#: TOPIC ANNOTATION, which is exactly what a background pool must not be selected or scored on.
_CATEGORY_LINK = re.compile(r"(?is)\[\[\s*Category\s*:[^\]]*\]\]")

#: Where a Wikinews article stops being prose. Everything from the first of these headings is
#: apparatus: a source list, related-article links, licence boilerplate.
#:
#: `notes?` was in this list and is now NOT. A "== Notes ==" section appears MID-ARTICLE in
#: Wikinews, so with DOTALL to end-of-string it discarded the body after it:
#: "Body text. == Notes == a footnote. More body prose. == Sources == ..." became
#: "Body text." Only the genuinely terminal apparatus headings belong here, and this is applied
#: to the RAW wikitext where headings are still on their own lines -- if it ever moves after
#: MW.plain(), which flattens to one line, the anchor stops meaning what it says.
_TAIL = re.compile(r"(?is)\n==+\s*(?:sources?|related news|external links?|"
                   r"references?|see also)\s*==+.*$")


def drop_media(text):
    """Remove [[File:...]] / [[Image:...]] / [[Media:...]] with balanced brackets.

    UNBALANCED MARKUP MUST NOT SWALLOW THE ARTICLE. The first version ran its depth counter to
    end-of-string whenever the closing `]]` never arrived, so one typo'd caption deleted
    everything after it: `Intro prose. [[File:x.jpg|thumb|a caption with [[a link] typo]] and
    then the real body continues...` came out as `Intro prose.` -- 112 characters to 14. That
    is the same silent EOF truncation this file was rewritten to remove, reintroduced by the
    balanced-bracket rewrite that removed it.

    `strip_templates` in mediawiki.py already had the answer and this did not: when the braces
    do not balance, fall back to the conservative reading rather than the destructive one. Here
    that means dropping only up to the first `]]` -- wrong in a small way (a caption fragment
    survives) instead of catastrophic in a large one (the article does not).
    """
    out, pos = [], 0
    for m in _MEDIA_OPEN.finditer(text):
        if m.start() < pos:
            continue
        i, depth = m.end(), 1
        while i < len(text) and depth:
            if text.startswith("[[", i):
                depth += 1
                i += 2
            elif text.startswith("]]", i):
                depth -= 1
                i += 2
            else:
                i += 1
        if depth:
            # Never closed. Take the first `]]` after the opener if there is one at all, and
            # otherwise drop nothing -- leaving markup in the text is a visible defect a
            # reader can spot, while deleting the body is one nobody can.
            close = text.find("]]", m.end())
            if close < 0:
                continue
            i = close + 2
        out.append(text[pos:m.start()])
        pos = i
    out.append(text[pos:])
    return " ".join(out)


def unwrap_wiki_links(text):
    """`{{w|target|display}}` -> display, `{{w|target}}` -> target. Repeated until stable.

    Repeated because these nest inside each other in a handful of articles, and one pass
    leaves the inner one as literal braces for the generic stripper to eat along with its word.
    """
    prev = None
    while prev != text:
        prev = text
        text = _WIKI_LINK_TEMPLATE.sub(lambda m: m.group(1).split("|")[-1], text)
    return text


def clean(text):
    """Wikinews wikitext to prose, in the order the damage requires.

    Tail first, then category links, then media (its caption goes with it), then the
    Wikipedia-link templates unwrapped
    (their text must be KEPT), then the shared stripper, then boilerplate. Reordering these
    breaks them: unwrap before dropping media and a `{{w|...}}` inside a caption survives into
    the body; strip templates before unwrapping and the link text is already gone.
    """
    out = _TAIL.sub(" ", text or "")
    out = _CATEGORY_LINK.sub(" ", out)
    out = drop_media(out)
    out = unwrap_wiki_links(out)
    out = MW.plain(out, MW._DROP_CLASSES + MW.SITE_DROP_CLASSES["wikinews"])
    for pat in _BOILER:
        out = pat.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


def content_hash(text):
    """SHA-256 of the normalised text. The lock, so a rebuild is checkable rather than hoped."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_manifest(category, cap, allow_topical):
    if not _DATED.match(category) and not allow_topical:
        raise SystemExit(
            "refusing to build a background pool from the topical category %r.\n"
            "A background rate measured on documents selected by topic is not a background\n"
            "rate. Pass --allow-topical if you mean it; the manifest will record that it is\n"
            "topical so nothing downstream treats it as accidental." % category)
    MW.use_site("wikinews")
    titles = MW.list_category_tree(category, limit=cap * 3)
    if not titles:
        raise SystemExit("no articles in Category:%s" % category)
    revs = MW.revisions(titles)
    records = []
    for title in titles:
        rec = revs.get(title)
        if not rec:
            continue
        records.append({"id": "wikinews:%d" % rec["revid"],
                        "title": title,
                        "revid": rec["revid"],
                        "timestamp": rec.get("timestamp"),
                        "category": category,
                        "topical": not _DATED.match(category),
                        "url": "https://en.wikinews.org/w/index.php?oldid=%d" % rec["revid"],
                        "licence": "CC-BY-2.5",
                        "role": "background"})
    return records[:cap]


def fetch_texts(records, cap=None):
    """Text for each pinned revision, with its content hash. Serial, delayed, identified."""
    MW.use_site("wikinews")
    out, short = [], 0
    for i, rec in enumerate(records if cap is None else records[:cap]):
        raw = MW.fetch_by_revid(rec["revid"], raw=True)
        if raw is None:
            continue
        text = clean(raw)
        if len(text.split()) < MIN_WORDS:
            short += 1
            continue
        out.append(dict(rec, text=text, sha256=content_hash(text),
                        words=len(text.split())))
        if i % 10 == 9:
            print("  %d/%d" % (i + 1, len(records)), file=sys.stderr)
    return out, short


def load_jsonl(path):
    return [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]


def write_jsonl(path, records):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    # Repeatable. Wikinews' output per month varies by an order of magnitude across its life
    # (2014 runs ~45/month, 2022 nearer 5), so a pool of a given size spans however many
    # months it takes. Naming them explicitly beats a "most recent N articles" selector: the
    # months are in the manifest, so the pool's date range is a stated fact rather than
    # whatever the archive happened to hold on the day it was built.
    ap.add_argument("--month", action="append", default=[],
                    help="dated archive as Wikinews names it, e.g. \"March 2014\"; repeatable")
    ap.add_argument("--category", help="any category (topical needs --allow-topical)")
    ap.add_argument("--allow-topical", action="store_true",
                    help="permit a topic-selected pool, recorded as topical in the manifest")
    ap.add_argument("--cap", type=int, default=120, help="manifest size cap")
    ap.add_argument("--out", help="manifest destination -- COMMIT this file")
    ap.add_argument("--manifest", help="an existing manifest to fetch or verify")
    ap.add_argument("--fetch", metavar="PATH",
                    help="fetch text for a manifest into PATH (keep it OUT of the repo)")
    ap.add_argument("--lock", metavar="CORPUS",
                    help="write the content hashes from CORPUS back into the manifest")
    ap.add_argument("--verify", action="store_true",
                    help="re-fetch and compare content hashes against the manifest")
    ap.add_argument("--verify-limit", type=int, default=25,
                    help="how many records --verify re-fetches (all of them is slow and rude)")
    args = ap.parse_args(argv)

    categories = list(args.month) + ([args.category] if args.category else [])

    if categories:
        if not args.out:
            raise SystemExit("--out is required when building a manifest")
        records, seen = [], set()
        for cat in categories:
            got = build_manifest(cat, args.cap, args.allow_topical)
            # Deduplicate on revision id across categories. An article dated near a month
            # boundary carries both months' day categories, and counting it twice would put
            # the same document in the background pool twice -- inflating the denominator with
            # a document that is not an independent observation.
            fresh = [r for r in got if r["id"] not in seen]
            seen.update(r["id"] for r in fresh)
            records += fresh
            print("  Category:%-18s %3d new record(s)" % (cat, len(fresh)))
            if len(records) >= args.cap:
                break
        records = records[:args.cap]
        write_jsonl(args.out, records)
        print("manifest: %d record(s) from %d categor%s -> %s"
              % (len(records), len(categories),
                 "y" if len(categories) == 1 else "ies", args.out))
        print("Each record pins a REVISION id, so a rebuild gets the same text or fails loudly.")
        print("Next: --fetch to build the corpus, then --lock to write the hashes back.")
        return 0

    if not args.manifest:
        ap.error("give --month/--category to build a manifest, or --manifest to use one")
    records = load_jsonl(args.manifest)

    if args.fetch:
        got, short = fetch_texts(records)
        write_jsonl(args.fetch, got)
        print("fetched %d of %d record(s) -> %s" % (len(got), len(records), args.fetch))
        if short:
            print("  %d skipped as under %d words (stubs, not background)" % (short, MIN_WORDS))
        print("  next: --lock %s, to put those hashes in the manifest" % args.fetch)
        return 0

    if args.lock:
        # The lock step is separate from the fetch on purpose. Writing hashes at fetch time
        # would mean the manifest always agrees with whatever was last downloaded, which makes
        # --verify a tautology: it would be comparing a fetch against itself. Locking is a
        # deliberate act that says "this text is the reference", and only then does a later
        # verify mean anything.
        corpus = {r["id"]: r for r in load_jsonl(args.lock)}
        locked, absent = 0, 0
        for rec in records:
            fresh = corpus.get(rec["id"])
            if not fresh:
                absent += 1
                continue
            rec["sha256"] = fresh["sha256"]
            rec["words"] = fresh.get("words")
            locked += 1
        write_jsonl(args.manifest, records)
        print("locked %d hash(es) into %s" % (locked, args.manifest))
        if absent:
            print("  %d manifest record(s) had no text in %s -- left unlocked, so --verify"
                  % (absent, args.lock))
            print("  will report them rather than passing over them")
        return 0

    if args.verify:
        sub = records[:args.verify_limit]
        got, _ = fetch_texts(sub)
        by_id = {r["id"]: r for r in got}
        missing, changed, ok = [], [], 0
        for rec in sub:
            fresh = by_id.get(rec["id"])
            if fresh is None:
                missing.append(rec["id"])
            elif rec.get("sha256") and fresh["sha256"] != rec["sha256"]:
                changed.append(rec["id"])
            else:
                ok += 1
        print("VERIFY %d record(s) of %d in the manifest" % (len(sub), len(records)))
        print("  %d reproduced, %d changed, %d unfetchable" % (ok, len(changed), len(missing)))
        if changed or missing:
            for i in changed:
                print("    CHANGED %s" % i)
            for i in missing:
                print("    MISSING %s" % i)
            print("  A pinned revision that no longer reproduces means the manifest is not a")
            print("  recipe. Do not relax the hash: re-pin deliberately and say why.")
            return 1
        if not any(r.get("sha256") for r in sub):
            print("  NO HASHES IN THE MANIFEST -- nothing was actually compared.")
            print("  This is a vacuous pass. Build the corpus with --fetch, then --lock.")
            return 1
        return 0

    ap.error("nothing to do: pass --fetch, --lock or --verify with --manifest")


if __name__ == "__main__":
    raise SystemExit(main())
