"""Input adapters: turn subjects / URLs / timelines into documents to grade.

A *document* here is a small dict: {doc_id, text, subject, url, date}. Adapters only build
documents; detect.py scores them and grader.py grades them. Network/HTML deps are optional and
imported lazily so the core stays dependency-free.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional


def from_text(text: str, *, doc_id: str = "text", subject: Optional[str] = None,
              url: Optional[str] = None, date: Optional[str] = None) -> dict:
    return {"doc_id": doc_id, "text": text, "subject": subject, "url": url, "date": date}


def token_estimate(text: str) -> int:
    """Cheap, stable token proxy (~0.75 words/token). Deterministic — no tokenizer dep."""
    words = len(text.split())
    return max(1, int(words / 0.75))


def from_url(url: str, *, subject: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Fetch a URL with a browser UA and crudely extract visible text."""
    import requests  # lazy
    headers = {"User-Agent": "Mozilla/5.0 (compatible; tradecraft/0.1; +accountability research)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    html = resp.text
    html = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return from_text(text, doc_id=url, subject=subject, url=url, date=date)


def from_subject(subject_id: str, entities_path: str) -> dict:
    """Look a subject up in the OSINT entity graph (research-entities.json) and return its
    sourced URLs as a corpus to fetch. Reuses the existing entity research rather than duplicating.
    Returns {subject, label, sources:[url,...]}; caller fetches via from_url."""
    with open(entities_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    pools = []
    for key in ("people", "institutions", "entities", "nodes"):
        if isinstance(data.get(key), list):
            pools.extend(data[key])
    for ent in pools:
        if ent.get("id") == subject_id or ent.get("label") == subject_id:
            srcs = ent.get("sources", [])
            urls = [s.get("url", s) if isinstance(s, dict) else s for s in srcs]
            return {"subject": ent.get("id", subject_id), "label": ent.get("label"),
                    "sources": [u for u in urls if isinstance(u, str) and u.startswith("http")]}
    raise KeyError(f"subject {subject_id!r} not found in {os.path.basename(entities_path)}")


def from_file(path: str, *, subject: Optional[str] = None, url: Optional[str] = None,
              date: Optional[str] = None) -> dict:
    """One plain-text / markdown file -> a document. doc_id defaults to the basename."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return from_text(text, doc_id=os.path.basename(path), subject=subject, url=url, date=date)


def from_dir(path: str, *, pattern: str = "*.txt", subject: Optional[str] = None) -> list[dict]:
    """Every file matching ``pattern`` in a directory -> a list of documents (sorted by name).

    The broadest cheap intake: drop a folder of speeches / transcripts / op-eds and grade them all.
    """
    import glob as _glob
    docs = []
    for p in sorted(_glob.glob(os.path.join(path, pattern))):
        if os.path.isfile(p):
            docs.append(from_file(p, subject=subject))
    return docs


def from_jsonl(path: str, *, subject: Optional[str] = None, text_key: str = "text") -> list[dict]:
    """A JSONL texts store -> documents. The texts-by-person store format:
    ``{text, [id], [url], [date], [person_id|subject]}``. Optionally filter to one subject.

    This is the bridge between the stored evidence (ratchet-mcp ``texts.jsonl``) and the grader.
    """
    docs = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            subj = rec.get("subject") or rec.get("person_id")
            if subject and subj != subject:
                continue
            body = rec.get(text_key) or ""
            if not body.strip():
                continue
            docs.append(from_text(body, doc_id=rec.get("id") or f"{subj or 'doc'}#{i}",
                                  subject=subj, url=rec.get("url"), date=rec.get("date")))
    return docs


def from_pdf(path: str, *, subject: Optional[str] = None, url: Optional[str] = None,
             date: Optional[str] = None) -> dict:
    """One PDF -> a document. Lazy import: tries ``pypdf`` then ``pdfminer.six``; raises a clear
    error if neither is installed (PDF support is optional, not a core dependency)."""
    text = None
    try:
        from pypdf import PdfReader  # lazy, optional
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    except ImportError:
        try:
            from pdfminer.high_level import extract_text  # lazy, optional
            text = extract_text(path)
        except ImportError as e:
            raise ImportError("PDF intake needs 'pypdf' or 'pdfminer.six' "
                              "(pip install pypdf).") from e
    text = re.sub(r"\s+\n", "\n", (text or "")).strip()
    return from_text(text, doc_id=os.path.basename(path), subject=subject, url=url, date=date)


def from_x_export(path: str, *, subject: Optional[str] = None) -> list[dict]:
    """An X/Twitter export (the ``x_ingest`` JSONL: ``{id, handle, created_at, text, url}``)
    -> documents. ``subject`` filters to one handle. Offline — reads the exported file, never
    calls the API (ingestion is the X tools' job; grading is ours)."""
    docs = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            handle = rec.get("handle")
            if subject and handle not in (subject, subject.lstrip("@")):
                continue
            body = rec.get("text") or rec.get("full_text") or ""
            if not body.strip():
                continue
            created = rec.get("created_at") or ""
            docs.append(from_text(body, doc_id=str(rec.get("id") or f"x#{len(docs)}"),
                                  subject=handle, url=rec.get("url"),
                                  date=created[:10] if created else None))
    return docs


def write_ratchet_graph(data_dir: str, out_path: str) -> int:
    """Convert a ratchet-mcp data dir (``people.jsonl`` + ``institutions.jsonl`` + ``edges.jsonl``)
    into the ``{entities:[{id,sector,name}], edges:[{source,target}]}`` schema the graph lenses
    (structural.py / network.py) read, and write it to ``out_path``. Returns the entity count.

    This bridges the two graphs: the rich 844-edge establishment graph lives in ratchet-mcp, but the
    graph lenses were written against the research-entities schema. Note: ratchet edges are plain
    adjacency (no career-move ``rel`` types), so ``network_brokerage`` (betweenness / degree /
    sector-brokerage — adjacency + sector only) ports cleanly, while ``revolving_door`` (which keys
    on move/funding ``rel`` types) cannot fire from this graph until those edges are typed.
    """
    entities: list[dict] = []
    for fn in ("people.jsonl", "institutions.jsonl"):
        with open(os.path.join(data_dir, fn), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                entities.append({"id": r["id"], "sector": r.get("sector"),
                                 "name": r.get("label", r["id"])})
    edges: list[dict] = []
    with open(os.path.join(data_dir, "edges.jsonl"), "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if isinstance(e, list):
                e = {"source": e[0], "target": e[1]}
            if e.get("source") and e.get("target"):
                edges.append({"source": e["source"], "target": e["target"]})
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"entities": entities, "edges": edges}, fh, ensure_ascii=False)
    return len(entities)


def group_timeline(documents: list[dict]) -> list[dict]:
    """Sort dated documents oldest-first for escalation views (ISO dates sort lexically)."""
    return sorted([d for d in documents if d.get("date")], key=lambda d: d["date"]) \
        + [d for d in documents if not d.get("date")]
