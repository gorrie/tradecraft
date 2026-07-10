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
    return Taxonomy(
        id=raw["id"], name=raw["name"], description=raw.get("description", ""),
        markers=markers, config=config,
    )


def load_lenses(detectors_dir: str) -> dict[str, Taxonomy]:
    """Load every detectors/<lens>/taxonomy.yaml under a directory."""
    out: dict[str, Taxonomy] = {}
    for path in sorted(glob.glob(os.path.join(detectors_dir, "*", "taxonomy.yaml"))):
        tax = load_taxonomy(path)
        out[tax.id] = tax
    return out
