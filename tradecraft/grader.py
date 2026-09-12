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

    # TWO DIFFERENT SUMS, and keeping them apart is the point.
    #
    # 2026-09-02: the matcher used to return one hit per detection, so `total_weighted` was
    # bounded by how many DETECTIONS matched -- typically 1 -- and `density = total_weighted /
    # (tokens/1000)` reduced to `k / document_length`. It was an inverse-length term wearing
    # the docstring of a rate. Measured across the corpus, `subculture_register`'s index
    # correlated -1.000 with length. The matcher now returns every occurrence.
    #
    # But occurrences must NOT flow into breadth and intensity. Those answer "which markers
    # are present" and "how strongly", and a document repeating one cue forty times would
    # otherwise cap its marker score and read as broad and intense on the strength of a single
    # phrase. So marker scoring counts each DETECTION once, at its strongest hit, and only
    # density sees the occurrence count. Letting repetition drive intensity would have made
    # intensity a second, worse copy of density.
    marker_scores: dict[str, float] = {m.id: 0.0 for m in taxonomy.markers}
    best_per_detection: dict[str, float] = {}
    total_weighted = 0.0
    for h in hits:
        det = taxonomy.detection(h.detection_id)
        if det is None:
            continue  # unknown detection id: ignore, don't crash (taxonomy may have moved)
        contribution = max(0.0, min(1.0, h.confidence)) * det.weight
        total_weighted += contribution                      # every occurrence: the RATE
        prev = best_per_detection.get(h.detection_id, 0.0)
        if contribution > prev:
            best_per_detection[h.detection_id] = contribution
    for detection_id, contribution in best_per_detection.items():
        marker_id = taxonomy.marker_of(detection_id)        # once per detection: PRESENCE
        marker_scores[marker_id] = min(1.0, marker_scores[marker_id] + contribution)

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
    text: Optional[str] = None,
) -> DocumentProfile:
    """Score one document across every lens. Returns a profile (one index per lens).

    `text` is optional and is used only to attach the script/charset profile. It is not scored
    and cannot change any index -- callers that already hold hits but not the source text (the
    web export, for one) keep working and simply carry no script profile.
    """
    results = {
        lens_id: grade_document_for_lens(tax, hits_by_lens.get(lens_id, []), token_count)
        for lens_id, tax in lenses.items()
    }
    script = None
    if text:
        from .script_profile import profile as script_profile
        script = script_profile(text)
    return DocumentProfile(
        doc_id=doc_id, subject=subject, url=url, date=date,
        token_count=token_count, lenses=results, script=script,
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
        script=_script_summary(profiles),
    )


def _script_summary(profiles: list[DocumentProfile]) -> Optional[dict]:
    """Aggregate the per-document script profiles across a subject.

    Counted in DOCUMENTS rather than in words, deliberately. A subject with one document full
    of confusable substitutions is a different object from one whose whole corpus carries them,
    and a word count would flatten that distinction into a single large number. Returns None
    when no profile carried a script read, so the field distinguishes "nothing found" from "not
    measured" -- the same discipline the floors contract uses.
    """
    scored = [p.script for p in profiles if p.script]
    if not scored:
        return None
    scripts: dict[str, int] = {}
    for s in scored:
        for name in s.get("scripts", {}):
            scripts[name] = scripts.get(name, 0) + 1
    return {
        "documents_profiled": len(scored),
        "scripts_seen": dict(sorted(scripts.items(), key=lambda kv: -kv[1])),
        "documents_multiscript": sum(1 for s in scored if s.get("script_count", 0) > 1),
        "documents_with_mixed_script_words": sum(
            1 for s in scored if s.get("mixed_script_total")),
        "documents_with_confusables": sum(1 for s in scored if s.get("confusable_total")),
        "documents_with_invisibles": sum(1 for s in scored if s.get("invisibles")),
    }
