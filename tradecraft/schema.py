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
    # Phrases that SUPPRESS a firing when they appear near the match. Added 2026-09-01.
    #
    # The case that forced it: `legibility` / `erase-local-knowledge` carries the cue
    # "eliminate ambiguity", which is a real marker of the standardisation grid in
    # argumentative prose -- and is also three words of Executive Order 12988 boilerplate
    # ("meets applicable standards to minimize litigation, eliminate ambiguity, and reduce
    # burden"), a paragraph legally required in a large share of US rulemakings. Keeping the
    # cue means firing on nearly every federal rule; dropping it loses a genuine marker.
    #
    # An exclusion can only ever SUPPRESS. It cannot invent a firing, so it cannot make a
    # lens over-fire -- the only risk it carries is lost recall, which `gold_check.py`
    # measures. Every entry should name text that is boilerplate or idiom rather than
    # argument, and narrowing the cue is preferable where the cue can be narrowed.
    excludes: list[str] = field(default_factory=list)


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
    # What the lens reads, and whether literal cue matching can judge it. Declared in the
    # taxonomy since 2026-09-01; previously these facts lived in three hardcoded sets across
    # eval/gold_check.py, tools/harvest_gold.py and tools/export_web.py.
    #
    # That was not a tidiness problem. The parity blind spot found the same day had the
    # export_web list as its root cause: a lens capability recorded away from the lens
    # silently decided which engine features got parity-tested, and a real divergence between
    # detect.py and engine.js passed the gate.
    reads: str = "text"                  # "text" | "graph"
    cue_matching: str = "supported"      # "supported" | "unsupported"

    @property
    def is_structural(self) -> bool:
        """Reads a graph rather than prose, so a cue backend is the wrong instrument."""
        return self.reads == "graph"

    @property
    def cues_usable(self) -> bool:
        """Literal cue matching is a valid backend for these markers."""
        return self.cue_matching == "supported"

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
    #: Script/charset profile (tradecraft.script_profile). Optional because a caller that
    #: passes hits without the text cannot produce one. NOT a lens result and never part of an
    #: index: it records which writing systems the document uses, whether scripts are mixed
    #: inside single words, and whether invisible or bidi characters are present. That is
    #: context no vocabulary-based lens can see -- a cue set cannot notice that `ruѕѕian` is
    #: spelled with a Cyrillic dze, and this does.
    script: Optional[dict] = None


@dataclass
class SubjectProfile:
    """A subject (or URL set, or timeline) aggregated across documents, per lens."""
    subject: str
    n_documents: int
    per_lens: dict[str, dict]          # lens_id -> {max, mean, n_present, trend}
    timeline: list[dict]               # [{date, lens_id: index, ...}] for escalation views
    #: Script/charset summary across the subject's documents: which writing systems appear and
    #: in how many documents, plus counts of documents carrying mixed-script words, Latin
    #: confusables, or invisible/bidi characters. Not scored, not ranked -- a subject writing
    #: in two scripts, or one whose texts carry look-alike substitutions, is a different
    #: research object from one who does not, and that fact belongs in a dossier rather than
    #: in an index.
    script: Optional[dict] = None
