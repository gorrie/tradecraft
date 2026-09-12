#!/usr/bin/env python3
"""Apply `textnorm.clean` to corpora already on disk. Deterministic, in place, reversible.

The three fetchers now normalise on the way in (2026-09-05), but they all skip ids they
already hold, so no re-fetch can retrofit what is already stored. Unlike the truncation
repair, this needs no network and cannot change corpus membership: it is a pure function of
the text each record already carries. Same documents, same order, same count -- markup out.

    python corpus/repair_markup.py            # report what would change, touch nothing
    python corpus/repair_markup.py --apply    # rewrite, after writing a .pre-markup backup

WHAT IT WILL NOT DO
-------------------
Refuses to write when cleaning would empty a record or drop more than `--max-loss` of its
words. A normaliser that eats a document is indistinguishable from a fetch failure once it
has been written, and this repo has already shipped one silent EOF truncation from a
"cleanup" regex.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import textnorm  # noqa: E402

TEXT_FIELDS = ("text", "body", "comment", "content")


def field_of(rec):
    for f in TEXT_FIELDS:
        if isinstance(rec.get(f), str) and rec[f]:
            return f
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-loss", type=float, default=0.25,
                    help="refuse if any record loses more than this fraction of its words")
    ap.add_argument("--glob", default="*.jsonl")
    args = ap.parse_args(argv)

    rc = 0
    for path in sorted(glob.glob(os.path.join(HERE, args.glob))):
        rows = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
        changed, worst, worst_id, out = 0, 0.0, "", []
        for rec in rows:
            f = field_of(rec)
            if not f:
                out.append(rec)
                continue
            before = rec[f]
            after = textnorm.clean(before)
            if after != before:
                changed += 1
                bw, aw = len(before.split()), len(after.split())
                loss = 0.0 if not bw else max(0.0, (bw - aw) / float(bw))
                if loss > worst:
                    worst, worst_id = loss, str(rec.get("id") or f)
                rec = dict(rec, **{f: after})
            out.append(rec)

        name = os.path.basename(path)
        if not changed:
            print("%-40s clean" % name)
            continue
        print("%-40s %d of %d record(s) carry markup; worst word loss %.1f%% (%s)"
              % (name, changed, len(rows), worst * 100, worst_id))
        if worst > args.max_loss:
            print("   REFUSING: %.1f%% exceeds --max-loss %.0f%%. Cleaning that removes a "
                  "quarter of a document is a parser bug, not a repair." % (worst * 100,
                                                                            args.max_loss * 100))
            rc = 1
            continue
        if not args.apply:
            continue
        backup = path + ".pre-markup"
        if not os.path.exists(backup):
            shutil.copyfile(path, backup)
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            for rec in out:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("   rewritten (%d rows); previous file kept at %s" % (len(out),
                                                                    os.path.basename(backup)))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
