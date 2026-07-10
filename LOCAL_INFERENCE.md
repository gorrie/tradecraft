# Local inference — the fallback that isn't optional

This tool reads occult, esoteric, and influence-operation material. An aligned cloud API will
sometimes refuse to analyze it. So a **local, uncensored** scoring path is core infrastructure,
not a nicety. This documents the viable pattern, validated on this hardware 2026-06-17.

## What's viable here (probed, not assumed)

- **Ollama 0.30.7** on `localhost:11434`, RTX 4090 (24 GB).
- Uncensored ("abliterated") models already pulled — built for exactly the "API won't touch our
  materials" case:
  - **`huihui_ai/qwen2.5-abliterate:14b`** — uncensored **and** advertises `tools` capability.
    **This is the default** (`TRADECRAFT_LOCAL_MODEL`): best accuracy + structured output.
  - `huihui_ai/qwen2.5-abliterate:7b` — faster, but sloppy on label/span precision (smoke-tested).
  - `wash-*-ablit`, `phi4-abliterated`, etc. — additional uncensored options.
- Smoke test (2026-06-17): the 7b returned **valid structured JSON with zero refusal** on a
  permeation+esoteric passage; 37 s cold (model load), seconds when warm.

## The proven call pattern (reused, not reinvented)

Lifted from the bias study's `evil-robots-series/research/bias-study/scripts/run_study.py`
(`call_ollama` + its `channel:model` abstraction — `ollama:<model>` vs `openrouter:<model>`):

```python
requests.post("http://localhost:11434/api/chat", json={
    "model": "huihui_ai/qwen2.5-abliterate:14b",
    "format": "json",                       # force valid JSON
    "stream": False,
    "options": {"temperature": 0.2, "num_predict": 1500},
    "messages": [{"role": "system", "content": SYSTEM_WITH_JSON_INSTRUCTION},
                 {"role": "user", "content": build_user_prompt(taxonomy, text)}],
}, timeout=300)
# -> r.json()["message"]["content"] is a JSON string: {"hits":[...]}
```

For the heavier weight-rung work (ablating the refusal direction yourself) the prior art is
OBLITERATUS + `run_local.py` in the `obliteratus:gpu` container — see that repo's `DEVELOPER.md`.
We don't need that here; the already-abliterated Ollama models are enough for scoring.

## How this tool uses it

`tradecraft/detect.py` exposes `detect(text, taxonomy, backend=...)`:

- `backend="cloud"` — via **OpenRouter** (key from `~/.claude/agents/.env`), JSON-mode; default
  model `google/gemini-2.5-flash` (override `TRADECRAFT_CLOUD_MODEL`). Validated 4/4 positives,
  3/3 negatives on the eval set.
- `backend="local"` — the Ollama pattern above, default model the 14b abliterate.
- `backend="auto"` (default) — try the cloud; on **refusal** (empty / non-JSON response) **or**
  missing key, fall back to the local uncensored model automatically. No human has to notice the
  refusal and intervene.

## Incorporate into the skills

This is the reusable shape every content/analysis skill should adopt when its subject can trip a
content filter (the documented docker/local-gemma fallback rule). The bias-study `abliteration-run`
skill and `run_study.py`'s channel abstraction are the existing homes; the `auto` dispatcher
(try-cloud-then-local-on-refusal) is the pattern.

DONE: the dispatcher is extracted into a shared `local_llm` helper.

- **In-package**: `tradecraft/local_llm.py` exposes `cloud()`, `local()`, `complete()`, and the
  `Refusal` exception. `detect.py` now imports it for transport and only owns the detection-specific
  prompt building (`build_user_prompt`, `_few_shot`) and hit parsing (`_parse_hits`). The public
  `detect(text, taxonomy, *, backend, model)` signature and `backend="auto"` fall-back behavior are
  unchanged; `detect.RefusalError` is an alias of `local_llm.Refusal` for back-compat.
- **Vendorable twin**: `.claude/skills/local-llm-fallback/local_llm.py` is the stdlib+requests copy
  for skills that cannot import the package. Keep the two in sync (same models, same env overrides,
  same try-cloud-then-local contract).
