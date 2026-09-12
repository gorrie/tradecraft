"""Every lens declares what it can do, and the loader refuses one that does not.

Capability facts about a lens used to live in three hardcoded sets: `STRUCTURAL` in
eval/gold_check.py, `STRUCTURAL` again in tools/harvest_gold.py, and `LLM_ONLY` in
tools/export_web.py. gold_check's own comment said the first belonged in the taxonomy.

The cost of leaving them there was not hypothetical. On 2026-09-01 cue exclusions were added
to detect.py and not to engine.js, and test_engine_parity stayed green -- because the only lens
carrying an `excludes` entry was in export_web's LLM_ONLY set, so no exported fixture exercised
the feature at all. A capability recorded away from the lens decided what got tested.

Run with `pytest` or directly: `python tests/test_lens_capabilities.py`.
"""
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.loader import load_lenses, load_taxonomy  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS = os.path.join(REPO_ROOT, "detectors")
LENSES = load_lenses(DETECTORS)


def test_every_lens_declares_both_capabilities():
    for lens_id, tax in LENSES.items():
        assert tax.reads in ("text", "graph"), lens_id
        assert tax.cue_matching in ("supported", "unsupported"), lens_id


def test_the_declarations_are_in_the_yaml_not_defaults():
    """A default would let a new lens be graded by the wrong instrument in silence."""
    for lens_id in LENSES:
        path = os.path.join(DETECTORS, lens_id, "taxonomy.yaml")
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        assert "reads" in raw, "%s does not declare reads" % lens_id
        assert "cue_matching" in raw, "%s does not declare cue_matching" % lens_id


def test_loader_refuses_a_taxonomy_with_no_declaration(tmp_path):
    p = tmp_path / "taxonomy.yaml"
    p.write_text(
        "id: nodecl\nname: No Declaration\ndescription: x\n"
        "markers:\n- id: m\n  name: m\n  base_weight: 1.0\n  detections:\n"
        "  - id: d\n    weight: 1.0\n    definition: x\n    cues: [foo]\n",
        encoding="utf-8")
    with pytest.raises(ValueError) as err:
        load_taxonomy(str(p))
    assert "does not declare" in str(err.value)


def test_loader_refuses_an_unknown_value(tmp_path):
    p = tmp_path / "taxonomy.yaml"
    p.write_text(
        "id: badval\nname: Bad\ndescription: x\nreads: tealeaves\n"
        "cue_matching: supported\n"
        "markers:\n- id: m\n  name: m\n  base_weight: 1.0\n  detections:\n"
        "  - id: d\n    weight: 1.0\n    definition: x\n    cues: [foo]\n",
        encoding="utf-8")
    with pytest.raises(ValueError) as err:
        load_taxonomy(str(p))
    assert "expected one of" in str(err.value)


def test_structural_lenses_are_the_graph_readers():
    """The two structural lenses read a graph; nothing else claims to."""
    graph = {lid for lid, t in LENSES.items() if t.is_structural}
    assert graph == {"revolving_door", "network_brokerage"}


def test_cue_unusable_set_is_unchanged_by_the_move():
    """Moving a fact must not revise it. This is the membership the hardcoded set had."""
    unusable = {lid for lid, t in LENSES.items() if not t.cues_usable}
    assert unusable == {"cognitive_capture", "legibility", "counterproductivity",
                        "distributed_accountability", "inevitability_framing"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([os.path.abspath(__file__), "-q"]))
