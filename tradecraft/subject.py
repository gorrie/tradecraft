"""The texts-by-person lane: grade a SUBJECT from the texts they authored.

This is the prose counterpart to ``structural.py``'s graph lane. Where the graph lane reads a
person's career/funding topology, this lane reads the person's own WORDS — speeches, op-eds, posts,
testimony — and grades how those texts operate under the TEXT lenses (institutional_permeation,
cognitive_capture, adept_speech, legibility, counterproductivity, distributed_accountability,
inevitability_framing).

It exists so a person in the Ratchet dataset can be profiled by method, the same ideology-blind way
the graph lane profiles topology:

  * PER LENS, NEVER BLENDED. Each text gets one index per lens (``grade_document``); the per-subject
    aggregate (``grade_subject``) keeps every lens on its own axis. There is no single "tradecraft
    score" for a person, by design — blending lenses would manufacture a verdict, and this tool never
    renders one.
  * GRAPH LENSES EXCLUDED. ``revolving_door`` and ``network_brokerage`` score a GRAPH, not prose;
    running them on text would be a category error. They are dropped here and stay in the graph lane.
  * NEVER A VERDICT. The output is a profile + receipts (the exact spans that fired) for human
    adjudication, attributed to the subject as *what their texts exhibit* — not a finding about the
    person's character or motives.
  * BACKEND-AGNOSTIC. Uses whatever detection backend you pass (``cues`` for the offline/CI floor,
    ``cloud``/``local``/``auto`` for the model read). The grader is identical regardless.
"""
from __future__ import annotations

from typing import Optional

from .schema import Taxonomy, DocumentProfile, SubjectProfile
from .grader import grade_document, grade_subject
from . import adapters

# Lenses that score a GRAPH (topology), not prose. Excluded from the text lane.
GRAPH_LENSES = frozenset({"revolving_door", "network_brokerage"})


def text_lenses(lenses: dict[str, Taxonomy]) -> dict[str, Taxonomy]:
    """The subset of ``lenses`` that operate on prose (everything but the graph lenses)."""
    return {lid: tax for lid, tax in lenses.items() if lid not in GRAPH_LENSES}


def grade_text(
    lenses: dict[str, Taxonomy],
    text: str,
    *,
    doc_id: str,
    subject: Optional[str] = None,
    url: Optional[str] = None,
    date: Optional[str] = None,
    backend: str = "cues",
    model: Optional[str] = None,
) -> DocumentProfile:
    """Score ONE text across every text lens. Returns a profile (one index per lens).

    ``backend="cues"`` is the deterministic offline default so this runs in CI and without a key;
    pass ``"cloud"``/``"local"``/``"auto"`` for the model read.
    """
    from .detect import detect  # lazy: the model backends need optional deps; cues does not
    tax_by_lens = text_lenses(lenses)
    hits_by_lens = {
        lid: detect(text, tax, backend=backend, model=model)
        for lid, tax in tax_by_lens.items()
    }
    return grade_document(
        tax_by_lens, hits_by_lens,
        token_count=adapters.token_estimate(text),
        doc_id=doc_id, subject=subject, url=url, date=date,
    )


def grade_person(
    lenses: dict[str, Taxonomy],
    person_id: str,
    texts: list[dict],
    *,
    backend: str = "cues",
    model: Optional[str] = None,
) -> tuple[SubjectProfile, list[DocumentProfile]]:
    """Grade a person from a list of their texts, per text lens, aggregated per subject.

    Each ``texts`` item is a dict: ``{text, [id], [url], [date]}`` (the ratchet-mcp texts store
    schema). Returns ``(SubjectProfile, [DocumentProfile])`` — the aggregate plus the per-document
    profiles, so receipts stay inspectable. Never blended across lenses; never a verdict.
    """
    profiles: list[DocumentProfile] = []
    for i, t in enumerate(texts):
        body = (t.get("text") or "").strip()
        if not body:
            continue
        profiles.append(grade_text(
            lenses, body,
            doc_id=t.get("id") or f"{person_id}#{i}",
            subject=person_id,
            url=t.get("url"),
            date=t.get("date"),
            backend=backend, model=model,
        ))
    return grade_subject(profiles, person_id), profiles
