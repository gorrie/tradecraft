#!/usr/bin/env python3
"""CP5's other half: a floor for `revolving_door`, whose null is not the brokerage one.

WHY THIS IS A SEPARATE HARNESS AND NOT A `--lens` FLAG ON graph_floor.py
------------------------------------------------------------------------
`eval/graph_floor.py` measures `network_brokerage`, and two of its four perturbations are
asserted INVARIANTS -- relabelling every node and flipping every edge must move the index by
exactly zero. That is correct there because brokerage reads an UNDIRECTED adjacency graph.

It is false here. `revolving_door` is directional by construction: a career move is an edge
whose SOURCE is the subject (`structural.MOVE_RELS`), and a funding tie counts when the subject
is the TARGET of a `funded-by` edge. Flip every edge and a person's employment history becomes
their employers' history. So flip-edges is not an invariant for this lens, it is a change of
meaning -- and handing `revolving_door` the brokerage floor would have asserted an invariant
that is false, then reported the resulting movement as noise.

Which is the same category error this project has now made twice and caught twice: the
/tech/instrument renderer nearly printed a firing-rate MDE as though it qualified an index, and
`rollback_asymmetry` was nearly taught Federal Register cues because FR measures had been filed
against a prose lens. A resolution belongs to one measurement.

THE NULL, and why these four
----------------------------
An entity graph built from dossiers is permanently incomplete, and the order research lands in
has nothing to do with any particular subject. So:

  **A subject's career-trajectory read must not swing on whether some unrelated person's
  dossier happens to have been entered yet, nor on the order edges sit in the file.**

  relabel          opaque node ids. Directionality and rel types are untouched, so this IS an
                   invariant here -- any movement is a bug, not a floor.
  shuffle-edges    the same edges in a different file order. The lens reports a "chain", so if
                   ordering changes the read then the trajectory claim is an artifact of file
                   order. Also an invariant, and the analogue of sentence-order for text.
  drop-far-move    delete a career-move edge NOT incident to the subject: another person's
                   dossier that had not landed yet.
  add-far-move     add a career-move edge between two other nodes: the next dossier landing
                   somewhere else.

Deliberately NOT included: flip-edges (changes meaning, see above) and any perturbation that
touches the subject's own edges (that is the signal, not the noise).

    python eval/revolving_floor.py
    python eval/revolving_floor.py --subjects 12 --trials 15
    python eval/revolving_floor.py --check       # exit 1 if an invariant moved
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from tradecraft import structural as S                    # noqa: E402
from tradecraft.grader import grade_document_for_lens      # noqa: E402
from tradecraft.loader import load_lenses                  # noqa: E402

from graph_floor import mde, pctile                        # noqa: E402

SEED = 20260904
ALPHA = 0.05
GRAPH = os.path.join(ROOT, "data", "research-entities.json")
OUT = os.path.join(HERE, "graph-floors.json")

#: A subject with no career-move edges has nothing for this lens to read, so it cannot
#: contribute to a floor. Same rule as MIN_LIVE_DOCS for the text lenses.
MIN_LIVE_SUBJECTS = 5


def load_graph():
    return json.load(io.open(GRAPH, encoding="utf-8"))


def index_of(graph, subject_id, taxonomy):
    """revolving_door's index for one subject, against an in-memory graph."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(graph, fh)
        hits = S.detect_subject(path, subject_id)
    finally:
        os.unlink(path)
    # Token count is meaningless for a graph lens; density is not part of this read, so pass a
    # constant and let breadth and intensity carry the index. Constant across perturbations,
    # which is what matters for a floor.
    return grade_document_for_lens(taxonomy, hits, 1000).index


def _move_edges(graph):
    return [e for e in graph["edges"]
            if e.get("rel") in S.MOVE_RELS or not e.get("rel")]


