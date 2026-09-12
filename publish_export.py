#!/usr/bin/env python3
"""Build a clean export tree for the public mirror, and refuse to build a leaky one.

A working tree accumulates operator material — maintainer skills, caches, run queues — so
publication goes through an explicit exclusion manifest rather than copying the directory.

    python publish_export.py --out <dir>         # build the export
    python publish_export.py --out <dir> --scan  # build, then run the leak scanner (gates)

PUBLISH-EXCLUDE.txt is required; a missing manifest is an error, not a permissive default.
PUBLISH-REDACT.txt is optional and rewrites provenance strings at the export boundary.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PUBLISH-EXCLUDE.txt"
REDACT_MANIFEST = ROOT / "PUBLISH-REDACT.txt"

#: Extensions treated as text for redaction. Everything else is copied byte-for-byte.
TEXT_EXT = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".html", ".js", ".css",
            ".toml", ".cfg", ".ini", ".sh", ".jsonl"}


def load_redactions():
    """(compiled regex, replacement) pairs, or [] when no manifest exists.

    Redaction happens at the export boundary, not in the source: the strings involved are
    provenance the working tree should keep.
    """
    if not REDACT_MANIFEST.exists():
        return []
    out = []
    for raw in REDACT_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" not in line:
            raise SystemExit("PUBLISH-REDACT.txt: no '=>' in %r" % line)
        pat, rep = line.split("=>", 1)
        out.append((re.compile(pat.strip()), rep.strip()))
    return out


def load_patterns() -> list[str]:
    if not MANIFEST.exists():
        raise SystemExit(
            "PUBLISH-EXCLUDE.txt is missing. Refusing to build an export with no exclusion\n"
            "list -- publishing whatever the working tree holds is the defect this script\n"
            "exists to prevent.")
    pats = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(line)
    if not pats:
        raise SystemExit("PUBLISH-EXCLUDE.txt contains no patterns.")
    return pats


def excluded(rel: str, pats: list[str]) -> bool:
    """rel is an export-relative POSIX path."""
    for p in pats:
        if p.endswith("/"):
            if rel == p.rstrip("/") or rel.startswith(p) or ("/" + p) in ("/" + rel + "/"):
                return True
            if fnmatch.fnmatch(rel + "/", p if p.startswith("**") else "*" + p):
                return True
        if fnmatch.fnmatch(rel, p):
            return True
        # `**/x/` style: match any path segment run
        if p.startswith("**/"):
            tail = p[3:].rstrip("/")
            parts = rel.split("/")
            if tail in parts or fnmatch.fnmatch(parts[-1], tail):
                return True
    return False


def build(out: Path, pats: list[str], reds) -> tuple[int, int, dict]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    kept = skipped = 0
    redacted: dict = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        if rel_dir == ".git" or rel_dir.startswith(".git/"):
            dirnames[:] = []
            continue
        # Prune excluded directories so we never descend into them.
        keep_dirs = []
        for d in dirnames:
            rd = f"{rel_dir}/{d}" if rel_dir else d
            if d == ".git" or excluded(rd + "/", pats) or excluded(rd, pats):
                skipped += 1
                continue
            keep_dirs.append(d)
        dirnames[:] = keep_dirs
        for fn in filenames:
            rel = f"{rel_dir}/{fn}" if rel_dir else fn
            if excluded(rel, pats):
                skipped += 1
                continue
            src = Path(dirpath) / fn
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if reds and src.suffix.lower() in TEXT_EXT:
                try:
                    text = src.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    shutil.copy2(src, dst)
                    kept += 1
                    continue
                new = text
                for rx, rep in reds:
                    new = rx.sub(rep, new)
                if new != text:
                    redacted[rel] = sum(1 for rx, _ in reds if rx.search(text))
                dst.write_text(new, encoding="utf-8", newline="")
            else:
                shutil.copy2(src, dst)
            kept += 1
    return kept, skipped, redacted


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="directory to build the export into")
    ap.add_argument("--scan", action="store_true",
                    help="run release-leak-scan over the export and fail on any leak")
    args = ap.parse_args(argv)

    pats = load_patterns()
    reds = load_redactions()
    out = Path(args.out).resolve()
    kept, skipped, redacted = build(out, pats, reds)
    print(f"export: {kept} file(s) written, {skipped} excluded by "
          f"{MANIFEST.name} ({len(pats)} pattern(s))")
    if reds:
        print(f"redaction: {len(reds)} rule(s), applied in {len(redacted)} file(s)")
        for rel in sorted(redacted)[:10]:
            print(f"    {rel}")
        if len(redacted) > 10:
            print(f"    ... and {len(redacted) - 10} more")
    print(f"  -> {out}")

    if not args.scan:
        print("\nNot scanned. Re-run with --scan before pushing anywhere.")
        return 0

    scanner = Path(os.path.expanduser("~/.claude/skills/release-leak-scan/leak-scan.py"))
    if not scanner.exists():
        print("\nLEAK SCANNER NOT FOUND -- refusing to report this export as clean.")
        return 1
    r = subprocess.run([sys.executable, str(scanner), str(out), "--profile", "gorrie"],
                       text=True)
    if r.returncode != 0:
        print("\nEXPORT IS NOT PUBLISHABLE. Fix the content, or add the path to "
              "PUBLISH-EXCLUDE.txt with the reason.")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
