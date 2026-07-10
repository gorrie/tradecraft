"""Tools the local agent can call (Ollama function-calling schema + dispatch).

Stage 1: tradecraft_grade + read_file + fetch_url.
Stage 2: lookup_entity (OSINT entity-graph affiliations / cross-membership) and grade_subject
(grade a subject across its sourced corpus, aggregated). Add tools here (write, research) to
grow the agent toward a local gorrie.
"""
from __future__ import annotations

import json
import os

from tradecraft.loader import load_lenses
from tradecraft.grader import grade_document, grade_subject as _aggregate_subject
from tradecraft.detect import detect
from tradecraft import adapters

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS_DIR = os.path.join(_REPO, "detectors")
# OSINT entity graph. Defaults to the bundled sample snapshot (also exported by ratchet-mcp);
# override via env to point at a fresher/other graph.
ENTITIES_PATH = os.environ.get(
    "TRADECRAFT_ENTITIES",
    os.path.join(_REPO, "data", "research-entities.json"),
)
AGENT_OUT = os.environ.get("AGENT_OUTPUT_DIR", os.path.join(_REPO, "agent_output"))
_LENSES = None
_ENTITIES = None


def _lenses():
    global _LENSES
    if _LENSES is None:
        _LENSES = load_lenses(DETECTORS_DIR)
    return _LENSES


def _entities() -> dict:
    global _ENTITIES
    if _ENTITIES is None:
        with open(ENTITIES_PATH, "r", encoding="utf-8") as fh:
            _ENTITIES = json.load(fh)
    return _ENTITIES


def _find_entity(name: str):
    nl = name.strip().lower()
    ents = _entities().get("entities", [])
    for e in ents:  # exact id/name
        if e.get("id", "").lower() == nl or e.get("name", "").lower() == nl:
            return e
    for e in ents:  # substring
        if nl and (nl in e.get("name", "").lower() or nl in e.get("id", "").lower()):
            return e
    return None


def _entity_sources(e: dict) -> list[str]:
    out = []
    for s in e.get("sources", []):
        u = s.get("url") if isinstance(s, dict) else s
        if isinstance(u, str) and u.startswith("http"):
            out.append(u)
    return out


# ---- tools ----

def tradecraft_grade(text: str, lens: str) -> dict:
    """Score text under a lens locally; return the index, tier, markers, and receipts."""
    lenses = _lenses()
    if lens not in lenses:
        return {"error": f"unknown lens {lens!r}", "available": list(lenses)}
    tax = lenses[lens]
    hits = detect(text, tax, backend="local")
    prof = grade_document({tax.id: tax}, {tax.id: hits}, adapters.token_estimate(text))
    mr = prof.lenses[tax.id]
    return {
        "lens": tax.id, "index": mr.index, "tier": mr.tier,
        "markers_present": mr.markers_present,
        "receipts": [{"detection_id": h.detection_id, "confidence": round(h.confidence, 2),
                      "span": h.span} for h in mr.receipts],
        "note": "a profile + receipts for human review, not a verdict",
    }


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()[:20000]


def fetch_url(url: str) -> str:
    return adapters.from_url(url)["text"][:20000]


def write_file(filename: str, content: str) -> dict:
    """Draft to a file under the agent's output dir (basename only — no path traversal)."""
    os.makedirs(AGENT_OUT, exist_ok=True)
    p = os.path.join(AGENT_OUT, os.path.basename(filename))
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(content)
    return {"ok": True, "path": p, "bytes": len(content)}


