"""The weighted grader: deterministic, auditable, dependency-free.

The LLM produces DetectionHits (see detect.py). This module turns hits into grades you
can re-run and check by hand. Per lens only — indices are NEVER blended across lenses.

Signal model (per lens, per document):
    index = 100 * (w_breadth*breadth + w_intensity*intensity + w_density*density)
  where
    breadth   = fraction of the lens's markers that fired above threshold
                (co-occurrence across distinct markers — the load-bearing signal:
                 one tell is rhetoric; many tells together, densely, is tradecraft)
    intensity = base-weighted mean of per-marker strength
    density   = weighted hits per 1k tokens, capped

Then grade_subject() aggregates document indices for a subject / URL set / timeline,
keeping each lens on its own axis and reporting a trend (escalation) when docs are dated.
"""
from __future__ import annotations

from statistics import mean
from typing import Iterable, Optional

from .schema import (
    Taxonomy, DetectionHit, ModuleResult, DocumentProfile, SubjectProfile,
)


def _tier_for(index: float, tiers: list[dict]) -> str:
    label = tiers[0]["label"] if tiers else "unknown"
    for t in sorted(tiers, key=lambda x: x["min"]):
        if index >= t["min"]:
            label = t["label"]
    return label


def grade_document_for_lens(
    taxonomy: Taxonomy,
    hits: Iterable[DetectionHit],
    token_count: int,
) -> ModuleResult:
    cfg = taxonomy.config
    hits = list(hits)

    # Per-marker raw strength: capped weighted sum of confidences for that marker's hits.
    marker_scores: dict[str, float] = {m.id: 0.0 for m in taxonomy.markers}
    total_weighted = 0.0
    for h in hits:
        det = taxonomy.detection(h.detection_id)
        if det is None:
            continue  # unknown detection id: ignore, don't crash (taxonomy may have moved)
        marker_id = taxonomy.marker_of(h.detection_id)
        contribution = max(0.0, min(1.0, h.confidence)) * det.weight
        marker_scores[marker_id] = min(1.0, marker_scores[marker_id] + contribution)
        total_weighted += contribution

    markers_present = [
        mid for mid, s in marker_scores.items() if s >= cfg.marker_present_threshold
    ]
    n_markers = len(taxonomy.markers) or 1
    breadth = len(markers_present) / n_markers

    base_sum = sum(m.base_weight for m in taxonomy.markers) or 1.0
    intensity = sum(marker_scores[m.id] * m.base_weight for m in taxonomy.markers) / base_sum

    if token_count > 0:
        per_1k = total_weighted / (token_count / 1000.0)
        density = min(1.0, per_1k / cfg.density_cap_per_1k) if cfg.density_cap_per_1k else 0.0
    else:
        density = 0.0

    index = 100.0 * (
        cfg.w_breadth * breadth
        + cfg.w_intensity * intensity
        + cfg.w_density * density
    )
    index = round(max(0.0, min(100.0, index)), 2)

    return ModuleResult(
        lens_id=taxonomy.id,
        index=index,
        tier=_tier_for(index, cfg.tiers),
        breadth=round(breadth, 4),
        intensity=round(intensity, 4),
        density=round(density, 4),
        marker_scores={k: round(v, 4) for k, v in marker_scores.items()},
        markers_present=markers_present,
        receipts=hits,
    )


def grade_document(
    lenses: dict[str, Taxonomy],
    hits_by_lens: dict[str, list[DetectionHit]],
    token_count: int,
    *,
    doc_id: str = "doc",
    subject: Optional[str] = None,
    url: Optional[str] = None,
    date: Optional[str] = None,
) -> DocumentProfile:
    """Score one document across every lens. Returns a profile (one index per lens)."""
    results = {
        lens_id: grade_document_for_lens(tax, hits_by_lens.get(lens_id, []), token_count)
        for lens_id, tax in lenses.items()
    }
    return DocumentProfile(
        doc_id=doc_id, subject=subject, url=url, date=date,
        token_count=token_count, lenses=results,
    )


def _trend(indices_in_time_order: list[float]) -> str:
    """Rising / flat / falling, by comparing first-half vs second-half mean."""
    n = len(indices_in_time_order)
    if n < 2:
        return "insufficient-data"
    half = n // 2
    first, second = indices_in_time_order[:half], indices_in_time_order[half:]
    delta = mean(second) - mean(first)
    if delta > 5.0:
        return "rising"
    if delta < -5.0:
        return "falling"
    return "flat"


def grade_subject(profiles: list[DocumentProfile], subject: str) -> SubjectProfile:
    """Aggregate document profiles for a subject / URL set / timeline. Per lens, own axis."""
    dated = [p for p in profiles if p.date]
    dated.sort(key=lambda p: p.date)  # ISO dates sort lexicographically
    ordered = dated + [p for p in profiles if not p.date]

    lens_ids = sorted({lid for p in profiles for lid in p.lenses})
    per_lens: dict[str, dict] = {}
    for lid in lens_ids:
        idxs = [p.lenses[lid].index for p in profiles if lid in p.lenses]
        present = [p for p in profiles if lid in p.lenses and p.lenses[lid].markers_present]
        time_ordered = [p.lenses[lid].index for p in dated if lid in p.lenses]
        per_lens[lid] = {
            "max": round(max(idxs), 2) if idxs else 0.0,
            "mean": round(mean(idxs), 2) if idxs else 0.0,
            "n_documents_with_signal": len(present),
            "trend": _trend(time_ordered),
        }

    timeline = [
        {"date": p.date, "doc_id": p.doc_id,
         **{lid: p.lenses[lid].index for lid in p.lenses}}
        for p in ordered if p.date
    ]

    return SubjectProfile(
        subject=subject,
        n_documents=len(profiles),
        per_lens=per_lens,
        timeline=timeline,
    )
