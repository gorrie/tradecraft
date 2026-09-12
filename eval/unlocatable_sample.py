#!/usr/bin/env python
"""Sample the LLM find stage's UNLOCATABLE spans for a hand-read.

WHY THIS EXISTS
---------------
`RESULTS-2026-09-07-llm-find-stage.md` closed on one owed measurement: 3,210 of 8,789 quoted
spans (36.5%) are text the model says it found in an article and that `str.find` cannot locate.
The results file's own ruling is that this number decides whether a fuzzy locator is a FIX or a
LAUNDERING STEP, and that the classification must happen **before** any locator is written --
otherwise the locator is tuned against the number it is supposed to be judged by.

The question a hand-read answers: of the spans that do not locate, how many are the model
paraphrasing or reformatting real text (a locator would legitimately recover these), and how many
are text that is simply not in the document (a locator would launder these into false receipts)?

THE CLASSES
-----------
Assigned by a reader, one per span, against the article text:

  WHITESPACE   present verbatim but for whitespace/newline/tab differences
  PUNCT        present but for quote style, dashes, ellipses, casing
  TRUNCATION   the span is a real passage with an elision ("..." or a dropped middle)
  PARAPHRASE   the substance is present in the article, the wording is the model's
  INVENTION    no corresponding passage in the article at all
  BOUNDARY     real text, but the span merges across a sentence/paragraph gap

WHITESPACE, PUNCT, TRUNCATION and BOUNDARY are recoverable by a locator that is not lying.
PARAPHRASE is the judgement call -- the text is there, the quote is not. INVENTION is the number
that decides the question.

SAMPLING
--------
Seeded, proportional to each lens's share of unlocatable spans, so the sample reflects the corpus
rather than the lens with the most hits. The seed is fixed and the sample is written before any
span is read, so the set cannot be adjusted after seeing it.

    python unlocatable_sample.py --n 120 --out SAMPLE-<date>.jsonl
    python unlocatable_sample.py --grade SAMPLE-<date>.jsonl     # scoring report
"""
import argparse
import io
import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
SEED = 20260911

sys.path.insert(0, str(HERE))
from llm_find_stage import (LOCAL_MODEL, load_corpus,             # noqa: E402
                            load_lenses, prompt_hash)

CLASSES = ["WHITESPACE", "PUNCT", "TRUNCATION", "PARAPHRASE", "INVENTION", "BOUNDARY"]
RECOVERABLE = {"WHITESPACE", "PUNCT", "TRUNCATION", "BOUNDARY"}


def norm(s: str) -> str:
    """Whitespace- and punctuation-insensitive form, for the automatic pre-classification."""
    s = s.lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-").replace("…", "...")
    return re.sub(r"\s+", " ", s).strip()


def collect(model: str) -> list:
    """Every unlocatable span across every lens cache, at the CURRENT taxonomy.

    Selection is by `prompt_hash`, exactly as `llm_find_stage.load_cache` does it -- NOT by
    "the biggest set in the file". Four lenses carry two complete 371-record runs (the
    2026-09-07 one and the 2026-09-11 re-run after the cue repair), so picking by size is a
    coin flip that silently reads the superseded run: the first draft of this collected 3,234
    spans against the payload's 3,210, and that 24-span gap was the bug announcing itself.
    """
    corpus = {d["id"]: d for d in load_corpus()}
    safe = model.replace("/", "_").replace(":", "_")
    lenses = load_lenses(str(HERE.parent / "detectors"))
    out = []
    for p in sorted(CACHE.glob(f"llm-find__{safe}__*.jsonl")):
        lens = p.name.split("__")[-1][: -len(".jsonl")]
        tax = lenses.get(lens)
        if tax is None:
            continue
        want = prompt_hash(tax)
        recs = []
        for line in io.open(p, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("prompt_hash") == want:
                recs.append(rec)
        for rec in recs:
            for h in rec.get("hits", []):
                if h.get("char_start") is None and (h.get("span") or "").strip():
                    out.append({"lens": lens, "article": rec["article"],
                                "detection_id": h.get("detection_id"),
                                "span": h["span"]})
    return out, corpus


def pre_classify(span: str, text: str) -> str:
    """Cheap automatic pass. Only assigns the classes a machine can decide without judgement;
    everything else is left UNREAD for a human. A pre-classifier that guessed PARAPHRASE vs
    INVENTION would be the laundering this whole exercise exists to prevent."""
    if span in text:
        return "LOCATABLE-NOW"
    ns, nt = norm(span), norm(text)
    if ns in nt:
        return "WHITESPACE/PUNCT"
    if "..." in ns or "…" in span:
        head = norm(span.split("...")[0])[:60]
        if len(head) > 20 and head in nt:
            return "TRUNCATION"
    return "UNREAD"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--model", default=LOCAL_MODEL)
    ap.add_argument("--out")
    ap.add_argument("--grade")
    a = ap.parse_args(argv)

    if a.grade:
        rows = [json.loads(l) for l in io.open(a.grade, encoding="utf-8") if l.strip()]
        graded = [r for r in rows if r.get("class")]
        counts = {}
        for r in graded:
            counts[r["class"]] = counts.get(r["class"], 0) + 1
        print(f"graded {len(graded)} of {len(rows)}")
        for c in sorted(counts, key=lambda k: -counts[k]):
            print(f"  {c:<18} {counts[c]:>4}  {counts[c]/max(1,len(graded))*100:5.1f}%")
        inv = counts.get("INVENTION", 0)
        rec = sum(v for k, v in counts.items() if k in RECOVERABLE)
        par = counts.get("PARAPHRASE", 0)
        if graded:
            print(f"\n  recoverable by a locator : {rec:>4}  {rec/len(graded)*100:5.1f}%")
            print(f"  paraphrase (judgement)   : {par:>4}  {par/len(graded)*100:5.1f}%")
            print(f"  INVENTION                : {inv:>4}  {inv/len(graded)*100:5.1f}%")
        return 0

    spans, corpus = collect(a.model)
    print(f"unlocatable spans found: {len(spans)}", file=sys.stderr)
    if not spans:
        return 1
    rng = random.Random(SEED)
    rng.shuffle(spans)
    sample = spans[: a.n]

    for s in sample:
        art = corpus.get(s["article"], {})
        text = art.get("text", "")
        s["pre"] = pre_classify(s["span"], text) if text else "NO-TEXT"
        s["class"] = ""
        s["note"] = ""

    out = Path(a.out) if a.out else HERE / "UNLOCATABLE-SAMPLE.jsonl"
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        for s in sample:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    pre = {}
    for s in sample:
        pre[s["pre"]] = pre.get(s["pre"], 0) + 1
    print(f"wrote {out} — {len(sample)} spans, seed {SEED}")
    for k in sorted(pre, key=lambda x: -pre[x]):
        print(f"  {k:<18} {pre[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
