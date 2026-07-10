"""Tests for the revolving_door structural (graph) lens.

Runs against the REAL graph file shipped with the research site, so the exhibits are the
actual documented careers (Nimmo, Sellitto, Christiano, Leung, ...). Pure graph math — no
network, no LLM. Asserts both the per-detection firing and that the existing grader produces
a ModuleResult with the edge-chain receipts populated.

Run with `pytest` or directly: `python tests/test_structural.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.structural import detect_subject, score_subject  # noqa: E402
from tradecraft.schema import DetectionHit  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# evil-robots-series/tradecraft/  ->  evil-robots-series/website/data/research-entities.json
SERIES_ROOT = os.path.dirname(REPO_ROOT)
GRAPH = os.path.join(SERIES_ROOT, "website", "data", "research-entities.json")
TAXONOMY = os.path.join(REPO_ROOT, "detectors", "revolving_door", "taxonomy.yaml")


def _fired(hits, detection_id):
    return any(h.detection_id == detection_id for h in hits)


def _ids(hits):
    return sorted(h.detection_id for h in hits)


def test_graph_file_present():
    assert os.path.isfile(GRAPH), f"real graph not found at {GRAPH}"
    assert os.path.isfile(TAXONOMY), f"taxonomy not found at {TAXONOMY}"


def test_sellitto_fires_multi_sector_career():
    hits = detect_subject(GRAPH, "MichaelSellitto")
    assert _fired(hits, "spans-three-sectors"), _ids(hits)
    # academia/tank/tech is exactly three -> not the four-plus detection.
    assert not _fired(hits, "spans-four-plus-sectors"), _ids(hits)


def test_nimmo_fires_serial_migration_and_monitor_to_industry():
    hits = detect_subject(GRAPH, "BenNimmo")
    assert _fired(hits, "three-plus-moves"), _ids(hits)        # 4 documented moves
    assert _fired(hits, "watchdog-then-join"), _ids(hits)      # tank (DFRLab/Graphika) -> tech (Meta/OpenAI)


def test_christiano_and_leung_fire_gov_industry_crossing():
    chits = detect_subject(GRAPH, "PaulChristiano")
    lhits = detect_subject(GRAPH, "JadeLeung")
    assert _fired(chits, "crosses-gov-industry"), _ids(chits)  # OpenAI (tech) -> CAISI (gov)
    assert _fired(lhits, "crosses-gov-industry"), _ids(lhits)  # OpenAI (tech) -> UK AISI (gov)


def test_funder_multiple_recipients_fires_for_open_phil():
    hits = detect_subject(GRAPH, "OpenPhilanthropy")
    assert _fired(hits, "funds-three-plus"), _ids(hits)        # MIRI/CAIS/GovAI/Horizon = 4


def test_single_sector_person_stays_incidental():
    """A clearly single-sector / low-edge person produces no revolving-door signal."""
    # Walter Lippmann has no career edges in this graph -> no hits -> index 0 -> incidental.
    hits = detect_subject(GRAPH, "WalterLippmann")
    assert hits == [], _ids(hits)
    result = score_subject(GRAPH, "WalterLippmann", TAXONOMY)
    assert result.index == 0.0
    assert result.tier == "incidental"
    assert result.markers_present == []


def test_grader_returns_module_result_with_receipts():
    """The grader runs on the structural hits and keeps the edge-chain spans as receipts."""
    result = score_subject(GRAPH, "BenNimmo", TAXONOMY)
    assert result.lens_id == "revolving_door"
    assert 0.0 <= result.index <= 100.0
    assert result.receipts, "expected the edge-chain DetectionHits to be carried through"
    assert all(isinstance(h, DetectionHit) for h in result.receipts)
    # the receipt span is a human-readable edge chain
    assert any("->" in h.span for h in result.receipts), [h.span for h in result.receipts]
    # at least serial_migration and monitor_to_industry markers present
    assert "serial_migration" in result.markers_present
    assert "monitor_to_industry" in result.markers_present


def test_loader_loads_the_lens():
    """The new lens loads via loader.load_lenses alongside the others."""
    from tradecraft.loader import load_lenses
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    assert "revolving_door" in lenses
    tax = lenses["revolving_door"]
    assert tax.config.w_density == 0.0
    assert {m.id for m in tax.markers} == {
        "multi_sector_career", "serial_migration", "monitor_to_industry",
        "gov_industry_crossing", "funder_multiple_recipients",
    }


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
