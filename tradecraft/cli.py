"""Command line: list lenses, grade text/URLs, or run an offline demo.

  python -m tradecraft.cli lenses
  python -m tradecraft.cli demo
  python -m tradecraft.cli grade --file speech.txt --lens institutional_permeation
  python -m tradecraft.cli grade --url https://example.org/op-ed --lens cognitive_capture
  python -m tradecraft.cli subject --id Rubin --texts texts.jsonl            # offline (cues)
  python -m tradecraft.cli subject --id Rubin --texts texts.jsonl --backend auto

`grade` needs ANTHROPIC_API_KEY. `demo` runs offline on canned hits to show the grader's output
shape (a profile + receipts), no key required. `subject` runs the texts-by-person lane: all TEXT
lenses over a person's texts, graded per subject, never blended — offline by default (`--backend
cues`), no key required.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os

from .loader import load_lenses
from .grader import grade_document
from .schema import DetectionHit
from . import adapters

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS_DIR = os.path.join(REPO_ROOT, "detectors")


def _emit(obj) -> None:
    print(json.dumps(obj, indent=2, default=lambda o: dataclasses.asdict(o)
                      if dataclasses.is_dataclass(o) else str(o)))


def cmd_lenses(_args) -> None:
    lenses = load_lenses(DETECTORS_DIR)
    _emit({lid: {"name": t.name, "markers": [m.id for m in t.markers],
                 "detections": sum(len(m.detections) for m in t.markers)}
           for lid, t in lenses.items()})


def cmd_demo(_args) -> None:
    lenses = load_lenses(DETECTORS_DIR)
    lid = "institutional_permeation"
    tax = lenses[lid]
    # Canned hits across several markers — a dense specimen, to show breadth driving the index.
    hits = [
        DetectionHit("indefinite-horizon", 0.9, "consistency of action over an indefinite period of years"),
        DetectionHit("infiltrate-existing-institutions", 0.85, "infiltrating existing institutions"),
        DetectionHit("value-as-science", 0.8, "sound science"),
        DetectionHit("neutrality-claim", 0.7, "aligns itself with no particular party"),
        DetectionHit("astroturf", 0.6, "an independent grassroots movement"),
    ]
    prof = grade_document({lid: tax}, {lid: hits}, token_count=600,
                          doc_id="demo", subject="DEMO")
    _emit(prof)
    print("\nNote: a profile + receipts for human review. Not a verdict.", flush=True)


def cmd_grade(args) -> None:
    from .detect import detect  # lazy (needs anthropic)
    lenses = load_lenses(DETECTORS_DIR)
    if args.lens not in lenses:
        raise SystemExit(f"unknown lens {args.lens!r}; have: {', '.join(lenses)}")
    tax = lenses[args.lens]
    if args.url:
        doc = adapters.from_url(args.url)
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            doc = adapters.from_text(fh.read(), doc_id=args.file)
    else:
        raise SystemExit("provide --file or --url")
    hits = detect(doc["text"], tax, model=args.model)
    prof = grade_document({tax.id: tax}, {tax.id: hits},
                          token_count=adapters.token_estimate(doc["text"]),
                          doc_id=doc["doc_id"], url=doc.get("url"))
    _emit(prof)


def cmd_subject(args) -> None:
    """The texts-by-person lane: grade all of a subject's texts under the TEXT lenses."""
    from .subject import grade_person, text_lenses  # lazy (model backends need optional deps)
    lenses = text_lenses(load_lenses(DETECTORS_DIR))
    texts: list[dict] = []
    with open(args.texts, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            # Accept the ratchet-mcp store schema: keep only this subject's texts when keyed.
            if args.id and rec.get("person_id") and rec["person_id"] != args.id:
                continue
            texts.append(rec)
    if not texts:
        raise SystemExit(f"no texts for subject {args.id!r} in {args.texts}")
    profile, docs = grade_person(lenses, args.id, texts, backend=args.backend, model=args.model)
    _emit({"subject": profile, "documents": docs})
    print("\nNote: per-lens profile + receipts for human review. Never blended; not a verdict.",
          flush=True)


def cmd_profile(args) -> None:
    """The combined profile: graph lane + text lane for one subject, per lens, never blended."""
    import tempfile
    from .profile import profile_subject
    graph_path = args.graph
    tmp = None
    if args.ratchet_dir and not graph_path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        tmp.close()
        n = adapters.write_ratchet_graph(args.ratchet_dir, tmp.name)
        print(f"# adapted ratchet graph: {n} entities -> {tmp.name}", flush=True)
        graph_path = tmp.name
    texts = None
    if args.texts:
        texts = adapters.from_jsonl(args.texts, subject=args.id)
        texts = [{"id": d["doc_id"], "text": d["text"], "url": d.get("url"), "date": d.get("date")}
                 for d in texts]
    lenses = tuple(args.graph_lenses.split(",")) if args.graph_lenses else ("network_brokerage",)
    out = profile_subject(args.id, detectors_dir=DETECTORS_DIR, graph_path=graph_path,
                          graph_lenses=lenses, texts=texts, backend=args.backend, model=args.model)
    _emit(out)
    if tmp:
        os.unlink(tmp.name)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="tradecraft", description="Detect & grade influence tradecraft.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lenses", help="list installed lenses").set_defaults(fn=cmd_lenses)
    sub.add_parser("demo", help="offline demo of the grader output").set_defaults(fn=cmd_demo)
    g = sub.add_parser("grade", help="score a document under a lens")
    g.add_argument("--lens", required=True)
    g.add_argument("--file")
    g.add_argument("--url")
    g.add_argument("--model", default="claude-sonnet-4-6")
    g.set_defaults(fn=cmd_grade)
    s = sub.add_parser("subject", help="grade a person's texts (texts-by-person lane)")
    s.add_argument("--id", required=True, help="subject id (e.g. a ratchet person id)")
    s.add_argument("--texts", required=True, help="JSONL of texts ({text,[id],[url],[date],[person_id]})")
    s.add_argument("--backend", default="cues",
                   choices=["cues", "cloud", "local", "auto"],
                   help="cues = deterministic/offline (default); others need a model")
    s.add_argument("--model", default=None)
    s.set_defaults(fn=cmd_subject)
    pr = sub.add_parser("profile", help="combined graph+text profile for one subject")
    pr.add_argument("--id", required=True, help="subject id present in the graph and/or texts store")
    pr.add_argument("--ratchet-dir", help="ratchet-mcp data dir (people/institutions/edges.jsonl) to adapt")
    pr.add_argument("--graph", help="a pre-adapted entities/edges graph JSON (instead of --ratchet-dir)")
    pr.add_argument("--texts", help="JSONL texts store for the text lane")
    pr.add_argument("--graph-lenses", default="network_brokerage,revolving_door",
                    help="comma list of graph lenses to run")
    pr.add_argument("--backend", default="cues", choices=["cues", "cloud", "local", "auto"])
    pr.add_argument("--model", default=None)
    pr.set_defaults(fn=cmd_profile)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":  # pragma: no cover
    main()
