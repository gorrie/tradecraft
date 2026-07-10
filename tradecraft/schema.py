"""Data model for the Tradecraft framework.

A *lens* (detector module) is a Taxonomy: markers, each holding granular detections.
An LLM scoring pass turns a document into DetectionHits. The grader turns hits into a
ModuleResult (per lens), and aggregates ModuleResults into Subject/Timeline profiles.

Pure stdlib so the grader is dependency-free and trivially testable. YAML loading lives
in `loader.py`; nothing here imports yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---- taxonomy (the lens definition; loaded from detectors/<lens>/taxonomy.yaml) ----

@dataclass(frozen=True)
class Detection:
    """One granular tell within a marker."""
    id: str
    weight: float                      # relative importance within the framework (0..1+)
    definition: str
    cues: list[str] = field(default_factory=list)
    gold: list[dict] = field(default_factory=list)   # [{text, source}] — the receipt that defines it


@dataclass(frozen=True)
class Marker:
    """A family of related detections (e.g. 'gradualism')."""
    id: str
    name: str
    base_weight: float
    detections: list[Detection]


@dataclass(frozen=True)
class GradingConfig:
    marker_present_threshold: float = 0.30
    w_breadth: float = 0.55            # co-occurrence across distinct markers — the real signal
    w_intensity: float = 0.30          # weighted strength of what fired
    w_density: float = 0.15            # hits per 1k tokens (capped)
    density_cap_per_1k: float = 6.0
    tiers: list[dict] = field(default_factory=lambda: [
        {"min": 0.0, "label": "incidental"},
        {"min": 35.0, "label": "notable"},
        {"min": 60.0, "label": "dense tradecraft (review)"},
    ])


@dataclass(frozen=True)
class Taxonomy:
    """A lens."""
    id: str
    name: str
    description: str
    markers: list[Marker]
    config: GradingConfig = field(default_factory=GradingConfig)

    def marker_of(self, detection_id: str) -> Optional[str]:
        for m in self.markers:
            for d in m.detections:
                if d.id == detection_id:
                    return m.id
        return None

    def detection(self, detection_id: str) -> Optional[Detection]:
        for m in self.markers:
            for d in m.detections:
                if d.id == detection_id:
                    return d
        return None


# ---- runtime (produced by detection + grading) ----

@dataclass(frozen=True)
class DetectionHit:
    """One firing of a detection in a document. Produced by the LLM scoring pass."""
    detection_id: str
    confidence: float                  # 0..1
    span: str                          # the exact quoted text — the receipt
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    rationale: str = ""


@dataclass
class ModuleResult:
    """A document's grade under ONE lens."""
    lens_id: str
    index: float                       # 0..100, this lens only — never blended across lenses
    tier: str
    breadth: float                     # fraction of markers present
    intensity: float
    density: float
    marker_scores: dict[str, float]    # marker_id -> 0..1
    markers_present: list[str]
    receipts: list[DetectionHit]       # every hit, kept for human adjudication


@dataclass
class DocumentProfile:
    """One document scored across every lens run. A profile, not a single score."""
    doc_id: str
    subject: Optional[str]
    url: Optional[str]
    date: Optional[str]                # ISO date string; sorting/timeline only
    token_count: int
    lenses: dict[str, ModuleResult]    # lens_id -> ModuleResult


@dataclass
class SubjectProfile:
    """A subject (or URL set, or timeline) aggregated across documents, per lens."""
    subject: str
    n_documents: int
    per_lens: dict[str, dict]          # lens_id -> {max, mean, n_present, trend}
    timeline: list[dict]               # [{date, lens_id: index, ...}] for escalation views