def lookup_entity(name: str) -> dict:
    """Look a subject up in the OSINT entity graph: type, sector, topics, summary, the entities it
    is connected to (cross-membership), an affiliation count, and its source URLs."""
    data = _entities()
    e = _find_entity(name)
    if e is None:
        return {"error": f"no entity matching {name!r} in the graph"}
    eid = e.get("id")
    byid = {x.get("id"): x.get("name") for x in data.get("entities", [])}
    connected = []
    for ed in data.get("edges", []):
        if isinstance(ed, list):
            a, b, rel = (ed + [None, None])[0], (ed + [None, None])[1], None
        else:
            a = ed.get("source") or ed.get("src")
            b = ed.get("target") or ed.get("tgt")
            rel = ed.get("rel")
        if eid in (a, b):
            other = b if a == eid else a
            nm = byid.get(other, other)
            connected.append(f"{nm} ({rel})" if rel else str(nm))
    affiliations = sorted(set(connected))
    return {
        "id": eid, "name": e.get("name"), "type": e.get("type"), "sector": e.get("sector"),
        "topics": e.get("topics", []), "summary": e.get("summary"),
        "affiliations": affiliations, "affiliation_count": len(affiliations),
        "sources": _entity_sources(e),
    }


def grade_subject(name: str, lens: str, max_docs: int = 3) -> dict:
    """Grade a subject across its sourced documents: fetch up to max_docs of the subject's source
    URLs, score each under the lens locally, and aggregate. Bounded (each doc is a model call)."""
    lenses = _lenses()
    if lens not in lenses:
        return {"error": f"unknown lens {lens!r}", "available": list(lenses)}
    tax = lenses[lens]
    e = _find_entity(name)
    if e is None:
        return {"error": f"no entity matching {name!r}"}
    urls = _entity_sources(e)[:max_docs]
    if not urls:
        return {"error": f"{e.get('name')} has no fetchable source URLs in the graph"}
    profiles, per_doc = [], []
    for u in urls:
        try:
            text = adapters.from_url(u)["text"][:8000]
        except Exception as ex:
            per_doc.append({"url": u, "error": str(ex)[:120]})
            continue
        hits = detect(text, tax, backend="local")
        prof = grade_document({tax.id: tax}, {tax.id: hits}, adapters.token_estimate(text),
                              doc_id=u, subject=e.get("name"), url=u)
        profiles.append(prof)
        mr = prof.lenses[tax.id]
        per_doc.append({"url": u, "index": mr.index, "tier": mr.tier, "markers": mr.markers_present})
    if not profiles:
        return {"subject": e.get("name"), "error": "no documents could be graded", "attempts": per_doc}
    sp = _aggregate_subject(profiles, e.get("name"))
    return {
        "subject": e.get("name"), "lens": tax.id,
        "per_document": per_doc,
        "aggregate": sp.per_lens.get(tax.id, {}),
        "note": "a profile across the subject's sourced documents; a research aid, never a verdict",
    }


def _lens_enum() -> list[str]:
    return list(_lenses().keys())


TOOLS = [
    {"type": "function", "function": {
        "name": "tradecraft_grade",
        "description": "Score a passage for influence tradecraft under a lens. Returns the index, "
                       "tier, which method-markers fired, and the verbatim receipt spans.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "the passage to analyze"},
            "lens": {"type": "string", "enum": _lens_enum()},
        }, "required": ["text", "lens"]}}},
    {"type": "function", "function": {
        "name": "lookup_entity",
        "description": "Look a person or organization up in the OSINT entity graph: its sector, "
                       "topics, summary, who it is connected to (cross-membership), and its sources.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "entity name or id"}}, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "grade_subject",
        "description": "Grade a subject across its sourced documents: fetch the subject's source URLs, "
                       "score each under a lens, and aggregate into a per-lens profile. Slow (bounded).",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"},
            "lens": {"type": "string", "enum": _lens_enum()},
            "max_docs": {"type": "integer", "description": "max sources to fetch (default 3)"},
        }, "required": ["name", "lens"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a local text file (first 20k chars).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "Fetch a URL and return its visible text (first 20k chars).",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write/draft text to a file under the agent output dir (filename only).",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string"}, "content": {"type": "string"}},
            "required": ["filename", "content"]}}},
]

DISPATCH = {
    "tradecraft_grade": tradecraft_grade,
    "lookup_entity": lookup_entity,
    "grade_subject": grade_subject,
    "read_file": read_file,
    "fetch_url": fetch_url,
    "write_file": write_file,
}
