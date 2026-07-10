"""Tests for the cloud/local transport (local_llm.py). Mocks requests + the key loader."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tradecraft import local_llm as L  # noqa: E402


class _Resp:
    def __init__(self, payload, ok=True, status=200, text=""):
        self._payload, self.ok, self.status_code, self.text = payload, ok, status, text

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


# ---- key loading -----------------------------------------------------------------------------

def test_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-env")
    assert L._openrouter_key() == "k-env"


def test_key_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    envp = tmp_path / ".env"
    envp.write_text('OPENROUTER_API_KEY="k-file"\n', encoding="utf-8")
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(envp))
    assert L._openrouter_key() == "k-file"


def test_key_missing_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(os.path, "expanduser", lambda p: "/nonexistent/.env")
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        L._openrouter_key()


# ---- cloud -----------------------------------------------------------------------------------

def test_cloud_ok(monkeypatch):
    import requests
    monkeypatch.setattr(L, "_openrouter_key", lambda: "k")
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _Resp({"choices": [{"message": {"content": "  hi  "}}]}))
    assert L.cloud("p", "s", model="m", json_mode=True) == "hi"


def test_cloud_http_error(monkeypatch):
    import requests
    monkeypatch.setattr(L, "_openrouter_key", lambda: "k")
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp({}, ok=False, status=429, text="rate"))
    with pytest.raises(RuntimeError, match="OpenRouter HTTP 429"):
        L.cloud("p", None, model="m", json_mode=False)


def test_cloud_empty_is_refusal(monkeypatch):
    import requests
    monkeypatch.setattr(L, "_openrouter_key", lambda: "k")
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _Resp({"choices": [{"message": {"content": ""}}]}))
    with pytest.raises(L.Refusal):
        L.cloud("p", "s", model="m", json_mode=False)


# ---- local -----------------------------------------------------------------------------------

def test_local_ok(monkeypatch):
    import requests
    monkeypatch.setattr(L, "ensure_ollama", lambda base, model: {"ok": True}, raising=False)
    # ensure_ollama is imported inside local(); patch the source in health instead
    from tradecraft import health
    monkeypatch.setattr(health, "ensure_ollama", lambda base, model: {"ok": True})
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _Resp({"message": {"content": "local-out"}}))
    assert L.local("p", "s", model="m", json_mode=True) == "local-out"


# ---- complete dispatch -----------------------------------------------------------------------

def test_complete_cloud(monkeypatch):
    monkeypatch.setattr(L, "cloud", lambda *a, **k: "C")
    assert L.complete("p", backend="cloud") == "C"


def test_complete_local(monkeypatch):
    monkeypatch.setattr(L, "local", lambda *a, **k: "Lo")
    assert L.complete("p", backend="local") == "Lo"


def test_complete_auto_falls_back_to_local(monkeypatch):
    def boom(*a, **k):
        raise L.Refusal("declined")
    monkeypatch.setattr(L, "cloud", boom)
    monkeypatch.setattr(L, "local", lambda *a, **k: "fellback")
    assert L.complete("p", backend="auto") == "fellback"


def test_complete_auto_uses_cloud_when_ok(monkeypatch):
    monkeypatch.setattr(L, "cloud", lambda *a, **k: "cloudwin")
    assert L.complete("p", backend="auto") == "cloudwin"


def test_complete_unknown_backend():
    with pytest.raises(ValueError, match="unknown backend"):
        L.complete("p", backend="nope")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
