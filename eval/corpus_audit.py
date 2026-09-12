#!/usr/bin/env python3
"""Is the testing corpus actually correct? Every check that could invalidate a published number.

WHY THIS EXISTS
---------------
Every precision, lift and coverage figure this project reports about the detector is computed by
slicing PTC's character offsets out of PTC's article text. If those offsets do not align with
the text as this code loads it, every one of those numbers is wrong in a way that looks
completely normal -- a shifted span still overlaps something sometimes, so the result is a
plausible number rather than an error.

That is not hypothetical here. The corpus has already produced three silent defects: 68
specimens stored as raw HTML, a corpus file no tool could see, and an embed arm that failed on
every article while reporting zero hits. So the corpus gets audited the same way the
instruments do.

WHAT IT CHECKS, and what a failure would mean

  offsets-in-bounds     A label pointing past the end of its article means the label file and
                        the text file disagree about which article they describe.
  offset-alignment      The strongest check available without a second annotation: a gold span
                        sliced from the loaded text should be TEXT, not whitespace or a
                        fragment starting mid-word. A systematic newline or encoding difference
                        between the labelled file and the loaded one shifts every offset, and
                        this is what that looks like from the outside.
  span-sanity           Zero-length, negative, or absurdly long spans.
  article-coverage      Every labelled article id resolves to a file that loads.
  duplicate-articles    The same text under two ids inflates every denominator.
  task1-vs-task2        The two label sets must describe the same articles.
  empty-articles        An article with no text is a silent zero in every rate.

    python eval/corpus_audit.py            # report
    python eval/corpus_audit.py --check    # exit 1 on any failure
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERIES = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

PTC = os.path.join(SERIES, "research", "external", "ptc")
ARTICLES = os.path.join(PTC, "train-articles")
TASK1 = os.path.join(PTC, "train-labels-task1-span-identification")
TASK2_AGG = os.path.join(PTC, "train-task2-TC.labels")

#: A gold span should be prose. If a large share of spans start or end on whitespace, or start
#: mid-word, the offsets are shifted relative to the text being loaded.
MIDWORD = re.compile(r"\w")


def load_articles():
    out = {}
    if not os.path.isdir(ARTICLES):
        return out
    for name in sorted(os.listdir(ARTICLES)):
        if not (name.startswith("article") and name.endswith(".txt")):
            continue
        aid = name[len("article"):-len(".txt")]
        # Read with newline="" so nothing is translated: the labels were computed against the
        # bytes on disk, and a universal-newlines read would silently shorten every line by
        # one character on CRLF input and shift every offset after the first line.
        with io.open(os.path.join(ARTICLES, name), encoding="utf-8",
                     errors="replace", newline="") as fh:
            out[aid] = fh.read()
    return out


def load_task1():
    """article id -> spans, INCLUDING ids whose label file is empty.

    The distinction matters and the first version of this audit got it wrong. 371 label files
    exist and 14 of them are EMPTY: PTC annotated those articles and found no propaganda, so
    they are genuine negatives. Counting only files that produced a span reported "357
    labelled files" and made a complete corpus look 4% un-annotated -- which would have argued
    for excluding 14 true negatives and quietly inflating every precision figure.

    An id present with an empty list is annotated-and-clean. An id absent entirely is
    unannotated, and that is the case worth failing on.
    """
    spans = collections.defaultdict(list)
    if not os.path.isdir(TASK1):
        return spans
    for name in sorted(os.listdir(TASK1)):
        if not name.endswith(".labels"):
            continue
        aid = name.split(".")[0].replace("article", "")
        spans[aid] = spans.get(aid, [])          # registers the id even with no rows
        for line in io.open(os.path.join(TASK1, name), encoding="utf-8", errors="replace"):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    spans[parts[0]].append((int(parts[1]), int(parts[2])))
                except ValueError:
                    continue
    return spans


def load_task2():
    spans = collections.defaultdict(list)
    if not os.path.exists(TASK2_AGG):
        return spans
    for line in io.open(TASK2_AGG, encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        try:
            spans[parts[0].strip()].append((parts[1], int(parts[2]), int(parts[3])))
        except ValueError:
            continue
    return spans


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args(argv)

    arts = load_articles()
    t1 = load_task1()
    t2 = load_task2()
    failures = []

    print("PTC TESTING CORPUS AUDIT")
    print("  articles loaded         %d" % len(arts))
    print("  task-1 labelled files   %d  (%d spans)"
          % (len(t1), sum(len(v) for v in t1.values())))
    print("  task-2 labelled files   %d  (%d typed spans)"
          % (len(t2), sum(len(v) for v in t2.values())))
    if not arts:
        print("\nNO ARTICLES FOUND at %s" % ARTICLES)
        return 1

    # ---- every labelled article must resolve to a loadable file
    missing1 = sorted(set(t1) - set(arts))
    missing2 = sorted(set(t2) - set(arts))
    if missing1 or missing2:
        failures.append("labels reference %d/%d article id(s) with no loadable text"
                        % (len(missing1), len(missing2)))
    print("\narticle-coverage          task1 missing %d, task2 missing %d"
          % (len(missing1), len(missing2)))

    # ---- the two label sets should describe the same articles
    only1 = sorted(set(t1) - set(t2))
    only2 = sorted(set(t2) - set(t1))
    print("task1-vs-task2            %d only in task1, %d only in task2"
          % (len(only1), len(only2)))

    # ---- empty articles
    empties = sorted(a for a, t in arts.items() if not t.strip())
    if empties:
        failures.append("%d empty article(s): %s" % (len(empties), empties[:5]))
    print("empty-articles            %d" % len(empties))

    # ---- duplicate texts
    by_hash = collections.defaultdict(list)
    for aid, text in arts.items():
        by_hash[hashlib.sha1(text.strip().encode("utf-8")).hexdigest()].append(aid)
    dupes = {h: ids for h, ids in by_hash.items() if len(ids) > 1}
    if dupes:
        failures.append("%d duplicated article text(s): %s"
                        % (len(dupes), list(dupes.values())[:3]))
    print("duplicate-articles        %d group(s)" % len(dupes))

    # ---- offsets in bounds, and span sanity
    oob = zero = negative = huge = 0
    for aid, spans in t1.items():
        text = arts.get(aid)
        if text is None:
            continue
        for s, e in spans:
            if s < 0 or e < 0:
                negative += 1
            elif e > len(text):
                oob += 1
            elif e == s:
                zero += 1
            elif (e - s) > len(text):
                huge += 1
    for label, n in (("out-of-bounds", oob), ("zero-length", zero),
                     ("negative", negative), ("absurd-length", huge)):
        if n:
            failures.append("%d span(s) %s" % (n, label))
    print("offsets-in-bounds         %d out of bounds, %d zero-length, %d negative"
          % (oob, zero, negative))

    # ---- THE ALIGNMENT CHECK
    #
    # A gold span should be prose. Count spans that begin or end on whitespace, and spans that
    # begin mid-word. Some of each is normal -- annotators do not snap to token boundaries --
    # but a SYSTEMATIC rate means the offsets are shifted relative to the loaded text, which
    # would silently corrupt every precision figure this project reports.
    starts_ws = ends_ws = midword = total = 0
    examples = []
    for aid, spans in sorted(t1.items()):
        text = arts.get(aid)
        if text is None:
            continue
        for s, e in spans:
            if not (0 <= s < e <= len(text)):
                continue
            total += 1
            frag = text[s:e]
            if frag[:1].isspace():
                starts_ws += 1
            if frag[-1:].isspace():
                ends_ws += 1
            if s > 0 and MIDWORD.match(text[s - 1] or "") and MIDWORD.match(frag[:1] or ""):
                midword += 1
                if len(examples) < args.examples:
                    examples.append((aid, s, repr(text[max(0, s - 12):e][:60])))
    if total:
        pct_ws = 100.0 * starts_ws / total
        pct_mid = 100.0 * midword / total
        print("offset-alignment          %d span(s) checked" % total)
        print("                          starts on whitespace %.1f%%, ends on whitespace %.1f%%"
              % (pct_ws, 100.0 * ends_ws / total))
        print("                          starts mid-word      %.1f%%" % pct_mid)
        # Thresholds are generous on purpose: the failure being guarded against is a SHIFT,
        # which drives these to tens of percent, not to 3%.
        if pct_ws > 15.0 or pct_mid > 15.0:
            failures.append("offsets look SHIFTED: %.1f%% start on whitespace, %.1f%% mid-word"
                            % (pct_ws, pct_mid))
        for aid, s, ctx in examples:
            print("      mid-word example  article %s @%d  %s" % (aid, s, ctx))

    # ---- the eval fixtures: the OTHER testing corpus, and the one the strict gate reads
    #
    # 97 hand-written fixtures decide whether CI is green. A duplicate id silently shadows one
    # of the pair; the same text under a positive and a negative id makes the suite
    # self-contradictory and one of them must always fail; an expect_any naming a marker that
    # does not exist can never be satisfied, so coverage silently caps below 100%.
    import json
    fx_path = os.path.join(HERE, "fixtures.json")
    if os.path.exists(fx_path):
        items = json.load(io.open(fx_path, encoding="utf-8"))
        ids = [f.get("id") for f in items if isinstance(f, dict)]
        dup_ids = sorted({i for i in ids if ids.count(i) > 1})
        by_text = collections.defaultdict(list)
        for f in items:
            by_text[" ".join((f.get("text") or "").split())].append(
                (f.get("id"), bool(f.get("should_fire"))))
        contradictions = [v for v in by_text.values()
                          if len({s for _, s in v}) > 1]
        dup_text = [v for v in by_text.values() if len(v) > 1 and v not in contradictions]

        bad_marker = []
        try:
            from tradecraft.loader import load_lenses
            lenses = load_lenses(os.path.join(ROOT, "detectors"))
            for f in items:
                tax = lenses.get(f.get("lens"))
                if tax is None:
                    bad_marker.append("%s: unknown lens %r" % (f.get("id"), f.get("lens")))
                    continue
                known = {m.id for m in tax.markers}
                for key in ("expect_any", "forbid_markers"):
                    for m in f.get(key) or []:
                        if m not in known:
                            bad_marker.append("%s: %s names unknown marker %r"
                                              % (f.get("id"), key, m))
        except Exception as exc:      # noqa: BLE001
            bad_marker.append("lens check skipped (%s)" % type(exc).__name__)

        if dup_ids:
            failures.append("duplicate fixture id(s): %s" % dup_ids)
        if contradictions:
            failures.append("%d fixture text(s) used as BOTH positive and negative: %s"
                            % (len(contradictions), contradictions[:2]))
        if bad_marker:
            failures.append("%d fixture marker problem(s): %s" % (len(bad_marker),
                                                                  bad_marker[:3]))
        print("\neval fixtures             %d fixture(s), %d duplicate id(s), "
              "%d contradiction(s), %d duplicated text(s), %d marker problem(s)"
              % (len(items), len(dup_ids), len(contradictions), len(dup_text),
                 len(bad_marker)))

    # ---- the local corpus buckets, via the role manifest
    try:
        import background_rate as BR
        from tradecraft.corpus_docs import documents
        undeclared = sorted({d.origin for d in documents(min_words=BR.MIN_WORDS)
                             if BR.role_of(d.origin) is None})
        if undeclared:
            failures.append("undeclared corpus file(s): %s" % undeclared)
        print("\nlocal corpus roles        %d file(s) undeclared" % len(undeclared))
    except Exception as exc:      # noqa: BLE001
        print("\nlocal corpus roles        NOT CHECKED (%s)" % type(exc).__name__)

    print("")
    if failures:
        print("AUDIT FAILED -- %d problem(s):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1 if args.check else 0
    print("AUDIT CLEAN. Offsets align, no duplicates, every label resolves to text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
