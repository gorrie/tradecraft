#!/usr/bin/env python3
"""One text normaliser for every corpus fetcher: markup out, words intact.

WHAT THIS FIXES
---------------
Measured 2026-09-05, after the by-id refetch:

    method-specimens.jsonl    155 of 155 documents carry HTML tags, 106 carry entities
    advocacy-comments.jsonl    28 of  38 carry tags,                 36 carry entities

`fetch_regulations.py` did `" ".join(comment.split())` and nothing else, so `<br/>` and
`&rsquo;` sit in the prose verbatim. The Federal Register's raw text carries its own markup --
`<bullet>`, `<INF>`/`<SUP>`, `</a>`, and Cloudflare's email-obfuscation spans -- and no fetcher
touched it either. Every one of those is a token in `text.split()`, which means:

  * word counts are wrong, and every background rate here is fired-documents over n-documents
    with word counts deciding the buckets;
  * a cue that spans a `<br/>` cannot match;
  * `&rsquo;` breaks any pattern written with a real apostrophe, which is all of them.

THREE COPIES ALREADY EXISTED
----------------------------
`fetch_manifest.py`, `mediawiki.plain()`, and `refile_method_specimens.de_html()` each
unescape entities their own way, and none of the three was applied to the specimen corpora.
This is the one implementation; `de_html` now delegates to it rather than being deleted,
because de-forking by taking one side wholesale has silently broken callers in this repo five
times and a thin wrapper costs nothing.

INLINE AND BLOCK ARE NOT THE SAME TAG
-------------------------------------
Mapping every tag to a space -- which `de_html` did -- turns `H<INF>2</INF>O` into `H 2 O`,
three tokens where the document has one. Mapping every tag to nothing welds `one<br/>two` into
`onetwo`. So inline formatting closes up and everything else opens a gap. That distinction is
the only judgement in this file, and it is why it is worth having one copy of.
"""
from __future__ import annotations

import html as html_mod
import re

#: Formatting that lives INSIDE a word. Removed with no separator: `H<INF>2</INF>O` -> `H2O`.
_INLINE = re.compile(r"(?i)</?(?:inf|sup|sub|b|i|em|strong|u|small)\s*/?>")

#: Cloudflare's email obfuscation. The visible content is a placeholder, not prose, so the
#: whole element goes -- leaving it behind puts `[email protected]` in the word stream 306 times.
_CF_EMAIL = re.compile(r'(?is)<span[^>]*class="[^"]*__cf_email__[^"]*"[^>]*>.*?</span>')

#: Elements whose CONTENT is not prose. Dropped whole, not unwrapped.
_DROP_WHOLE = re.compile(r"(?is)<(script|style|head|noscript)\b[^>]*>.*?</\1>")

#: Everything else. Becomes a space, because a block boundary is a word boundary.
#:
#: A TAG NAME IS REQUIRED after the `<`. Without that clause this was `<[^>]{0,400}>`, which
#: matched any `<...>` span at all -- and in a corpus of environmental rulemakings that means
#: PROSE: `precipitation <20 inches/year) for disposal years prior to 2010` was deleted whole
#: from fr_2024-07413. It surfaced only because the deletion left a literal `<` behind and the
#: repair pass was not idempotent on that one record. A cleaner that silently eats a sentence
#: containing a less-than sign is a worse defect than the markup it removes.
_ANY_TAG = re.compile(r"(?s)</?[a-zA-Z!?][^>]{0,400}>")


def clean(text: str) -> str:
    """Markup-free, entity-free, whitespace-collapsed prose.

    Order matters: drop non-prose elements before unwrapping anything, close up inline
    formatting before the generic rule can put spaces in the middle of words, and unescape
    entities LAST so that an escaped `&lt;br&gt;` in the source is not then treated as a tag.
    """
    if not text:
        return ""
    t = _DROP_WHOLE.sub(" ", text)
    t = _CF_EMAIL.sub(" ", t)
    t = _INLINE.sub("", t)
    t = _ANY_TAG.sub(" ", t)
    t = html_mod.unescape(t)
    return " ".join(t.split())


def has_markup(text: str) -> bool:
    """True when `clean` would change something structural. Used by the audit, not the fetch."""
    if not text:
        return False
    return bool(_ANY_TAG.search(text)) or html_mod.unescape(text) != text
