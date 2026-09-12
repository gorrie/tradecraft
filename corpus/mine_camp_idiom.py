#!/usr/bin/env python3
"""Mine candidate shibboleths from a camp's own canon, with the controls that make it honest.

WHY THIS EXISTS
---------------
Step 2 of `BACKLOG-shibboleth-corpus-study.md`: pull multi-word terms that recur ACROSS the
camp's own works and are near-absent from general prose. Step 3's precision arm decides what
survives. Run once by hand for `georgist` on 2026-09-03 and the ratio was **22 candidates in,
one cue out** (`eval/RESULTS-2026-09-03-georgist-canon-mine.md`), which is worth knowing before
scheduling nine more camps.

THE CONTROL THAT MATTERS IS THE DISCIPLINE-MATCHED ONE
------------------------------------------------------
The in-repo benign controls -- `corpus/_news-control` (news) and `corpus/_calibration-cache`
(Federal Register) -- cannot separate a camp from its FIELD, because neither is that field. For
`georgist` they passed four candidates that Adam Smith then rejected outright as ordinary
political economy: `adam smith` (69 occurrences in Smith), `taxes upon` (82), `wealth of
nations` (51), `effect upon` (14). All four would have shipped on the benign controls alone.

So `--discipline` is not optional in practice. Suggested pairings, one control serving several
camps:

    classical economics (Smith, Mill, Ricardo)  -> georgist, mmt_monetary
    mainstream theology                          -> christian_nationalist, tradcath_integralist
    academic sociology                           -> critical_social_justice, radical_feminist
    security studies / terrorism studies         -> jihadist_militant, militant_mobilization
    mainstream macro / central-bank prose        -> mmt_monetary, crypto_sovereign_libertarian

AND THE LIMIT THIS TOOL CANNOT FIX
----------------------------------
Keyness mining against a single-author control separates one AUTHOR from another, not a camp
from a field. Everything distinctive about *Progress and Poverty* against *The Wealth of
Nations* is partly Georgism and partly George-the-Victorian-essayist, and n-gram frequency
cannot tell those apart -- which is why nine of the georgist survivors were phrases like
`thrown open`, `great masses` and `least exertion`. They would fire on Mill or Spencer.

**Give a camp >=2 DIFFERENT AUTHORS** so what survives is what the camp shares rather than what
one writer repeats. This tool prints how many distinct canon files each candidate appears in
(`files` column) precisely so that is visible; a candidate in only one file is one writer's tic
until a second author confirms it.

Nothing here edits a taxonomy. It prints candidates for a human to rule on, and the ruling is
the bottleneck.

    python corpus/mine_camp_idiom.py --canon ~/canon/georgist.jsonl \
        --discipline ~/canon/smith.jsonl --min-canon 4
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BENIGN = (os.path.join(ROOT, "corpus", "_news-control", "*.txt"),
          os.path.join(ROOT, "corpus", "_calibration-cache", "*.txt"))

STOP = set("""the a an and or but if of to in on for with as by at from that this these those
it its is are was were be been being he she they we you i his her their our your not no nor so
than then there here when where which who whom whose what how why all any both each few more
most other some such only own same too very can will just should now would could may might must
shall do does did have has had am into over under again further once about against between
during before after above below up down out off s t ll ve re d m o y""".split())


def load_jsonl(path):
    out = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            rec = json.loads(line)
            text = rec.get("text") or rec.get("wikitext") or ""
            if text.strip():
                out.append((rec.get("title") or os.path.basename(path), text))
    return out


#: British/American orthography, normalised on BOTH sides before anything is counted.
#:
#: Found the hard way, 2026-09-03. The Wikisource *Wealth of Nations* is an American edition
#: ("labor" 1,324 times, "labour" 56) and George is British ("labour" 576, "labor" 12). So
#: `produce of labour` measured ZERO occurrences in Smith and passed the discipline control as
#: a Georgist shibboleth -- while `produce of labor` occurs 8 times in the same text. Without
#: this, every -our/-ise gram in a British canon clears an American control for free, which is
#: the most flattering possible error and completely silent.
VARIANTS = {
    "labour": "labor", "labours": "labors", "labourer": "laborer", "labourers": "laborers",
    "neighbour": "neighbor", "neighbours": "neighbors", "colour": "color",
    "honour": "honor", "favour": "favor", "favours": "favors", "behaviour": "behavior",
    "endeavour": "endeavor", "vapour": "vapor", "savour": "savor", "harbour": "harbor",
    "rigour": "rigor", "vigour": "vigor", "splendour": "splendor", "clamour": "clamor",
    "centre": "center", "centres": "centers", "theatre": "theater", "metre": "meter",
    "defence": "defense", "offence": "offense", "licence": "license", "practise": "practice",
    "organise": "organize", "organised": "organized", "recognise": "recognize",
    "recognised": "recognized", "realise": "realize", "realised": "realized",
    "civilised": "civilized", "specialise": "specialize", "utilise": "utilize",
}


#: DISCIPLINE CONTROLS, declared once and reused. Seven camps do not need seven controls.
#:
#: The georgist run established that the benign controls cannot separate a camp from its FIELD:
#: news and Federal Register prose are not economics, so they passed four candidates that Adam
#: Smith then rejected outright as ordinary political economy. What separates a camp is a
#: control drawn from the camp's own discipline, and disciplines are shared.
#:
#: Recorded here so the pairing is a stated decision rather than a fresh guess per camp, and so
#: the second camp on a discipline costs nothing. `--discipline` still takes explicit paths;
#: this is the map of which corpus to point at, not a loader.
#:
#: A control needs >=2 authors spanning the field's development, for the reason the georgist run
#: found the hard way: Smith predates Ricardo, so Smith's silence on `margin of cultivation`
#: proved nothing about whether it is Georgist or simply post-Smith economics.
DISCIPLINE_CONTROLS = {
    "classical-economics": {
        "camps": ["georgist", "mmt_monetary", "crypto_sovereign_libertarian"],
        "canon": "Smith; Ricardo and Mill needed for post-1776 vocabulary",
        "status": "Smith fetched (418k words, Wikisource, public domain); Ricardo/Mill open",
    },
    "mainstream-theology": {
        "camps": ["christian_nationalist", "tradcath_integralist"],
        "canon": "mainstream systematic theology, ideally pre- and post-Vatican II",
        "status": "not built",
    },
    "academic-sociology": {
        "camps": ["critical_social_justice", "radical_feminist", "gender_critical"],
        "canon": "mainstream sociology and gender studies, not movement material",
        "status": "not built",
    },
    "security-studies": {
        "camps": ["jihadist_militant", "militant_mobilization", "accelerationist_right"],
        "canon": "terrorism-studies and counter-extremism literature",
        "status": "not built. For jihadist_militant the control must be IN ARABIC: "
                  "dar al-harb is mainstream classical juristic vocabulary, so an "
                  "English-language control cannot separate doctrine from jurisprudence "
                  "(T3.1 landed; T3.2 orthography is the remaining prerequisite)",
    },
    "classical-marxism": {
        "camps": ["tankie_mlm", "revolutionary_left"],
        "canon": "Marx and Engels",
        "status": "built (74.6k words, Wikisource, public domain)",
    },
}


#: PER-LANGUAGE ORTHOGRAPHY. English spelling is not a special case, it is the case that
#: happened to be found first: `produce of labour` measured zero in an American-edition control
#: while `produce of labor` occurred 8 times in the same text. Every language has this, and in
#: several it is worse than a spelling convention.
#:
#: Arabic: hamza-carrying alefs are written inconsistently and often bare, ya and alef maqsura
#: are interchanged, ta marbuta alternates with ha in informal text, and short-vowel marks
#: (harakat) plus the tatweel elongation are optional decoration that changes nothing about the
#: word. An unnormalised Arabic cue therefore misses most of its own occurrences.
#:
#: Hebrew: niqqud is optional and usually absent, and the five final-form letters are purely
#: positional -- the same letter, written differently because it ends a word.
#:
#: German: eszett alternates with ss by orthography reform and by Swiss convention.
#:
#: NOT handled here, and it needs saying: Serbian and Kazakh are written in two SCRIPTS, which
#: is transliteration rather than folding and belongs with T3.3's sibling-cue work.
#:
#: This is the MINER's normalisation, applied to canon and controls alike before counting. It
#: is deliberately NOT the detector's: changing what `detect.py` matches would alter firing
#: semantics and must be mirrored in engine.js under the parity gate. Keep them separate.
_ARABIC_FOLD = {
    "أ": "ا", "إ": "ا", "آ": "ا",   # alef with hamza/madda
    "ٱ": "ا",                                            # alef wasla
    "ى": "ي",                                            # alef maqsura -> ya
    "ة": "ه",                                            # ta marbuta -> ha
    "ـ": "",                                                  # tatweel: pure elongation
}
#: Arabic harakat and Quranic marks, and Hebrew niqqud/cantillation: optional pointing.
_STRIP_MARKS = re.compile(r"[ً-ٰٟۖ-ۭ֑-ׇ]")
_HEBREW_FINALS = {"ך": "כ", "ם": "מ", "ן": "נ",
                  "ף": "פ", "ץ": "צ"}


def normalise(text):
    """Fold orthographic variants so canon and control are comparable, per language.

    Case-preserving for Latin: callers lowercase for counting, but a function that silently
    downcases is a trap for the next caller that does not.
    """
    def sub(m):
        w = m.group(0)
        folded = VARIANTS.get(w.lower())
        if folded is None:
            return w
        if w.isupper():
            return folded.upper()
        if w[0].isupper():
            return folded.capitalize()
        return folded

    text = re.sub(r"[A-Za-z]+", sub, text)
    text = text.replace("ß", "ss")            # German eszett
    text = _STRIP_MARKS.sub("", text)
    if any(ch in _ARABIC_FOLD or ch in _HEBREW_FINALS for ch in text):
        text = "".join(_ARABIC_FOLD.get(ch, _HEBREW_FINALS.get(ch, ch)) for ch in text)
    return text


#: Structural boilerplate from a transcription's own navigation, not the author's prose.
#: The first run of this tool put `chapter x`, `chapter ii` ... `chapter xi` in the top
#: fourteen candidates -- each appearing in 27 of 27 canon files, because Wikisource renders
#: chapter navigation into every page. Left in, it would pollute every camp mined this way, and
#: it is the kind of noise that looks like a strong signal: high count, present everywhere.
NAV = re.compile(r"\b(chapter|book|part|section|volume|page|appendix|preface|contents|index)\b"
                 r"|^[ivxlcdm]+$|\b[ivxlcdm]{2,}\b")

#: SCHOLARLY APPARATUS. A heavily-footnoted primary work carries its citation machinery at the
#: frequency of real idiom: mining Lenin's *Imperialism* surfaced `op cit` 16 times across 6
#: files, cleanly absent from both controls, which is exactly the profile of a shibboleth and
#: is instead a footnote convention. Same class as navigation: nothing to do with the argument.
APPARATUS = re.compile(r"\b(op cit|loc cit|ibid|et al|cf|passim|vol|pp|footnote|translated by"
                       r"|quoted in|reprinted|edition|publishers?|press)\b")

#: THE POLEMICAL TARGET'S VOCABULARY. A camp's canon quotes its opponents at length in order to
#: attack them, so an opponent's coinage can appear at the frequency of the camp's own idiom and
#: clear every control -- the opponent is not in the discipline control either.
#:
#: Found on the third camp, 2026-09-03: mining Marx and Engels surfaced `constituted value`, 21
#: occurrences across 7 files, clean on both controls. It is **Proudhon's** term, which Marx
#: quotes throughout *The Poverty of Philosophy* while demolishing it. Shipping it would have
#: made the Marxist lens fire on Proudhonists.
#:
#: The separation is sharp and needs no external knowledge. Measured over the same corpus:
#:
#:     constituted value    80% inside quotation marks, 75% near an attribution
#:     means of production   4%                          9%
#:     productive forces     5%                          2%
#:     petty bourgeois       0%                         22%
#:
#: Reported as a column rather than wired into a filter: a camp DOES sometimes adopt a term it
#: first quoted, and `labor time` sits at 37%/31% precisely because Marx discusses Ricardo's and
#: Proudhon's labour-time as well as his own. So it flags for the human, like dispersion.
ATTRIBUTION = re.compile(r"(\bsays\b|\baccording to\b|\bwrites\b|\bdeclares\b|\basserts\b"
                         r"|\bquotes\b|\btells us\b|\bin the words of\b|\bcalls it\b"
                         r"|\bso-called\b|\bwhat he calls\b|\bm\.\s)", re.IGNORECASE)
QUOTE_CHARS = '"“”«»‘’'
#: Occurrences within this many characters count as the local context for the test above.
QUOTE_WINDOW = 120


def quoted_share(gram, text):
    """Share of `gram`'s occurrences that sit in quotation or attribution context, 0.0-1.0."""
    hits = list(re.finditer(re.escape(gram), text, re.IGNORECASE))
    if not hits:
        return 0.0
    flagged = 0
    for m in hits:
        window = text[max(0, m.start() - QUOTE_WINDOW):m.end() + QUOTE_WINDOW]
        if any(q in window for q in QUOTE_CHARS) or ATTRIBUTION.search(window):
            flagged += 1
    return flagged / len(hits)


