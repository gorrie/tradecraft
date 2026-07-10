"""Cross-platform preflight for the local backend. Clear failures, not stack traces.

Pure requests; works the same on Windows / macOS / Linux. The agent and detector call
ensure_ollama() before a local run so a stopped daemon or an un-pulled model produces an
actionable message instead of a raw connection error.
"""
from __future__ import annotations


def ollama_status(base: str) -> dict:
    """Return {ok, models, error}. Never raises."""
    try:
        import requests
        r = requests.get(f"{base}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return {"ok": True, "models": models, "error": None}
    except Exception as e:  # ImportError, ConnectionError, timeout, HTTP error
        return {"ok": False, "models": [], "error": str(e)[:200]}


def ensure_ollama(base: str, model: str) -> dict:
    """Raise a clear, actionable RuntimeError if Ollama is down or the model is missing."""
    st = ollama_status(base)
    if not st["ok"]:
        raise RuntimeError(
            f"Local model backend unreachable at {base} ({st['error']}). "
            f"Is Ollama running? Start it with `ollama serve` (or set OLLAMA_BASE)."
        )
    if model not in st["models"]:
        have = ", ".join(st["models"]) or "(none pulled)"
        raise RuntimeError(
            f"Local model {model!r} is not available. Pull it with `ollama pull {model}`. "
            f"Currently available: {have}."
        )
    return st
