#!/usr/bin/env python3
"""Tradecraft web endpoint — wraps detect() + grade over every lens.

The browser demo runs only the deterministic cue floor. This tiny Flask app exposes the FULL
engine so a page (the /tech/ front door, or the Atlas node-click) can request cloud / local /
abliterated backends beyond the floor, with grading and verbatim receipts returned as JSON.

  POST /api/detect  {"text": "...", "backend": "cues"|"auto"|"cloud"|"local", "lenses": [ids?]}
     -> {"backend": ..., "results": [{lens, index, tier, breadth, markers_present, receipts:[...]}]}
  GET  /health      -> {"ok": true, "lenses": [...]}
  GET  /            -> the offline demo.html

Backend defaults to "cues" so it runs with no key, anywhere. detect() falls back to the cue floor
when a cloud key is absent or the model refuses the material. Nothing is persisted.

Run:  pip install -r requirements.txt && python web/server.py    # localhost:8099
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from flask import Flask, request, jsonify, send_from_directory  # noqa: E402
from tradecraft.loader import load_lenses          # noqa: E402
from tradecraft.detect import detect               # noqa: E402
from tradecraft.grader import grade_document_for_lens  # noqa: E402
from tradecraft import adapters                    # noqa: E402

DETECTORS = os.path.join(REPO, "detectors")
LENSES = load_lenses(DETECTORS)
MAX_CHARS = 40000

app = Flask(__name__)


def _run(text: str, backend: str, want: list[str]) -> list[dict]:
    out = []
    tokens = adapters.token_estimate(text)
    for lid in want:
        tax = LENSES.get(lid)
        if tax is None:
            continue
        hits = detect(text, tax, backend=backend)
        mr = grade_document_for_lens(tax, hits, tokens)
        out.append({
            "lens": lid,
            "index": mr.index,
            "tier": mr.tier,
            "breadth": mr.breadth,
            "markers_present": mr.markers_present,
            "receipts": [
                {"detection_id": h.detection_id, "marker": tax.marker_of(h.detection_id),
                 "span": h.span, "confidence": h.confidence, "rationale": h.rationale}
                for h in mr.receipts
            ],
        })
    out.sort(key=lambda r: r["index"], reverse=True)
    return out


@app.post("/api/detect")
def api_detect():
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "")[:MAX_CHARS]
    if not text.strip():
        return jsonify({"error": "empty text"}), 400
    backend = body.get("backend") or "cues"
    want = body.get("lenses") or list(LENSES)
    want = [l for l in want if l in LENSES]
    return jsonify({"backend": backend, "results": _run(text, backend, want)})


@app.get("/health")
def health():
    return jsonify({"ok": True, "lenses": sorted(LENSES)})


@app.get("/")
def index():
    return send_from_directory(HERE, "demo.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8099")))
