"""The receipt loop: intake -> queue -> adjudication -> ledger -> counts, on temp files.

No network (every intake here passes --no-verify), no GitHub, and never the real ledger: the
accept path is proven against a copy so the defamation-gated leaderboard.jsonl is not touched
by a test. The real detectors and actors.json ARE used, because the point of --accept is that a
record fails score.validate exactly as a hand-typed one would.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import pytest  # noqa: E402

import import_receipts as ir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_LEDGER = os.path.join(ROOT, "leaderboard", "data", "leaderboard.jsonl")

COLLECTOR_RECEIPT = {
    "schema": "leaderboard-receipt/1",
    "institution": "Wikipedia (English)",
    "span": "administrators and the Arbitration Committee operate under pseudonyms",
    "receipts": ["https://en.wikipedia.org/wiki/Arbitration_Committee_(Wikipedia)",
                 "https://web.archive.org/web/20260101000000/https://en.wikipedia.org/wiki/Arbitration_Committee_(Wikipedia)"],
    "assurance": "FACT", "note": "pseudonymous governance corps", "date": "2026-09-07",
    "submitter": "test", "lens": None, "marker": None, "move": None, "actor": None,
    "severity": None, "self_correction": None,
    "capture_degree": {"score": 12, "band": "low", "asserted": 0, "attributed": 0},
}
OLD_SHAPE = {"claim": "The ESRC funded a project on the English crown's credit finance.",
             "actor": "ESRC", "action": "funded the project", "source_url": "https://centaur.reading.ac.uk/16785/",
             "archive_url": "", "tier": "FACT", "date": "2026-09-07", "submitter": ""}


@pytest.fixture
def paths(tmp_path):
    ledger = tmp_path / "leaderboard.jsonl"
    ledger.write_text(open(REAL_LEDGER, encoding="utf-8").read(), encoding="utf-8")
    return {"queue": tmp_path / "queue.jsonl", "ledger": ledger, "counts": tmp_path / "receipt_queue.json"}


def _argv(paths, *rest):
    return ["--queue", str(paths["queue"]), "--ledger", str(paths["ledger"]),
            "--counts", str(paths["counts"])] + list(rest)


def test_intake_queues_never_ledgers(paths, tmp_path):
    f = tmp_path / "sub.json"
    f.write_text(json.dumps(COLLECTOR_RECEIPT), encoding="utf-8")
    before = ir.read_jsonl(paths["ledger"])
    assert ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify")) == 0
    q = ir.read_jsonl(paths["queue"])
    assert len(q) == 1 and q[0]["status"] == "queued" and q[0]["adjudication"] is None
    assert q[0]["checks"]["schema"] == []
    assert q[0]["checks"]["archive_url"].startswith("wayback")
    assert ir.read_jsonl(paths["ledger"]) == before, "intake must never touch the ledger"
    # idempotent: the same receipt is not queued twice
    assert ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify")) == 0
    assert len(ir.read_jsonl(paths["queue"])) == 1


def test_old_collector_shape_is_translated_and_issue_body_parsed(paths, tmp_path):
    body = "### Capture receipt submission\n\n```json\n" + json.dumps(OLD_SHAPE, indent=2) + "\n```\n<!-- checklist -->"
    f = tmp_path / "issue.md"
    f.write_text(body, encoding="utf-8")
    assert ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify", "--origin", "github:test#1")) == 0
    q = ir.read_jsonl(paths["queue"])[0]
    r = q["receipt"]
    assert r["institution"] == "ESRC" and r["span"].startswith("The ESRC") and r["assurance"] == "FACT"
    assert r["receipts"] == ["https://centaur.reading.ac.uk/16785/"]
    assert "translated" in r["schema"]
    assert q["checks"]["archive_url"].startswith("missing")
    assert q["origin"] == "github:test#1"


def test_schema_errors_are_recorded_not_dropped(paths, tmp_path):
    bad = dict(COLLECTOR_RECEIPT, receipts=[], institution="")
    f = tmp_path / "bad.json"
    f.write_text(json.dumps(bad), encoding="utf-8")
    ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify"))
    q = ir.read_jsonl(paths["queue"])[0]
    assert any("institution" in e for e in q["checks"]["schema"])
    assert any("no source URL" in e for e in q["checks"]["schema"])
    # and such a receipt cannot be accepted
    with pytest.raises(SystemExit):
        ir.main(_argv(paths, "adjudicate", q["id"], "--accept", "--by", "t", "--reason", "x",
                      "--lens", "reference_capture", "--marker", "pseudonymous_enforcement",
                      "--move", "permeation", "--actor", "internal_clique", "--severity", "0.5"))


def test_reject_records_reason_and_counts(paths, tmp_path):
    f = tmp_path / "sub.json"
    f.write_text(json.dumps(COLLECTOR_RECEIPT), encoding="utf-8")
    ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify"))
    rid = ir.read_jsonl(paths["queue"])[0]["id"]
    with pytest.raises(SystemExit):   # a reason is required
        ir.main(_argv(paths, "adjudicate", rid, "--reject", "--by", "t", "--reason", "  "))
    assert ir.main(_argv(paths, "adjudicate", rid, "--reject", "--by", "t",
                         "--reason", "duplicate of an existing ledger record")) == 0
    q = ir.read_jsonl(paths["queue"])[0]
    assert q["status"] == "rejected" and q["adjudication"]["reason"].startswith("duplicate")
    with pytest.raises(SystemExit):   # cannot adjudicate twice
        ir.main(_argv(paths, "adjudicate", rid, "--reject", "--by", "t", "--reason", "again"))
    c = ir.counts(paths)
    assert (c["submitted"], c["queued"], c["accepted"], c["rejected"]) == (1, 0, 0, 1)
    assert list(c["rejected_by_reason"].values()) == [1]


def test_accept_appends_a_validated_ledger_record(paths, tmp_path):
    f = tmp_path / "sub.json"
    f.write_text(json.dumps(COLLECTOR_RECEIPT), encoding="utf-8")
    ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify"))
    rid = ir.read_jsonl(paths["queue"])[0]["id"]
    # a marker that does not exist in the lens fails score.validate and never reaches the ledger
    with pytest.raises(SystemExit):
        ir.main(_argv(paths, "adjudicate", rid, "--accept", "--by", "t", "--reason", "ok",
                      "--lens", "reference_capture", "--marker", "not_a_real_marker",
                      "--move", "permeation", "--actor", "internal_clique", "--severity", "0.5"))
    assert ir.read_jsonl(paths["queue"])[0]["status"] == "queued"
    n_before = len(ir.read_jsonl(paths["ledger"]))
    assert ir.main(_argv(paths, "adjudicate", rid, "--accept", "--by", "t", "--reason", "verified",
                         "--lens", "reference_capture", "--marker", "pseudonymous_enforcement",
                         "--move", "permeation", "--actor", "internal_clique", "--severity", "0.6")) == 0
    ledger = ir.read_jsonl(paths["ledger"])
    assert len(ledger) == n_before + 1
    rec = ledger[-1]
    assert rec["institution"] == "Wikipedia (English)" and rec["lens"] == "reference_capture"
    assert rec["receipts"] == COLLECTOR_RECEIPT["receipts"] and rec["assurance"] == "FACT"
    q = ir.read_jsonl(paths["queue"])[0]
    assert q["status"] == "accepted" and q["adjudication"]["ledger_key"][1] == "pseudonymous_enforcement"


def test_counts_check_gate(paths, tmp_path):
    f = tmp_path / "sub.json"
    f.write_text(json.dumps(COLLECTOR_RECEIPT), encoding="utf-8")
    ir.main(_argv(paths, "intake", "--file", str(f), "--no-verify"))
    assert ir.main(_argv(paths, "--check")) == 1            # nothing published yet
    assert ir.main(_argv(paths, "counts", "--write")) == 0
    assert ir.main(_argv(paths, "--check")) == 0
    published = json.loads(paths["counts"].read_text(encoding="utf-8"))
    assert published["submitted"] == 1 and "public intake is not open" in published["intake"]
    # a hand edit to the published counts is caught
    published["accepted"] = 99
    paths["counts"].write_text(json.dumps(published, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    assert ir.main(_argv(paths, "--check")) == 1