def _incident(graph, subject_id):
    out = {subject_id}
    for e in graph["edges"]:
        if e.get("source") == subject_id:
            out.add(e.get("target"))
        elif e.get("target") == subject_id:
            out.add(e.get("source"))
    return out


def relabel(graph, subject_id, rng):
    ids = sorted(e["id"] for e in graph["entities"])
    mapping = {old: "n%06d" % i for i, old in enumerate(ids)}
    out = copy.deepcopy(graph)
    for ent in out["entities"]:
        ent["id"] = mapping[ent["id"]]
    kept = []
    for edge in out["edges"]:
        if edge.get("source") in mapping and edge.get("target") in mapping:
            edge["source"] = mapping[edge["source"]]
            edge["target"] = mapping[edge["target"]]
            kept.append(edge)          # rel and direction preserved: that is the point
    out["edges"] = kept
    return out, mapping[subject_id]


def shuffle_edges(graph, subject_id, rng):
    out = copy.deepcopy(graph)
    rng.shuffle(out["edges"])
    return out, subject_id


def drop_far_move(graph, subject_id, rng):
    near = _incident(graph, subject_id)
    far = [i for i, e in enumerate(graph["edges"])
           if e.get("source") not in near and e.get("target") not in near
           and (e.get("rel") in S.MOVE_RELS or not e.get("rel"))]
    if not far:
        return None, subject_id
    victim = rng.choice(far)
    out = copy.deepcopy(graph)
    del out["edges"][victim]
    return out, subject_id


def add_far_move(graph, subject_id, rng):
    near = _incident(graph, subject_id)
    others = sorted(e["id"] for e in graph["entities"] if e["id"] not in near)
    if len(others) < 2:
        return None, subject_id
    a, b = rng.sample(others, 2)
    out = copy.deepcopy(graph)
    out["edges"].append({"source": a, "target": b, "rel": "employed-by"})
    return out, subject_id


#: (name, fn, is_invariant)
PERTURBATIONS = [
    ("relabel", relabel, True),
    ("shuffle-edges", shuffle_edges, True),
    ("drop-far-move", drop_far_move, False),
    ("add-far-move", add_far_move, False),
]


