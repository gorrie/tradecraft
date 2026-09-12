"""Deterministic context windows, and a cache for expensive model verdicts.

WHY A WINDOW

`verify_hit` asks a model whether a flagged span is the method at work, "read in full
context". Handing it a whole document is wrong twice: it is slow, and past the model's
usable context it gets silently truncated at one end, so the model reads an arbitrary
slice and nobody can tell which. A declared window is reproducible; a truncation is not.
`context_window` takes a fixed span either side, snapped outward to paragraph breaks so
the model never opens mid-sentence.

WHY A CACHE

A verification pass over a real corpus is hundreds of model calls and tens of minutes. Any
measurement worth trusting gets re-run — after a cue edit, a prompt change, a new lens —
and re-paying for verdicts that cannot have changed is what stops people from re-running
it. The cache is content-addressed so that only the parts that actually changed re-run.

THE KEY IS THE WINDOW AND THE PROMPT, NOT THE DOCUMENT

A verdict is only valid for the text the model read and the question it was asked, so both
are in the key. Consequences, all wanted:

  * edit a paragraph and only the hits inside it go stale, not the whole document
  * the same sentence occurring in two documents resolves to one verdict
  * bump `VERIFY_PROMPT_VERSION` and every entry invalidates, rather than a fixed prompt
    silently inheriting the answers the broken one gave — which nearly happened on
    2026-08-26, when prompt v1 turned out unable to tell use from mention

`WINDOW_CHARS` determines the window text and so is in the key by construction: widening it
invalidates everything rather than mixing verdicts taken at two different scopes.

Entries are meant to be reviewable — model, rationale, and the span it judged — because a
verdict nobody can inspect is not evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

#: The verifier's PROMPT is an input to every verdict, so it belongs in the key. Without it,
#: rewriting the prompt would serve cached answers to a question no longer being asked --
#: which nearly happened: prompt v1 could not tell use from mention, and fixing it had to
#: invalidate 85 verdicts rather than silently keep them.
from tradecraft.detect import VERIFY_PROMPT_VERSION

#: Characters of context on each side of the flagged span. The verifier's question is
#: "read in full context, is the author employing this method" -- which needs the
#: surrounding argument, not the whole chapter. A full 200k-char chapter would also blow
#: past the local model's usable context and get silently truncated at one end, which is
#: worse than a declared window: the model would read an arbitrary slice and nobody could
#: tell which. Snapped to paragraph breaks below, so the model never opens mid-sentence.
WINDOW_CHARS = 2000

SCHEMA = 1


def context_window(text: str, start: int, span: str) -> str:
    """The exact text a verifier sees for one hit. Deterministic and paragraph-snapped."""
    if start is None or start < 0:
        return text[:WINDOW_CHARS * 2]
    lo = max(0, start - WINDOW_CHARS)
    hi = min(len(text), start + len(span) + WINDOW_CHARS)
    # Snap outward to a paragraph boundary so the window does not open or close
    # mid-sentence. Bounded: only look a short way, never past the original slice.
    cut = text.rfind("\n\n", lo, start)
    if cut != -1:
        lo = cut + 2
    cut = text.find("\n\n", start + len(span), hi)
    if cut != -1:
        hi = cut
    return text[lo:hi]


def key_for(lens: str, detection: str, span: str, window: str, mode: str = "author") -> str:
    """Stable content-addressed key.

    Includes the window text, so an edit to the surrounding paragraph invalidates the
    verdict that was read from it; the MODE, because "is the author doing this" and "is
    this an instance of the technique" are different questions with different right
    answers on the same span; and that mode's prompt version, so a prompt fix cannot serve
    the answers the broken prompt gave.
    """
    h = hashlib.sha1()
    version = str(VERIFY_PROMPT_VERSION[mode])
    for part in (str(SCHEMA), mode, version, lens, detection, span, window):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:20]


def load(path: Path) -> dict:
    if not Path(path).is_file():
        return {}
    blob = json.loads(Path(path).read_text(encoding="utf-8"))
    if blob.get("schema") != SCHEMA or blob.get("window_chars") != WINDOW_CHARS:
        # Not an error and not silently ignored either: the caller sees an empty cache and
        # re-verifies. These two are GLOBAL -- they change the meaning of every entry, so
        # the whole file goes.
        #
        # Prompt version is deliberately NOT checked here. It is per-mode and it is inside
        # the key, so bumping one mode's prompt misses only that mode's entries instead of
        # discarding a correct and expensive cache for the other.
        return {}
    return blob.get("verdicts", {})


def save(path: Path, verdicts: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "schema": SCHEMA,
        "prompt_versions": dict(VERIFY_PROMPT_VERSION),   # recorded; the KEY enforces it
        "window_chars": WINDOW_CHARS,
        "note": ("Model verdicts for cue hits, computed by tools/verify_mirror.py and read "
                 "as data by tools/export_web.py. Committed so the exporter stays a pure "
                 "function of committed inputs and its --check determinism gate keeps "
                 "meaning something. Key = sha1(schema, prompt_version, lens, detection, "
                 "mode, prompt_version, span, window)."),
        "verdicts": dict(sorted(verdicts.items())),
    }
    p.write_text(json.dumps(body, ensure_ascii=False, indent=1, sort_keys=False),
                 encoding="utf-8", newline="\n")
