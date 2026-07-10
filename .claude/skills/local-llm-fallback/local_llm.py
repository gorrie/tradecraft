"""Reusable local-LLM fallback.

Try the cloud (via OpenRouter — the bias study's channel, key in ~/.claude/agents/.env or
OPENROUTER_API_KEY); when it REFUSES the material (or there's no key), fall back to a LOCAL
uncensored model via Ollama. Drop-in for any skill whose subject can trip a content filter
(occult / influence-op / cyber / adversarial analysis). Stdlib + requests only — no project
imports, so it can be copied into any skill.

    from local_llm import complete
    text = complete("Analyze this passage...", system="You are an analyst.")   # auto-fallback
    data = complete(prompt, json_mode=True)                                     # force JSON out

Env overrides: LOCAL_LLM_CLOUD_MODEL, OPENROUTER_API_KEY, OLLAMA_BASE, LOCAL_LLM_MODEL.
Pattern lifted from tradecraft/detect.py + run_study.call_openrouter / call_ollama (bias study).
"""
from __future__ import annotations

import json
import os

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
CLOUD_MODEL = os.environ.get("LOCAL_LLM_CLOUD_MODEL", "google/gemini-2.5-flash")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
LOCAL_MODEL = os.environ.get("LOCAL_LLM_MODEL", "huihui_ai/qwen2.5-abliterate:14b")


class Refusal(RuntimeError):
    """Raised when the cloud backend declines the material, so auto-mode falls back to local."""


def _openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    envp = os.path.expanduser("~/.claude/agents/.env")
    if os.path.isfile(envp):
        for line in open(envp, encoding="utf-8"):
            s = line.strip()
            if s.startswith("OPENROUTER_API_KEY") and "=" in s:
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENROUTER_API_KEY not set (env or ~/.claude/agents/.env)")


def _cloud(prompt: str, system: str | None, json_mode: bool) -> str:
    import requests
    key = _openrouter_key()
    msgs = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    body = {"model": CLOUD_MODEL, "temperature": 0.3, "max_tokens": 2000, "messages": msgs}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(f"{OPENROUTER_BASE}/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                               "HTTP-Referer": "https://evilrobots.lol", "X-Title": "local-llm-fallback"},
                      json=body, timeout=120)
    if not r.ok:
        raise RuntimeError(f"OpenRouter HTTP {r.status_code}: {r.text[:200]}")
    text = (r.json().get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    if not text:
        raise Refusal("cloud returned empty (soft refusal)")
    return text


def _local(prompt: str, system: str | None, json_mode: bool) -> str:
    import requests
    try:  # preflight: clear failures, not stack traces
        models = [m.get("name") for m in
                  requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5).json().get("models", [])]
    except Exception as e:
        raise RuntimeError(f"local backend unreachable at {OLLAMA_BASE} ({e}); run `ollama serve`")
    if LOCAL_MODEL not in models:
        raise RuntimeError(f"local model {LOCAL_MODEL!r} not pulled; `ollama pull {LOCAL_MODEL}`. "
                           f"have: {', '.join(models) or 'none'}")
    msgs = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    body = {"model": LOCAL_MODEL, "stream": False, "messages": msgs,
            "options": {"temperature": 0.3, "num_predict": 1500}}
    if json_mode:
        body["format"] = "json"
    r = requests.post(f"{OLLAMA_BASE}/api/chat", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"]


def complete(prompt: str, system: str | None = None, *,
             backend: str = "auto", json_mode: bool = False) -> str:
    """backend: 'auto' (cloud via OpenRouter, then local on refusal/no-key) | 'cloud' | 'local'."""
    if backend == "cloud":
        return _cloud(prompt, system, json_mode)
    if backend == "local":
        return _local(prompt, system, json_mode)
    if backend == "auto":
        try:
            return _cloud(prompt, system, json_mode)
        except (Refusal, RuntimeError):
            return _local(prompt, system, json_mode)
    raise ValueError(f"unknown backend {backend!r}")
