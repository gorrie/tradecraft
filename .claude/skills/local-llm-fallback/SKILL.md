# Local LLM Fallback

When a task's *subject* can trip a content filter — occult / influence-operation / cyber /
adversarial / "evil weirdos" analysis — the cloud model will sometimes refuse. This skill is the
one reusable answer: **try the cloud, and on refusal fall back to a local uncensored model**, so
the work never dead-ends on a content-policy bounce. It replaces the per-skill, re-derived
docker/local-gemma fallback with one helper.

## TRIGGER when

- A sub-agent or model call returns "content restriction" / "Usage Policy" / "I can't help with
  that" / an empty or hedged non-answer on legitimate analysis material.
- You are about to analyze, score, or summarize material you already know is filter-prone (the
  permeation/occult/influence corpora; the tradecraft detector's lenses; adversarial security text).
- A skill's documented fallback says "use the local model."

## SKIP

- Ordinary prose/editing/build tasks the cloud handles fine. Don't route everything local —
  the local abliterated models are less capable; use them when the cloud refuses, not by default.

## How to use

```python
import sys; sys.path.insert(0, "<path-to>/local-llm-fallback")
from local_llm import complete

text = complete("Analyze this passage for influence tradecraft: ...",
                system="You are an ideology-blind analyst.")   # backend='auto' (default)
data = complete(prompt, json_mode=True)                        # force valid JSON output (local path)
```

`backend`: **`auto`** (default — cloud, then local on refusal/no-key/no-SDK) · `cloud` · `local`.

## What's viable (validated 2026-06-17, RTX 4090)

- **Ollama** on `localhost:11434`. Default local model **`huihui_ai/qwen2.5-abliterate:14b`** —
  uncensored *and* tools-capable; smoke-tested returning clean structured JSON with zero refusal
  on permeation+esoteric text. Faster/sloppier alternative: the `:7b`. Others pulled: `wash-*-ablit`.
- The cloud path is **OpenRouter** (key from `~/.claude/agents/.env`), default `google/gemini-2.5-flash`.
  Auto-fallback fires on a refusal (empty or non-JSON response) or a missing key.
- Env overrides: `OLLAMA_BASE`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_CLOUD_MODEL`, `OPENROUTER_API_KEY`.

## Hard rules / discipline

- **Local is the fallback, not the default** — the uncensored models are less capable; reach for
  them when the cloud won't engage, not to skip the cloud.
- **The output is still subject to every downstream discipline** — sourcing, attribution,
  defamation rules, no-ethnic-essence, no-Gaza-Health-Ministry-tolls. Uncensored ≠ unsourced.
  A local model will happily assert; you still verify and attribute exactly as always.
- **Clear failures, not stack traces** — the helper preflights Ollama and the model and raises an
  actionable message (daemon down → `ollama serve`; model missing → `ollama pull <model>`).
- Keys come from the environment; nothing is hardcoded or logged.

## Lineage

Pattern lifted from `tradecraft/detect.py` (the detector's `backend="auto"`) + the bias study's
`run_study.call_ollama`. This is the canonical version; the bias-study `abliteration-run` skill and
the polish skills' docker-fallback notes are siblings. See `tradecraft/LOCAL_INFERENCE.md`.

## Setup note

`local_llm.py` sits beside this file. To make this skill runtime-loadable, junction this directory
into `~/.claude/skills/` per the workspace's skill convention (skills live in the project repo;
`~/.claude/skills/` is populated by junctions — never author skills directly in `~/.claude/`).