def ngrams(text, lo, hi):
    words = re.findall(r"[a-z][a-z'-]*", text.lower())
    for n in range(lo, hi + 1):
        for i in range(len(words) - n + 1):
            gram = words[i:i + n]
            if gram[0] in STOP or gram[-1] in STOP:
                continue
            joined = " ".join(gram)
            if NAV.search(joined) or APPARATUS.search(joined):
                continue
            yield joined


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canon", action="append", required=True,
                    help="JSONL of the camp's own works; repeatable, one per author ideally")
    ap.add_argument("--discipline", action="append", default=[],
                    help="JSONL of field-matched NEGATIVE control (e.g. Adam Smith for georgist)")
    ap.add_argument("--min-canon", type=int, default=4,
                    help="minimum occurrences across the canon (default 4)")
    ap.add_argument("--ngram", default="2-4", help="n-gram range, e.g. 2-4")
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--author", action="append", default=[],
                    help="author name(s) to exclude; repeatable. Rendered transcriptions put "
                         "the author in a header on every page, which reads as strong idiom")
    ap.add_argument("--max-file-share", type=float, default=0.8,
                    help="drop grams appearing in more than this share of canon documents; "
                         "boilerplate saturates, real idiom concentrates (default 0.8)")
    args = ap.parse_args(argv)

    lo, hi = (int(x) for x in args.ngram.split("-"))

    canon_docs = []
    for path in args.canon:
        canon_docs.extend(load_jsonl(path))
    if not canon_docs:
        print("no canon text loaded")
        return 1
    canon_words = sum(len(t.split()) for _, t in canon_docs)
    print("canon: %d document(s), %d words, from %d file(s)"
          % (len(canon_docs), canon_words, len(args.canon)))

    # TITLE STOPLIST, defence in depth against a defect the saturation guard cannot see.
    # A canon's own work titles and author name recur throughout it, and with two books they
    # land in roughly half the files each -- under any sane saturation threshold. Mining Lenin
    # put `infantile disorder`, `left-wing communism`, `last stage of capitalism` and
    # `vladimir ilyich lenin` straight to the top. The titles are KNOWN metadata, so they are
    # simply excluded rather than guessed at. fetch_wikisource.py also strips the rendered
    # header block at the source; this catches whatever any other source leaks.
    title_text = normalise(" ".join(t for t, _ in canon_docs).lower())
    banned = set(ngrams(title_text, lo, hi))
    if args.author:
        for name in args.author:
            banned |= set(ngrams(normalise(name.lower()), lo, hi))

    counts = collections.Counter()
    files_with = collections.defaultdict(set)
    for title, text in canon_docs:
        text = normalise(text)
        grams = [g for g in ngrams(text, lo, hi) if g not in banned]
        counts.update(grams)
        for gram in set(grams):
            files_with[gram].add(title)
    if banned:
        print("title/author stoplist: %d gram(s) excluded as canon metadata" % len(banned))

    benign = []
    for pattern in BENIGN:
        for path in sorted(glob.glob(pattern)):
            benign.append(normalise(
                io.open(path, encoding="utf-8", errors="replace").read().lower()))
    print("benign control: %d document(s)" % len(benign))

    discipline = ""
    for path in args.discipline:
        discipline += " " + " ".join(t for _, t in load_jsonl(path))
    discipline = normalise(discipline.lower())
    if discipline:
        print("discipline control: %d words" % len(discipline.split()))
    else:
        print("discipline control: NONE GIVEN -- candidates below cannot be separated from the")
        print("  camp's own field. Four georgist candidates cleared the benign controls and")
        print("  were then rejected outright by Adam Smith as ordinary political economy.")
        # This tool takes corpus paths and has no idea which camp is being mined, so it prints
        # the registry rather than guessing. Cheaper than making the next person rediscover
        # which control to point at, and it shows which controls already exist.
        print("")
        print("  DISCIPLINE CONTROLS -- built once per discipline, not per camp:")
        for disc, spec in sorted(DISCIPLINE_CONTROLS.items()):
            print("    %-22s %s" % (disc, ", ".join(spec["camps"])))
            print("      %-20s %s" % ("canon:", spec["canon"]))
            print("      %-20s %s" % ("status:", spec["status"]))
    ratio = canon_words / max(1, len(discipline.split())) if discipline else 0.0

    # SATURATION GUARD, and it is source-agnostic in a way the NAV list is not. Real idiom
    # CONCENTRATES -- `natural opportunities` sat in 4 of 28 files, `labour and capital` in 12
    # of 28. Structural boilerplate SATURATES: every template field name and navigation string
    # measured here appeared in 27 or 28 of 28. So a gram present in nearly every document of
    # a canon is the transcription's scaffolding, not the author's argument, whatever the
    # scaffolding happens to be called on the site it came from.
    n_docs = len(canon_docs)
    cands = [(g, n) for g, n in counts.items()
             if n >= args.min_canon
             and (n_docs < 4 or len(files_with[g]) <= args.max_file_share * n_docs)]
    dropped_sat = sum(1 for g, n in counts.items()
                      if n >= args.min_canon and n_docs >= 4
                      and len(files_with[g]) > args.max_file_share * n_docs)
    if dropped_sat:
        print("dropped %d saturated gram(s) present in >%.0f%% of canon documents "
              "(transcription boilerplate)" % (dropped_sat, 100 * args.max_file_share))
    canon_all = normalise(" ".join(t for _, t in canon_docs))
    print("")
    print("%-32s %6s %5s %7s %7s %6s  %s"
          % ("candidate", "canon", "files", "benign", "field", "quoted", "verdict"))
    keep = []
    for gram, n in sorted(cands, key=lambda kv: -kv[1])[:args.top]:
        nb = sum(1 for t in benign if gram in t)
        nd = discipline.count(gram) if discipline else 0
        nf = len(files_with[gram])
        qs = quoted_share(gram, canon_all)
        if nb == 0 and discipline and nd == 0:
            if qs >= 0.5:
                verdict = "QUOTED -- the polemical target's term?"
            elif nf >= 2:
                verdict = "CANDIDATE"
                keep.append(gram)
            else:
                verdict = "candidate (ONE file -- author's tic?)"
        elif discipline and nd >= (n / ratio) * 0.5:
            verdict = "field vocabulary"
        elif nb:
            verdict = "in benign control"
        else:
            verdict = "review"
        print("%-32s %6d %5d %7d %7d %5.0f%%  %s"
              % (gram, n, nf, nb, nd, 100 * qs, verdict))

    print("")
    print("%d candidate(s) clear both controls." % len(keep))
    print("Now a human rules on each: a coined TERM OF ART or slogan survives; a phrase that is")
    print("merely this author's habit does not. That ruling is the bottleneck and this tool")
    print("cannot make it -- georgist yielded 1 cue from 22 candidates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
