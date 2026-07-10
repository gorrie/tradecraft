"""Tests for the local-backend preflight (health.py). Mocks requests; never hits the network."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tradecraft import health  # noqa: E402


class _Resp:
    def __init__(self, payload, ok=True):
        self._payload = payload
        self._ok = ok

    def raise_for_status(self):
        if not self._ok:
            raise RuntimeError("HTTP 500")

    def json(self):
        return self._payload


def _fake_requests(monkeypatch, payload=None, ok=True, boom=None):
    import requests
    def get(url, timeout=0):
        if boom:
            raise boom
        return _Resp(payload or {}, ok=ok)
    monkeypatch.setattr(requests, "get", get)


def test_ollama_status_ok(monkeypatch):
    _fake_requests(monkeypatch, payload={"models": [{"name": "m1"}, {"name": "m2"}]})
    st = health.ollama_status("http://x")
    assert st["ok"] and st["models"] == ["m1", "m2"] and st["error"] is None


def test_ollama_status_down_never_raises(monkeypatch):
    _fake_requests(monkeypatch, boom=ConnectionError("refused"))
    st = health.ollama_status("http://x")
    assert st["ok"] is False and st["models"] == [] and "refused" in st["error"]


def test_ensure_ollama_ok(monkeypatch):
    _fake_requests(monkeypatch, payload={"models": [{"name": "good"}]})
    assert health.ensure_ollama("http://x", "good")["ok"]


def test_ensure_ollama_daemon_down(monkeypatch):
    _fake_requests(monkeypatch, boom=ConnectionError("refused"))
    with pytest.raises(RuntimeError, match="unreachable"):
        health.ensure_ollama("http://x", "any")


def test_ensure_ollama_model_missing(monkeypatch):
    _fake_requests(monkeypatch, payload={"models": [{"name": "other"}]})
    with pytest.raises(RuntimeError, match="not available"):
        health.ensure_ollama("http://x", "missing")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
