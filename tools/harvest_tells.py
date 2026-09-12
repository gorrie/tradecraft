#!/usr/bin/env python3
"""Data-driven shibboleth harvester for subculture_register.

Instead of hand-guessing candidate tells, extract them by KEYNESS: for each camp, find the 2-4-word
phrases that are frequent in that camp's corpus and near-absent from a CONTRAST corpus (all other
camps' text + the benign controls). Over-representation vs. contrast IS the exclusivity test — a
dual-use phrase appears in the contrast set and auto-down-ranks, so the harvester surfaces coined
in-group idiom and screens out shared vocabulary without any hand-curated stoplist.

This is the scalable replacement for the manual curl+grep loop, and it runs on ANY corpus — historical
canon or modern X/Telegram/forum text — so it also drives the modernize-tells and emergent-group-
discovery phases (BACKLOG items A/E). It only PROPOSES candidates; every survivor still passes the
eval FP gate before landing in the taxonomy.

Usage:
    python tools/harvest_tells.py <corpus_dir>            # corpus_dir holds manifest.json + text files
    python tools/harvest_tells.py <corpus_dir> --camp revolutionary_left --top 25

manifest.json maps camp id -> [relative text filenames]; a "_benign" key may list background files.
Corpora are NOT committed (movement text, some sensitive) — they stage outside the repo. Only this
tool + any manifest live in git.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

STOP = set("the a an and or of to in on for with as is are was were be been being that this these those "
           "it its by at from we you they he she i our their his her your my not no do does did has have "
           "had will would can could should may might must one two into out up down over under more most "
           "such than then so if but which who whom whose what when where why how all any some each other "
           "there here about after before because between".split())

_URL = re.compile(r"https?://\S+|www\.\S+|\b\S+\.(?:org|com|net|gov|edu|io|co)\b\S*", re.I)

def words(text: str):
    text = _URL.sub(" ", text.lower())          # strip URLs/domains (nav/cruft noise)
    return re.findall(r"[a-z][a-z'\-]+", text)   # letters only; no "/" (kept out domain fragments)

def ngrams(toks, n):
    return [" ".join(toks[i:i+n]) for i in range(len(toks)-n+1)]

# markup/code tokens that survive a naive tag strip on JS-heavy pages — a gram containing any is junk
JUNK = set("lt gt amp quot apos nbsp rsquo lsquo ldquo rdquo href http https www function return var "
           "const let div span css px em rem gtag js json href src id class style script link meta "
           "cookiehint redim joomla schema config url origurl prefixes push arguments".split())

def all_stop(gram): return all(w in STOP for w in gram.split())
def has_junk(gram): return any(w in JUNK for w in gram.split())

def counts(text, ns=(2, 3, 4)):
    toks = words(text)
    c = Counter()
    for n in ns:
        for g in ngrams(toks, n):
            if not all_stop(g) and not has_junk(g):
                c[g] += 1
    return c, max(1, len(toks))

def load(corpus_dir):
    man = json.load(open(os.path.join(corpus_dir, "manifest.json"), encoding="utf-8"))
    texts = {}
    for camp, files in man.items():
        buf = []
        for fn in files:
            p = os.path.join(corpus_dir, fn)
            if os.path.exists(p):
                buf.append(open(p, encoding="utf-8", errors="ignore").read())
        texts[camp] = "\n".join(buf)
    return texts

def existing_cues():
    """Cues already in the taxonomy, to skip re-proposing them."""
    from tradecraft.loader import load_lenses
    tax = load_lenses(os.path.join(REPO, "detectors")).get("subculture_register")
    cues = set()
    if tax:
        for m in tax.markers:
            for d in m.detections:
                for cue in getattr(d, "cues", []):
                    cues.add(cue.lower())
    return cues

def harvest(texts, target, top, min_count=3):
    camp_c, camp_tok = counts(texts[target])
    contrast = Counter()
    for camp, txt in texts.items():
        if camp == target or camp == "_benign":
            continue
        c, _ = counts(txt); contrast.update(c)
    benign_c, _ = counts(texts.get("_benign", ""))
    contrast.update(benign_c)
    have = existing_cues()
    cands = []
    for gram, n in camp_c.items():
        if n < min_count or gram in have:
            continue
        cn = contrast.get(gram, 0)
        # keyness: frequent in-camp, rare/absent in contrast. per-1k-token rate ratio.
        rate = n / camp_tok * 1000
        exclusivity = n / (n + cn)          # 1.0 = never seen outside the camp
        cands.append((exclusivity, rate, n, cn, gram))
    # rank: exclusive first, then in-camp frequency
    cands.sort(key=lambda x: (round(x[0], 3), x[2]), reverse=True)
    return cands[:top]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("--camp", default=None)
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    texts = load(a.corpus_dir)
    camps = [a.camp] if a.camp else [c for c in texts if c != "_benign"]
    for camp in camps:
        if camp not in texts:
            print(f"[skip] {camp}: no corpus"); continue
        print(f"\n=== {camp} — top candidate tells (excl = share seen ONLY in-camp) ===")
        for excl, rate, n, cn, gram in harvest(texts, camp, a.top):
            flag = "" if cn == 0 else f"  <- also {cn}x in contrast (DUAL-USE, screen)"
            print(f"  excl={excl:.2f}  in={n:<3} out={cn:<3}  {gram!r}{flag}")

if __name__ == "__main__":
    main()