def live_subjects(graph, taxonomy):
    """Subjects this lens actually reads: they have career-move edges AND fire on them."""
    out = []
    for ent in graph["entities"]:
        sid = ent["id"]
        moves = [e for e in _move_edges(graph) if e.get("source") == sid]
        if not moves:
            continue
        if index_of(graph, sid, taxonomy) > 0:
            out.append(sid)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--subjects", type=int, default=10)
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if an invariant perturbation moved the index")
    args = ap.parse_args(argv)

    if not os.path.exists(GRAPH):
        print("no graph at %s" % GRAPH)
        return 1
    graph = load_graph()
    taxonomy = load_lenses(os.path.join(ROOT, "detectors")).get("revolving_door")
    if taxonomy is None:
        print("revolving_door lens not found")
        return 1

    rng = random.Random(SEED)
    subjects = live_subjects(graph, taxonomy)
    print("REVOLVING_DOOR FLOOR -- %d entities, %d edge(s), %d live subject(s), seed %d"
          % (len(graph["entities"]), len(graph["edges"]), len(subjects), SEED))
    if len(subjects) < MIN_LIVE_SUBJECTS:
        print("")
        print("NO FLOOR MEASURABLE: %d subject(s) fire this lens, need %d."
              % (len(subjects), MIN_LIVE_SUBJECTS))
        print("A floor over subjects the lens never fires on measures the stability of zero.")
        return 0
    subjects = subjects[:args.subjects]

    floors = {}
    invariance_failures = []
    print("")
    print("%-16s %7s %8s %8s %8s %6s" % ("perturbation", "n", "median", "p90", "max", "MDE"))
    for name, fn, is_invariant in PERTURBATIONS:
        deltas = []
        for sid in subjects:
            base = index_of(graph, sid, taxonomy)
            for _ in range(args.trials):
                mutated, new_sid = fn(graph, sid, rng)
                if mutated is None:
                    continue
                got = index_of(mutated, new_sid, taxonomy)
                deltas.append(got - base)
                if is_invariant and abs(got - base) > 1e-9:
                    invariance_failures.append((name, sid, base, got))
        if not deltas:
            print("%-16s %7s %8s %8s %8s %6s   (not applicable)"
                  % (name, "-", "-", "-", "-", "-"))
            continue
        absv = [abs(d) for d in deltas]
        thr = pctile(absv, 1 - ALPHA)
        floors[name] = {"n": len(deltas), "median": round(pctile(absv, 0.5), 3),
                        "p90": round(pctile(absv, 0.90), 3), "max": round(max(absv), 3),
                        "threshold": round(thr, 3), "mde": mde(absv, thr),
                        "invariance": is_invariant}
        print("%-16s %7d %8.3f %8.3f %8.3f %6s%s"
              % (name, len(deltas), floors[name]["median"], floors[name]["p90"],
                 floors[name]["max"], floors[name]["mde"],
                 "   (must be 0)" if is_invariant else ""))

    print("")
    if invariance_failures:
        print("INVARIANCE FAILURE -- %d case(s). Relabelling nodes or reordering the edge list")
        print("changed a subject's read, which means the trajectory depends on node identity or")
        print("on file order rather than on the ties themselves. That is a bug, not a floor.")
        for name, sid, base, got in invariance_failures[:5]:
            print("   %-14s %s: %.3f -> %.3f" % (name, sid, base, got))
    else:
        print("INVARIANT: relabelling every node and reordering every edge moves nothing.")

    growth = [f for k, f in floors.items() if k in ("drop-far-move", "add-far-move")]
    degenerate = bool(growth) and all(f["median"] == 0 and f["p90"] == 0 for f in growth)
    per_lens = {
        "subjects": len(subjects),
        "trials": args.trials,
        "threshold_p95": max((f["threshold"] for f in growth), default=None),
        # Same rule as everywhere else: a degenerate null gets no number, because the search
        # would return its own first step and that reads as a resolution earned by nothing.
        "mde": (None if degenerate
                else max((f["mde"] for f in growth if f["mde"] is not None), default=None)),
        "mde_note": ("degenerate null: median and p90 both 0, so what this lens can resolve is "
                     "bounded by index quantisation, not by measured noise"
                     if degenerate else None),
        "null": "edge-perturb",
        "note": ("Unrelated dossier growth: another person's career-move edge landing or not. "
                 "Relabelling and edge REORDERING are invariants; edge FLIPPING is not tested "
                 "because this lens is directional and flipping changes the meaning."),
    }
    if growth:
        print("")
        print("FLOOR from unrelated dossier growth: median %.3f, p90 %.3f, max %.3f index points"
              % (max(f["median"] for f in growth), max(f["p90"] for f in growth),
                 max(f["max"] for f in growth)))
        if degenerate:
            print("MDE: none measured -- the null is degenerate, so resolution is bounded by")
            print("quantisation rather than by noise. Reporting the search step would be a")
            print("resolution earned by nothing.")

    # Merge into the shared file rather than overwriting network_brokerage's entry.
    blob = {}
    if os.path.exists(OUT):
        try:
            blob = json.load(io.open(OUT, encoding="utf-8"))
        except ValueError:
            blob = {}
    blob.setdefault("lenses", {})["revolving_door"] = per_lens
    blob["revolving_door_perturbations"] = floors
    blob["_note"] = ("Graph-lens floors. network_brokerage from eval/graph_floor.py "
                     "(undirected adjacency); revolving_door from eval/revolving_floor.py "
                     "(directional, typed move edges). The two nulls are NOT interchangeable: "
                     "edge-flip is an invariant for the first and a change of meaning for the "
                     "second.")
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(blob, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 1 if (args.check and invariance_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
