"""MediaWiki retrieval, shared by every wiki-sourced corpus in this project.

Extracted from `fetch_wikisource.py` on 2026-09-04, when a second wiki was needed and the
choice was between copying 150 lines of API handling or having one copy. The wikitext
stripping in particular is the part that must not fork: `strip_templates` brace-matching and
the `ws-noexport` / `wst-header` element drops are the difference between a corpus of prose
and a corpus of navigation furniture, and a second implementation would drift from the first
without anything noticing -- the same failure this project has already fixed three times in
other files.

Site-specific behaviour lives in the callers:

    fetch_wikisource.py   en.wikisource.org  -- public-domain works, listed by subpage prefix
    fetch_wikinews.py     en.wikinews.org    -- CC-BY news copy, listed by category

Set the endpoint with `use_site()` before fetching. It is module state rather than a parameter
threaded through six functions because a process fetches from one wiki at a time, and a
half-switched endpoint is a corpus with two provenances and one label.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request

#: Current API endpoint. `use_site()` sets it; the default keeps existing callers working.
API = "https://en.wikisource.org/w/api.php"

UA = "tradecraft-research/1.0 (+https://github.com/gorrie/tradecraft)"

#: Titles per batched request. The API caps at 50; 40 leaves headroom for long titles in the URL.
BATCH = 40

#: Seconds between requests. Serial and unhurried on purpose -- see the project's request
#: discipline: never blast a site, honour a 429 by backing off, identify yourself.
DELAY = 1.5

SITES = {
    "wikisource": "https://en.wikisource.org/w/api.php",
    "wikinews": "https://en.wikinews.org/w/api.php",
}


def use_site(name):
    """Point every subsequent call at one wiki. Returns the endpoint, for the record."""
    global API
    if name not in SITES:
        raise ValueError("unknown site %r; known: %s" % (name, ", ".join(sorted(SITES))))
    API = SITES[name]
    return API


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def strip_templates(text):
    """Remove {{...}} by MATCHING BRACES, because templates nest.

    A non-greedy `\\{\\{.*?\\}\\}` stops at the first `}}`, so a header like
    `{{header|title=Progress and Poverty|author=Henry George|notes={{smalltoc}}}}` leaves its
    own field names behind as prose. Measured: `header title`, `author henry george`,
    `notes smalltoc` and `title chapters` all reached the top of a candidate list that way,
    each appearing in 27 of 28 canon files -- template scaffolding wearing the shape of a
    strong signal.
    """
    out = []
    depth = 0
    i = 0
    while i < len(text):
        if text.startswith("{{", i):
            depth += 1
            i += 2
        elif text.startswith("}}", i):
            depth = max(0, depth - 1)
            i += 2
        else:
            if depth == 0:
                out.append(text[i])
            i += 1
    if depth != 0:
        # Unbalanced braces: a malformed transcription must not swallow the rest of the page.
        # Fall back to removing only well-formed pairs, which is the old behaviour and is
        # wrong in a small way rather than catastrophic in a large one.
        return re.sub(r"(?s)\{\{.*?\}\}", " ", text)
    return "".join(out)


#: Rendered elements that are furniture, not prose: header templates and the "do not export"
#: blocks a wiki uses to keep apparatus out of downloads.
#:
#: EXACTLY the set fetch_wikisource.py used before this module existed, and it must stay that
#: way. The georgist, lenin and revleft canon mines were built with these three; adding
#: navbox/reflist/catlinks here -- which a first draft of this file did -- would silently
#: change the text of every already-measured corpus and move the idiom counts derived from it.
#: A shared module inherits its default from the caller it was extracted from, not from what
#: looks more thorough. Per-site extras go in SITE_DROP_CLASSES below.
_DROP_CLASSES = ("ws-noexport", "wst-header", "ws-noinclude")

#: Additional drops for a specific wiki, applied on top of the shared set by that wiki's
#: fetcher. Wikinews articles carry a dateline, a source list and boilerplate navigation that
#: are not the article's prose.
SITE_DROP_CLASSES = {
    "wikinews": ("navbox", "mw-editsection", "printfooter", "catlinks",
                 "sisterSitesBox", "messagebox", "infobox"),
}


def strip_elements(html_text, classes=_DROP_CLASSES):
    """Remove <div> elements whose class matches, including nested divs, by depth counting."""
    out = html_text
    for cls in classes:
        while True:
            m = re.search(r'<div[^>]*class="[^"]*%s[^"]*"[^>]*>' % re.escape(cls), out,
                          re.IGNORECASE)
            if not m:
                break
            i = m.end()
            depth = 1
            while i < len(out) and depth:
                nxt = re.compile(r"</?div\b", re.IGNORECASE).search(out, i)
                if not nxt:
                    break
                depth += -1 if out[nxt.start():nxt.start() + 5].lower() == "</div" else 1
                i = nxt.end()
            if depth:
                # NEVER CLOSED. The counter ran off the end because the `</div>` never arrived,
                # and this used to set `i = len(out)` and delete from the opener to EOF: measured
                # 98 characters to 13 on a one-line input with one unclosed `messagebox`.
                # strip_templates' fallback is the precedent -- unbalanced markup gets the
                # conservative reading, not the destructive one -- so take the FIRST `</div>`
                # after the opener if there is one, and otherwise drop only the opening tag,
                # which plain()'s generic tag strip would have removed anyway. Wrong in a small
                # way (a nested div's tail survives as prose) rather than catastrophic in a
                # large one. Only reachable when depth never returned to zero, i.e. only on the
                # inputs the old code truncated; a balanced document never enters this branch.
                first = re.compile(r"</div\b", re.IGNORECASE).search(out, m.end())
                i = first.end() if first else m.end()
            close = out.find(">", i - 1)
            out = out[:m.start()] + " " + out[(close + 1) if close != -1 else len(out):]
    return out


def plain(markup, drop_classes=_DROP_CLASSES):
    """Strip wikitext or rendered HTML to prose. Deliberately blunt: this feeds an n-gram count.

    BYTE-IDENTICAL to fetch_wikisource.py's version before the extraction, and verified so by
    tests/test_mediawiki_extraction.py. A first draft of this function "improved" it -- kept
    the label from an external link instead of the URL plus label, stripped `== Heading ==`
    lines -- and either change silently rewrites the text of the georgist, lenin and revleft
    corpora that have already been mined and measured. An extraction that changes behaviour is
    not an extraction, and the numbers derived from the old behaviour would have gone on
    standing in results files while the code no longer produced them.

    Two repairs since, each confined to inputs the old code TRUNCATED (2026-09-04): a
    self-closing `<ref .../>` no longer deletes everything up to the next `</ref>`, and an
    unclosed drop-class `<div>` no longer deletes to end-of-file (see strip_elements). Neither
    touches a well-formed document. Measured 2026-09-04, pre-repair vs post-repair on the same
    inputs: 101 raw Wikinews revisions (0 divergences; the 94 hash-pinned ones reproduce their
    manifest sha256 through both), 116 raw + 91 rendered Wikisource pages re-fetched for the
    georgist / lenin / revleft canon and their Smith and Marx controls (0 divergences in
    plain() and in strip_elements), the 28-page georgist raw wikitext stored from the
    2026-09-03 mine (0), and 331 in-repo corpus documents (0). The 29 stored lenin pages are
    reproduced exactly by the new code from the re-fetched input. Only the two synthetic
    truncation inputs in tests/test_mediawiki.py diverge, which is the intended outcome.
    """
    t = strip_elements(markup, drop_classes)
    # SELF-CLOSING FIRST. `<ref name=a/>` has no `</ref>`, so the paired pattern on the next line
    # ran from it to the NEXT `</ref>` anywhere in the document and deleted the prose between:
    # measured 105 characters to 16 on a two-sentence input with one named reference. Removing
    # the self-closing form on its own changes nothing else: a `<ref .../>` with no later
    # `</ref>` was already dropped by the generic `<[^>]+>` strip below, to the same single
    # space, and a paired `<ref>...</ref>` still matches the paired pattern.
    t = re.sub(r"(?is)<(script|style|table|sup|ref)[^>]*/>", " ", t)
    t = re.sub(r"(?is)<(script|style|table|sup|ref).*?</\1>", " ", t)
    t = strip_templates(t)
    t = re.sub(r"(?s)\[\[[^\]|]*\|", " ", t)
    t = re.sub(r"[\[\]']", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def list_subpages(prefix, limit=300):
    """Every mainspace page under `prefix`. Chapter subpages of a work, usually."""
    data = _get({"action": "query", "generator": "allpages", "gapprefix": prefix,
                 "gapnamespace": 0, "gaplimit": limit, "format": "json"})
    pages = data.get("query", {}).get("pages", {})
    return sorted(p["title"] for p in pages.values())


def list_category(category, limit=500):
    """Mainspace page titles in `category`, paging until exhausted or `limit` reached.

    Paged rather than single-shot because a Wikinews month category runs to several hundred
    articles and a truncated listing would silently bias a background pool toward whatever
    the API happened to return first.
    """
    titles, cont = [], None
    while len(titles) < limit:
        params = {"action": "query", "list": "categorymembers",
                  "cmtitle": "Category:" + category, "cmnamespace": 0,
                  "cmlimit": min(500, limit - len(titles)), "format": "json"}
        if cont:
            params["cmcontinue"] = cont
        data = _get(params)
        titles += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        cont = (data.get("continue") or {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(DELAY)
    return sorted(set(titles))[:limit]


def list_subcategories(category, limit=200):
    """Subcategory titles (namespace 14) inside `category`, full "Category:X" form."""
    data = _get({"action": "query", "list": "categorymembers",
                 "cmtitle": "Category:" + category, "cmnamespace": 14,
                 "cmlimit": limit, "format": "json"})
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def list_category_tree(category, limit=500):
    """Mainspace articles in `category` OR in any of its immediate subcategories.

    Wikinews' dated archive is two levels deep and this is not obvious from the outside:
    `Category:January 2024` contains thirty-one DAY subcategories and zero articles, while the
    articles carry `Category:January 1, 2024`. A single-level listing of the month returns an
    empty set and looks exactly like "that month has no news" -- which is what it did on the
    first run here, and why this function exists rather than a retry with a different month.
    """
    titles = list(list_category(category, limit=limit))
    if len(titles) >= limit:
        return titles[:limit]
    for sub in list_subcategories(category):
        name = sub.split(":", 1)[1] if ":" in sub else sub
        titles += list_category(name, limit=limit - len(titles))
        time.sleep(DELAY)
        if len(titles) >= limit:
            break
    return sorted(set(titles))[:limit]


def revisions(titles):
    """Revision ids and timestamps for many titles, so a fetch can be pinned to a version.

    A background pool must be rebuildable to the SAME text, not merely to the same titles --
    a wiki page changes under you. The revid is what makes "recomputable" mean something.
    """
    out = {}
    for i in range(0, len(titles), BATCH):
        batch = titles[i:i + BATCH]
        data = _get({"action": "query", "prop": "revisions",
                     "rvprop": "ids|timestamp", "redirects": "1",
                     "format": "json", "titles": "|".join(batch)})
        for page in data.get("query", {}).get("pages", {}).values():
            rev = (page.get("revisions") or [{}])[0]
            if rev.get("revid"):
                out[page["title"]] = {"revid": rev["revid"],
                                      "timestamp": rev.get("timestamp")}
        if i + BATCH < len(titles):
            time.sleep(DELAY)
    return out


def fetch_batched(titles):
    """Wikitext for many titles in few calls. Cheap, but returns stubs for proofread books."""
    out = {}
    for i in range(0, len(titles), BATCH):
        batch = titles[i:i + BATCH]
        data = _get({"action": "query", "prop": "revisions", "rvprop": "content",
                     "rvslots": "main", "redirects": "1", "format": "json",
                     "titles": "|".join(batch)})
        for page in data.get("query", {}).get("pages", {}).values():
            if "revisions" in page:
                out[page["title"]] = plain(
                    page["revisions"][0]["slots"]["main"]["*"])
        if i + BATCH < len(titles):
            time.sleep(DELAY)
    return out


def fetch_by_revid(revid, raw=False):
    """ONE pinned revision. The rebuild path for a manifest.

    `raw=True` returns the wikitext UNPROCESSED, for a caller with site-specific handling that
    has to run before the generic stripper. Wikinews needs it: `{{w|Kunming}}` is how it links
    to Wikipedia and the linked words are the article's own prose, so a caller that receives
    already-stripped text cannot recover them -- the first Wikinews fetch here came back with a
    hole where every place name had been, in 95 of 95 documents, because this function had no
    raw mode and cleaned before the caller could intervene.
    """
    data = _get({"action": "query", "prop": "revisions", "rvprop": "content",
                 "rvslots": "main", "revids": revid, "format": "json"})
    for page in data.get("query", {}).get("pages", {}).values():
        for rev in page.get("revisions") or ():
            text = rev["slots"]["main"]["*"]
            return text if raw else plain(text)
    return None


def fetch_raw_by_revids(revids):
    """Raw wikitext for many pinned revisions, {revid: text}, BATCH per request.

    The API takes multiple `revids`, so a thousand-article pool is 25 requests rather than a
    thousand. That is not an optimisation for our convenience -- it is the request discipline:
    one call per document, even politely delayed, is twenty-five minutes of sustained load on
    somebody else's server to collect a background corpus.
    """
    out = {}
    ids = [str(r) for r in revids]
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        data = _get({"action": "query", "prop": "revisions", "rvprop": "content|ids",
                     "rvslots": "main", "revids": "|".join(batch), "format": "json"})
        for page in data.get("query", {}).get("pages", {}).values():
            for rev in page.get("revisions") or ():
                if rev.get("revid"):
                    out[rev["revid"]] = rev["slots"]["main"]["*"]
        if i + BATCH < len(ids):
            time.sleep(DELAY)
    return out


def fetch_rendered(title):
    """Rendered text for one page, resolving Page:-namespace transclusion."""
    data = _get({"action": "parse", "page": title, "prop": "text",
                 "formatversion": "2", "redirects": "1", "format": "json"})
    if "parse" not in data:
        return None
    return plain(data["parse"]["text"])
