"""The local agent loop: Ollama native tool-calling on an uncensored model.

No cloud, no moderation gate. An optional persona (e.g. a local 'gorrie') is prepended to the
system prompt; tools come from tools.py.
"""
from __future__ import annotations

import json
import os

from tradecraft.detect import LOCAL_MODEL, OLLAMA_BASE
from .tools import TOOLS, DISPATCH

SYSTEM = (
    "You are a LOCAL, UNMODERATED, ideology-blind analyst of influence tradecraft. You judge HOW "
    "a text operates (its method), never whose side it is on. Use tradecraft_grade(text, lens) to "
    "score material; lookup_entity(name) for a subject's affiliations and sources; "
    "grade_subject(name, lens) to grade a subject across its sourced documents; read_file / "
    "fetch_url to obtain material; write_file to draft. You NEVER render a verdict about a person "
    "or organization — you report which method-markers fired, with their verbatim spans, and "
    "explain in plain language a journalist new to the subject could use. When you have enough, "
    "give a final plain-language summary that names the lens, the markers that fired, and quotes "
    "the receipts."
)

PERSONA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "personas")


def _load_persona(name: str) -> str:
    path = os.path.join(PERSONA_DIR, f"{name}.md")
    if not os.path.isfile(path):
        avail = [f[:-3] for f in os.listdir(PERSONA_DIR)] if os.path.isdir(PERSONA_DIR) else []
        raise FileNotFoundError(f"persona {name!r} not found; available: {', '.join(avail) or 'none'}")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def run(task: str, *, model: str | None = None, base: str | None = None, max_iters: int = 8,
        verbose: bool = False, persona: str | None = None) -> str:
    import requests  # lazy
    model = model or LOCAL_MODEL
    base = base or OLLAMA_BASE
    system = SYSTEM if not persona else _load_persona(persona) + "\n\n---\n\n" + SYSTEM
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task}]

    for step in range(max_iters):
        r = requests.post(
            f"{base}/api/chat",
            json={"model": model, "stream": False, "tools": TOOLS, "messages": messages,
                  "options": {"temperature": 0.3, "num_predict": 1500}},
            timeout=600,
        )
        r.raise_for_status()
        msg = r.json()["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content", "")
        for c in calls:
            fn = c.get("function", {}).get("name", "")
            args = c.get("function", {}).get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            if verbose:
                print(f"[tool] {fn}({', '.join(args)})", flush=True)
            try:
                result = DISPATCH[fn](**args) if fn in DISPATCH else {"error": f"unknown tool {fn}"}
            except Exception as e:  # tool failure must not crash the loop
                result = {"error": str(e)[:300]}
            messages.append({"role": "tool", "content": json.dumps(result, default=str)[:8000]})

    return messages[-1].get("content", "") or "(max iterations reached without a final answer)"
