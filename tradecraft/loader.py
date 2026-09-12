"""Load lens taxonomies from YAML (the only place yaml is imported)."""
from __future__ import annotations

import glob
import os

import yaml

from .schema import Taxonomy, Marker, Detection, GradingConfig


def load_taxonomy(path: str) -> Taxonomy:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    markers = [
        Marker(
            id=m["id"], name=m["name"], base_weight=float(m["base_weight"]),
            detections=[
                Detection(
                    id=d["id"], weight=float(d["weight"]), definition=d["definition"],
                    cues=list(d.get("cues", [])), gold=list(d.get("gold", [])),
                    excludes=list(d.get("excludes", [])),
                )
                for d in m["detections"]
            ],
        )
        for m in raw["markers"]
    ]
    cfg_raw = raw.get("config", {}) or {}
    config = GradingConfig(
        marker_present_threshold=float(cfg_raw.get("marker_present_threshold", 0.30)),
        w_breadth=float(cfg_raw.get("w_breadth", 0.55)),
        w_intensity=float(cfg_raw.get("w_intensity", 0.30)),
        w_density=float(cfg_raw.get("w_density", 0.15)),
        density_cap_per_1k=float(cfg_raw.get("density_cap_per_1k", 6.0)),
        tiers=list(cfg_raw.get("tiers", GradingConfig().tiers)),
    )
    # Required, not defaulted. A new lens that forgets to say what it reads would otherwise
    # default into "text" and get graded by the wrong instrument in silence -- which is the
    # error gold_check's first run made, reporting 0 of 9 for revolving_door as a defect.
    reads = raw.get("reads")
    cue_matching = raw.get("cue_matching")
    for field_name, value, allowed in (("reads", reads, ("text", "graph")),
                                       ("cue_matching", cue_matching,
                                        ("supported", "unsupported"))):
        if value is None:
            raise ValueError(
                "%s: taxonomy %r does not declare `%s`. Every lens must say what it can do, "
                "because the alternative is a tool guessing -- add `%s: <%s>` near the top."
                % (path, raw.get("id"), field_name, field_name, " | ".join(allowed)))
        if value not in allowed:
            raise ValueError("%s: taxonomy %r has `%s: %r`; expected one of %s"
                             % (path, raw.get("id"), field_name, value, list(allowed)))

    return Taxonomy(
        id=raw["id"], name=raw["name"], description=raw.get("description", ""),
        markers=markers, config=config, reads=reads, cue_matching=cue_matching,
    )


def load_lenses(detectors_dir: str) -> dict[str, Taxonomy]:
    """Load every detectors/<lens>/taxonomy.yaml under a directory."""
    out: dict[str, Taxonomy] = {}
    for path in sorted(glob.glob(os.path.join(detectors_dir, "*", "taxonomy.yaml"))):
        tax = load_taxonomy(path)
        out[tax.id] = tax
    return out
