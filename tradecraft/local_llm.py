"""Shared local-LLM transport: try the cloud, fall back to a local uncensored model on refusal.

This is the one place the "cloud via OpenRouter, then local via Ollama on refusal/no-key" pattern
lives for the package. `detect.py` builds the detection prompt and parses hits; it calls `complete`
here for the actual transport so the try-cloud-then-local dispatch is not re-derived per caller.
The standalone copy under `.claude/skills/local-llm-fallback/local_llm.py` is the vendorable twin
for skills that cannot import this package (stdlib + requests only); keep the two in sync.

    from .local_llm import complete, Refusal
    text = complete(prompt, system="You are an analyst.")          # backend='auto' (default)
    text = complete(prompt, system=..., json_mode=True)            # force JSON out

Env overrides: TRADECRAFT_CLOUD_MODEL, OPENROUTER_API_KEY, OLLAMA_BASE, TRADECRAFT_LOCAL_MODEL.
Pattern lifted from run_study.call_openrouter / call_ollama (bias study).
"""
from __future__ import annotations

import os
from typing import Optional

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
# Cloud model via OpenRouter — override with TRADECRAFT_CLOUD_MODEL (e.g. anthropic/claude-*, openai/gpt-*).
CLOUD_MODEL = os.environ.get("TRADECRAFT_CLOUD_MODEL", "google/gemini-2.5-flash")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
# Uncensored + tools-capable on a 24GB GPU; override via env.
LOCAL_MODEL = os.environ.get("TRADECRAFT_LOCAL_MODEL", "huihui_ai/qwen2.5-abliterate:14b")


class Refusal(RuntimeError):
    """Raised when the cloud backend declines the material, so auto-mode falls back to local."""


def _openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    envp = os.path.expanduser("~/.claude/agents/.env")
    if os.path.isfile(envp):
        with open(envp, "r", encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("OPENROUTER_API_KEY") and "=" in s:
                    return s.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENROUTER_API_KEY not set (env or ~/.claude/agents/.env)")


def cloud(prompt: str, system: Optional[str], *, model: str, json_mode: bool) -> str:
    """OpenRouter chat/completions (proven transport from run_study.call_openrouter)."""
    import requests  # lazy
    key = _openrouter_key()
    msgs = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    body = {"model": model, "temperature": 0.2, "max_tokens": 2000, "messages": msgs}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://evilrobots.lol", "X-Title": "Tradecraft Detector"},
        json=body, timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"OpenRouter HTTP {r.status_code}: {r.text[:200]}")
    text = (r.json().get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    if not text:
        raise Refusal("cloud returned empty (soft refusal)")
    return text


def local(prompt: str, system: Optional[str], *, model: str, json_mode: bool) -> str:
    """Ollama /api/chat (proven pattern from run_study.call_ollama), with a clear preflight."""
    import requests  # lazy
    from .health import ensure_ollama
    ensure_ollama(OLLAMA_BASE, model)  # clear, cross-platform failure if daemon/model missing
    msgs = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    body = {"model": model, "stream": False, "messages": msgs,
            "options": {"temperature": 0.2, "num_predict": 1500}}
    if json_mode:
        body["format"] = "json"
    r = requests.post(f"{OLLAMA_BASE}/api/chat", json=body, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"]


def complete(prompt: str, system: Optional[str] = None, *,
             backend: str = "auto", model: Optional[str] = None,
             local_model: Optional[str] = None, json_mode: bool = False) -> str:
    """backend: 'auto' (cloud, then local on refusal/no-key) | 'cloud' | 'local'.

    `model` overrides the cloud model; `local_model` overrides the local model. In 'auto' the
    cloud is tried first and any Refusal/RuntimeError (a refusal or a missing key) falls through
    to the local uncensored model.
    """
    if backend in ("cloud", "anthropic", "openrouter"):
        return cloud(prompt, system, model=model or CLOUD_MODEL, json_mode=json_mode)
    if backend == "local":
        return local(prompt, system, model=local_model or LOCAL_MODEL, json_mode=json_mode)
    if backend == "auto":
        try:
            return cloud(prompt, system, model=model or CLOUD_MODEL, json_mode=json_mode)
        except (Refusal, RuntimeError):
            return local(prompt, system, model=local_model or LOCAL_MODEL, json_mode=json_mode)
    raise ValueError(f"unknown backend {backend!r}")
