#!/usr/bin/env python3
"""Receipt intake -> adjudication queue -> ledger -> counts. The loop behind the receipt collector.

WHY THIS EXISTS (plan 3.3, the Book 4 keystone)
-----------------------------------------------
/tech/receipt-collector/ builds a portable evidence receipt and stops at the clipboard. The
series ends by telling a reader to work the faculty in public where it can be checked; a tool
that ends at the clipboard demonstrates a form, not the answer. This closes the loop the page
promised: a submitted receipt enters an ADJUDICATION QUEUE -- never the ledger directly -- a
human accepts or rejects it with a reason, an accepted record enters `leaderboard.jsonl`
through the same validation `score.py` applies to every record, and the counts (submitted /
queued / accepted / rejected, by reason) are published for the page to print.

THE SHAPE, ONCE
---------------
The collector emits exactly the ledger record shape (`leaderboard/README.md`, "Record
schema"), with the adjudicator's fields null:

    schema           "leaderboard-receipt/1"
    institution      the subject                      (the collector's Actor field)
    span             the exact quoted claim
    receipts         [source_url, archive_url]        (archive optional at submission)
    assurance        FACT | ATTRIBUTED | RUMOR | null (the collector's Tier)
    note             what they did                    (the collector's Action field)
    date             YYYY-MM-DD
    submitter        handle, optional
    lens, marker, move, actor, severity, self_correction   -- null until adjudicated
    capture_degree   the claim's own loading, scanned client-side

A queue record wraps that receipt with an id, its origin, the mechanical checks (schema,
source resolves, archive is a real Wayback capture) and the adjudication, if any.

WHAT IS AND IS NOT PUBLIC
-------------------------
Intake here is LOCAL: a file of receipts (JSON, JSONL, or a GitHub-issue body containing the
receipt's ```json block). `intake --github` is implemented for the day the public mirror is
current and the author opens intake; it reads issues labelled `receipt` through `gh api`,
read-only, and is not run by anything automatic. Nothing in this file creates an issue, posts
a comment, or pushes.

ADJUDICATION IS A HUMAN STEP
----------------------------
`adjudicate <id> --accept ...` requires the adjudicator to supply the lens, marker, move,
actor and severity -- the fields that turn a receipt into a scored record -- and validates them
against the detectors and `actors.json` exactly as `score.py` does. `--reject --reason` records
why. Both are appended to the queue record; nothing is deleted. The ledger stays the source of
truth `leaderboard-sync` gates; this tool only ever appends to it, and only on --accept.

    python tools/import_receipts.py intake --file receipts.jsonl [--no-verify] [--origin bookmarklet]
    python tools/import_receipts.py intake --github --repo gorrie/tradecraft     # read-only; not automatic
    python tools/import_receipts.py list [--status queued]
    python tools/import_receipts.py adjudicate rcpt-xxxx --reject --by ian --reason "duplicate of ..."
    python tools/import_receipts.py adjudicate rcpt-xxxx --accept --by ian --reason "..." \
        --lens reference_capture --marker pseudonymous_enforcement --move permeation \
        --actor internal_clique --severity 0.6 [--self-correction 0.0]
    python tools/import_receipts.py counts [--write]     # website/data/receipt_queue.json
    python tools/import_receipts.py --check              # counts file matches the queue (gate)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # tradecraft/
SERIES = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "leaderboard"))

QUEUE = ROOT / "leaderboard" / "data" / "queue.jsonl"
LEDGER = ROOT / "leaderboard" / "data" / "leaderboard.jsonl"
COUNTS = SERIES / "website" / "data" / "receipt_queue.json"

SCHEMA = "leaderboard-receipt/1"
ASSURANCE = ("FACT", "ATTRIBUTED", "RUMOR")
MOVES = ("permeation", "language", "ratchet")
RECEIPT_FIELDS = ("schema", "institution", "span", "receipts", "assurance", "note", "date",
                  "submitter", "lens", "marker", "move", "actor", "severity", "self_correction",
                  "capture_degree")
ADJUDICATOR_FIELDS = ("lens", "marker", "move", "actor", "severity")
UA = "evilrobots.lol receipt-intake (+https://evilrobots.lol/tech/receipt-collector/)"
WAYBACK = re.compile(r"^https?://web\.archive\.org/web/\d{4,14}(?:id_|if_|im_)?/\S+")
INTAKE_STATE = ("local intake only -- public intake is not open; the queue runs against the "
                "local ledger and the public mirror is not current")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# ── receipt parsing ──────────────────────────────────────────────────────────────────────────

def coerce_receipt(obj: dict) -> dict:
    """Accept the ledger shape, or the collector's pre-2026-09-07 shape, and return the ledger
    shape. The old shape is translated, not rejected, so a receipt made before the change still
    enters the queue -- but it is marked as translated in the schema field."""
    if obj.get("schema") == SCHEMA:
        r = {k: obj.get(k) for k in RECEIPT_FIELDS}
    else:
        rec = [u for u in (obj.get("source_url"), obj.get("archive_url")) if u]
        r = {
            "schema": SCHEMA + " (translated from claim/actor/action shape)",
            "institution": obj.get("actor"), "span": obj.get("claim"),
            "receipts": rec or obj.get("receipts") or [],
            "assurance": obj.get("tier") or obj.get("assurance"),
            "note": obj.get("action") or obj.get("note"), "date": obj.get("date"),
            "submitter": obj.get("submitter"), "lens": None, "marker": None, "move": None,
            "actor": None, "severity": None, "self_correction": None,
            "capture_degree": obj.get("capture_degree"),
        }
    r["receipts"] = [u for u in (r.get("receipts") or []) if isinstance(u, str) and u.strip()]
    return r


def parse_submissions(text: str) -> list[dict]:
    """A JSON object, a JSON array, JSONL, or a GitHub issue body with a ```json block."""
    text = text.strip()
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if blocks:
        return [json.loads(b) for b in blocks]
    if text.startswith("["):
        return list(json.loads(text))
    if text.startswith("{") and text.count("\n{") == 0:
        return [json.loads(text)]
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def receipt_id(r: dict) -> str:
    key = "|".join([str(r.get("institution") or ""), str(r.get("span") or ""),
                    (r.get("receipts") or [""])[0]])
    return "rcpt-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def schema_errors(r: dict) -> list[str]:
    e = []
    if not r.get("institution"):
        e.append("institution missing")
    if not r.get("span"):
        e.append("span (the quoted claim) missing")
    if not r.get("receipts"):
        e.append("no source URL -- a record with no receipt is a build error, per the ledger schema")
    if r.get("assurance") not in ASSURANCE and r.get("assurance") is not None:
        e.append("assurance must be FACT | ATTRIBUTED | RUMOR")
    if r.get("date") and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(r["date"])):
        e.append("date must be YYYY-MM-DD")
    return e


# ── URL checks (serial, polite, honest about failure) ─────────────────────────────────────────

def _head(url: str) -> str:
    try:
        import requests
    except ImportError:
        return "unchecked (requests not installed)"
    try:
        r = requests.head(url, allow_redirects=True, timeout=15, headers={"User-Agent": UA})
        if r.status_code in (403, 405) or r.status_code >= 500:
            r = requests.get(url, allow_redirects=True, timeout=20, headers={"User-Agent": UA}, stream=True)
        code = r.status_code
        if code == 429:
            return "rate-limited (429) -- unchecked, back off"
        return ("ok %d" % code) if code < 400 else ("dead %d" % code)
    except Exception as exc:                                        # noqa: BLE001
        return "unreachable (%s)" % type(exc).__name__


def check_urls(r: dict, verify: bool) -> dict:
    rec = r.get("receipts") or []
    src = rec[0] if rec else None
    arc = next((u for u in rec[1:] if WAYBACK.match(u)), None)
    non_wayback = [u for u in rec[1:] if not WAYBACK.match(u)]
    out = {"source_url": "missing" if not src else ("unverified" if not verify else _head(src))}
    if arc:
        out["archive_url"] = "wayback, unverified" if not verify else "wayback, " + _head(arc)
    elif non_wayback:
        out["archive_url"] = "not a Wayback capture: " + non_wayback[0][:80]
    else:
        out["archive_url"] = "missing -- cannot be graded FACT until the source is archived"
    if verify and src:
        time.sleep(1.0)                                              # serial, one per second
    return out


# ── queue operations ─────────────────────────────────────────────────────────────────────────

def intake(paths: dict, submissions: list[dict], origin: str, verify: bool) -> list[dict]:
    queue = read_jsonl(paths["queue"])
    have = {q["id"] for q in queue}
    added = []
    for raw in submissions:
        r = coerce_receipt(raw)
        rid = receipt_id(r)
        if rid in have:
            print("  skip %s -- already in the queue" % rid)
            continue
        rec = {"id": rid, "received": now(), "origin": origin, "status": "queued",
               "checks": {"schema": schema_errors(r), **check_urls(r, verify)},
               "adjudication": None, "receipt": r}
        append_jsonl(paths["queue"], rec)
        have.add(rid)
        added.append(rec)
        print("  queued %s  %s -- %s" % (rid, (r.get("institution") or "?")[:40],
                                        "; ".join(rec["checks"]["schema"]) or "schema ok"))
    return added


def github_submissions(repo: str) -> tuple[list[dict], list[str]]:
    """Read issues labelled `receipt` from the public repo. READ-ONLY, via `gh api`. Not run by
    anything automatic; the caller chose --github. Returns (submissions, origins)."""
    cmd = ["gh", "api", "-X", "GET", f"repos/{repo}/issues", "-f", "labels=receipt",
           "-f", "state=open", "-f", "per_page=100"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode:
        sys.exit("gh api failed: " + (r.stderr or r.stdout)[:300])
    subs, origins = [], []
    for issue in json.loads(r.stdout or "[]"):
        for s in parse_submissions(issue.get("body") or ""):
            subs.append(s)
            origins.append("github:%s#%d" % (repo, issue["number"]))
    return subs, origins


def adjudicate(paths: dict, rid: str, accept: bool, by: str, reason: str, fields: dict) -> dict:
    queue = read_jsonl(paths["queue"])
    idx = next((i for i, q in enumerate(queue) if q["id"] == rid), None)
    if idx is None:
        sys.exit("no queue record %s" % rid)
    q = queue[idx]
    if q["status"] != "queued":
        sys.exit("%s is already %s (%s)" % (rid, q["status"], (q.get("adjudication") or {}).get("reason")))
    if not reason.strip():
        sys.exit("a reason is required -- an unexplained decision is not adjudication")
    decision = {"at": now(), "by": by, "decision": "accepted" if accept else "rejected",
                "reason": reason.strip(), "ledger_key": None}
    if accept:
        r = dict(q["receipt"])
        missing = [f for f in ADJUDICATOR_FIELDS if fields.get(f) in (None, "")]
        if missing:
            sys.exit("accept needs the adjudicator's fields: " + ", ".join(missing))
        if q["checks"]["schema"]:
            sys.exit("cannot accept a receipt with schema errors: " + "; ".join(q["checks"]["schema"]))
        if r.get("assurance") not in ASSURANCE:
            sys.exit("accept needs a tier: assurance must be FACT | ATTRIBUTED | RUMOR")
        if fields["move"] not in MOVES:
            sys.exit("move must be one of %s" % ", ".join(MOVES))
        record = {
            "institution": r["institution"], "marker": fields["marker"], "move": fields["move"],
            "actor": fields["actor"], "assurance": r["assurance"],
            "severity": float(fields["severity"]),
            "self_correction": float(fields.get("self_correction") or 0.0),
            "span": r["span"], "receipts": list(r["receipts"]),
            "note": (r.get("note") or "") + (" [receipt %s, %s]" % (rid, r.get("date") or "undated")),
            "lens": fields["lens"],
        }
        # The same validation score.py applies to every record -- lens/marker coherence, actor
        # vocabulary, assurance, receipt-gate. A record that fails it never reaches the ledger.
        import score                                                 # leaderboard/score.py
        ledger = read_jsonl(paths["ledger"])
        problems = score.validate(ledger + [record], score.load_roles())
        problems = [p for p in problems if record["institution"] in p or fields["marker"] in p]
        if problems:
            sys.exit("record fails score.validate: " + "; ".join(problems))
        append_jsonl(paths["ledger"], record)
        decision["ledger_key"] = [record["institution"], record["marker"], record["span"]]
    q["status"] = decision["decision"]
    q["adjudication"] = decision
    queue[idx] = q
    write_jsonl(paths["queue"], queue)
    print("%s %s by %s: %s" % (rid, decision["decision"], by, decision["reason"]))
    if accept:
        print("  appended to %s; re-run leaderboard/score.py so leaderboard-sync stays green"
              % paths["ledger"].name)
    return q


def counts(paths: dict) -> dict:
    queue = read_jsonl(paths["queue"])
    by_reason = {}
    for q in queue:
        if q["status"] == "rejected":
            k = (q.get("adjudication") or {}).get("reason", "")[:80]
            by_reason[k] = by_reason.get(k, 0) + 1
    return {
        "generated_by": "tradecraft/tools/import_receipts.py counts --write",
        "queue": "tradecraft/leaderboard/data/queue.jsonl",
        "intake": INTAKE_STATE,
        "submitted": len(queue),
        "queued": sum(1 for q in queue if q["status"] == "queued"),
        "accepted": sum(1 for q in queue if q["status"] == "accepted"),
        "rejected": sum(1 for q in queue if q["status"] == "rejected"),
        "rejected_by_reason": dict(sorted(by_reason.items())),
        "origins": dict(sorted(
            ((o, sum(1 for q in queue if q.get("origin") == o))
             for o in {q.get("origin") for q in queue}))),
        "latest_received": max((q["received"] for q in queue), default=None),
    }


def counts_text(c: dict) -> str:
    return json.dumps(c, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--queue", default=str(QUEUE))
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--counts", default=str(COUNTS))
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the published counts file does not match the queue")
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("intake")
    i.add_argument("--file", help="JSON object / array / JSONL / issue body")
    i.add_argument("--github", action="store_true", help="read `receipt` issues via gh api (read-only)")
    i.add_argument("--repo", default="gorrie/tradecraft")
    i.add_argument("--origin", default=None)
    i.add_argument("--no-verify", action="store_true", help="skip the network checks on URLs")
    ls = sub.add_parser("list")
    ls.add_argument("--status", default=None)
    ad = sub.add_parser("adjudicate")
    ad.add_argument("id")
    g = ad.add_mutually_exclusive_group(required=True)
    g.add_argument("--accept", action="store_true")
    g.add_argument("--reject", action="store_true")
    ad.add_argument("--by", required=True)
    ad.add_argument("--reason", required=True)
    for f in ("lens", "marker", "move", "actor", "severity", "self-correction"):
        ad.add_argument("--" + f)
    c = sub.add_parser("counts")
    c.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    paths = {"queue": Path(a.queue), "ledger": Path(a.ledger), "counts": Path(a.counts)}

    if a.check:
        want = counts_text(counts(paths))
        have = paths["counts"].read_text(encoding="utf-8") if paths["counts"].is_file() else ""
        if want != have:
            print("receipt_queue.json is stale -- run tools/import_receipts.py counts --write")
            return 1
        print("receipt_queue.json matches the queue (%d submitted)" % counts(paths)["submitted"])
        return 0

    if a.cmd == "intake":
        if a.github:
            subs, origins = github_submissions(a.repo)
            for s, o in zip(subs, origins):
                intake(paths, [s], o, verify=not a.no_verify)
        elif a.file:
            text = io.open(a.file, encoding="utf-8").read()
            intake(paths, parse_submissions(text), a.origin or ("local:" + os.path.basename(a.file)),
                   verify=not a.no_verify)
        else:
            sys.exit("intake needs --file or --github")
        return 0
    if a.cmd == "list":
        for q in read_jsonl(paths["queue"]):
            if a.status and q["status"] != a.status:
                continue
            r = q["receipt"]
            print("%s  %-9s %-28s %s" % (q["id"], q["status"], (r.get("institution") or "?")[:28],
                                         (r.get("span") or "")[:60]))
        return 0
    if a.cmd == "adjudicate":
        fields = {"lens": a.lens, "marker": a.marker, "move": a.move, "actor": a.actor,
                  "severity": a.severity, "self_correction": a.self_correction}
        adjudicate(paths, a.id, a.accept, a.by, a.reason, fields)
        return 0
    if a.cmd == "counts":
        text = counts_text(counts(paths))
        if a.write:
            paths["counts"].parent.mkdir(parents=True, exist_ok=True)
            paths["counts"].write_text(text, encoding="utf-8")
            print("wrote " + str(paths["counts"]))
        print(text)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
