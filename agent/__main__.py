"""CLI: python -m agent "your task"  (runs entirely on the local uncensored model)."""
from __future__ import annotations

import argparse

from .loop import run


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="agent", description="Local unmoderated tradecraft agent.")
    p.add_argument("task", help="task / question for the agent")
    p.add_argument("--persona", default=None, help="persona to load (e.g. gorrie); default: analyst")
    p.add_argument("--model", default=None, help="ollama model (default: TRADECRAFT_LOCAL_MODEL)")
    p.add_argument("--base", default=None, help="ollama base url (default: OLLAMA_BASE)")
    p.add_argument("--max-iters", type=int, default=8)
    p.add_argument("-v", "--verbose", action="store_true", help="print tool calls")
    a = p.parse_args(argv)
    print(run(a.task, model=a.model, base=a.base, max_iters=a.max_iters,
              verbose=a.verbose, persona=a.persona))


if __name__ == "__main__":
    main()
