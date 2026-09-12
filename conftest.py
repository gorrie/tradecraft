"""Skip tests that need sibling repos when this is a standalone checkout.

Nine tests depend on artifacts that live OUTSIDE this repository in the combined workspace:
the built web instrument and the site's engine JS (`website/static/tech/...`), and the
ratchet-mcp text corpus. A standalone clone has neither, which is supported — those tests
should skip with a reason, not fail.

The lists are explicit; `test_sibling_skip_lists_are_current` fails if a named test stops
existing, so the exemptions cannot rot into cover for a real failure.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SERIES = ROOT.parent

WEB_INSTRUMENT = SERIES / "website" / "static" / "tech" / "instrument"
RATCHET_TEXTS = SERIES / "research" / "ratchet-mcp" / "server" / "data" / "texts.jsonl"

HAVE_WEB = (WEB_INSTRUMENT / "instrument.json").exists() and (WEB_INSTRUMENT / "engine.js").exists()
HAVE_TEXTS = RATCHET_TEXTS.exists()

WEB_TESTS = (
    "tools/test_engine_parity.py::test_engine_parity",
    "tools/test_engine_parity.py::test_engine_mechanism_parity",
    "tools/test_engine_parity.py::test_tradecraft_page_uses_the_engine",
    "tools/test_engine_parity.py::test_standalone_demo_embeds_the_same_engine_and_payload",
    "tools/test_engine_parity.py::test_generated_front_end_is_current",
    "tests/test_scriptio_continua_parity.py::test_range_tables_are_identical",
    "tests/test_scriptio_continua_parity.py::test_hangul_is_absent_from_both",
    "tests/test_scriptio_continua_parity.py::test_both_runtimes_agree_character_by_character",
)

TEXTS_TESTS = (
    "tests/test_collateral_eval.py::test_frozen_sample_reports_survivors_and_dropped",
)

WEB_REASON = ("needs the built web instrument from the series website "
              "(website/static/tech/instrument/). Run tools/export_web.py in a combined "
              "workspace checkout; a standalone clone of this repo does not have it.")
TEXTS_REASON = ("needs the ratchet-mcp text corpus "
                "(research/ratchet-mcp/server/data/texts.jsonl), a sibling repo not present "
                "in a standalone checkout.")


def _norm(nodeid: str) -> str:
    return nodeid.replace(os.sep, "/")


def pytest_collection_modifyitems(config, items):
    web = pytest.mark.skip(reason=WEB_REASON)
    txt = pytest.mark.skip(reason=TEXTS_REASON)
    for item in items:
        nid = _norm(item.nodeid)
        if not HAVE_WEB and any(nid.endswith(t) for t in WEB_TESTS):
            item.add_marker(web)
        if not HAVE_TEXTS and any(nid.endswith(t) for t in TEXTS_TESTS):
            item.add_marker(txt)


def test_sibling_skip_lists_are_current(request):
    """Every named test still exists."""
    collected = {_norm(i.nodeid) for i in request.session.items}
    missing = [t for t in WEB_TESTS + TEXTS_TESTS
               if not any(n.endswith(t) for n in collected)]
    assert not missing, "skip lists name tests that no longer exist: %s" % missing
