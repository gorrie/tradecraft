#!/usr/bin/env python3
"""What does a graph lens's index do when the graph changes in ways that say nothing new?

WHY THIS EXISTS
---------------
`eval/lens_floor.py` measures the resolution of a TEXT lens by perturbing prose — reorder the
sentences, re-chunk, renormalise whitespace, duplicate. None of those means anything to
`network_brokerage` or `revolving_door`, which read a graph. So the two graph lenses have been
scored with no statement of what an index difference between two subjects is worth, which is
the exact defect this repository spent three days documenting in the political-bias literature.
Corpus item 30 asks for it for `ratchet_series`; this is the same object for the graph.

THE NULL, AND WHY IT IS THE RIGHT ONE
-------------------------------------
An entity graph built from dossiers is permanently incomplete. Nodes and edges arrive as
research lands, in an order that has nothing to do with any particular subject. So:

  **A subject's structural position must not swing on whether some unrelated peripheral node
  happens to have been entered yet.**

That is a null a graph detector can be held to, and it is the nuisance factor that actually
governs a longitudinal leaderboard — the board is re-cut as the corpus grows, and a movement
between cuts has to be distinguishable from the corpus having grown.

Four perturbations, none of which changes anything the subject's own ties assert:

  relabel        every node id replaced by an opaque token. Pure invariance: any movement at
                 all is a bug, not a floor.
  flip-edges     every edge's source and target swapped. Adjacency is undirected, so this must
                 be exactly zero too.
  drop-far-leaf  a degree-1 node NOT adjacent to the subject is removed -- a dossier that had
                 not landed yet.
  add-far-leaf   a new degree-1 node is attached to a random non-adjacent node -- the next
                 dossier landing somewhere else.

The first two are correctness assertions. The last two are the floor.

    python eval/graph_floor.py
    python eval/graph_floor.py --subjects 12 --trials 30
    python eval/graph_floor.py --check          # exit 1 if an invariance perturbation moves
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

from tradecraft import brokerage as B                      # noqa: E402
from tradecraft.grader import grade_document_for_lens       # noqa: E402
from tradecraft.loader import load_lenses                   # noqa: E402

GRAPH = os.path.join(ROOT, "data", "research-entities.json")
OUT = os.path.join(HERE, "graph-floors.json")
SEED = 20260902
POWER = 0.80
ALPHA = 0.05

# Movement allowed on a perturbation that cannot change any structural fact. Not a tolerance
# to be widened: relabelling node ids is a rename, and a rename that moves a score is a bug.
INVARIANT_TOLERANCE = 1e-9


def index_of(graph, subject_id, taxonomy):
    hits = detect_on_graph(graph, subject_id)
    return grade_document_for_lens(taxonomy, hits, token_count=0).index


def measure(graph, subject_id, taxonomy):
    """(index, betweenness) -- BOTH, because the index alone cannot answer the question.

    The first run of this harness returned 0.000 for every perturbation and every subject,
    which reads as a perfectly precise instrument and is not one. The graph metrics move
    exactly as they should -- dropping an unrelated leaf takes Frontier Model Forum's
    betweenness from 0.1078 to 0.1090, adding one takes it to 0.1097 -- while the INDEX does
    not move at all.

    The reason is quantisation. This lens has three markers and its detections fire at a fixed
    confidence, so the index can take only a handful of values: once all three fire, it is
    saturated and no amount of movement in the underlying centrality changes it. A floor of
    0.000 therefore means the index is COARSE, not that the measurement is sharp -- and
    reporting it as a clean floor would be the most flattering possible reading of no
    resolution.

    So both are tracked. The index floor says what a leaderboard gap is worth; the metric floor
    says what the arithmetic underneath actually does.
    """
    hits = detect_on_graph(graph, subject_id)
    index = grade_document_for_lens(taxonomy, hits, token_count=0).index
    bc = None
    for hit in hits:
        if hit.detection_id == "high-betweenness":
            try:
                bc = float(hit.span.split("betweenness")[1].split(",")[0])
            except (IndexError, ValueError):
                bc = None
    return index, bc


def detect_on_graph(graph, subject_id):
    """brokerage.detect_subject, against an in-memory graph rather than a path."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(graph, fh)
        return B.detect_subject(path, subject_id)
    finally:
        os.unlink(path)


def relabel(graph, subject_id, rng):
    """Opaque ids for every node. The subject's new id is returned with the graph."""
    ids = [e["id"] for e in graph["entities"]]
    mapping = {old: "n%06d" % i for i, old in enumerate(sorted(ids))}
    out = copy.deepcopy(graph)
    for ent in out["entities"]:
        ent["id"] = mapping[ent["id"]]
    kept = []
    for edge in out["edges"]:
        if edge.get("source") in mapping and edge.get("target") in mapping:
            edge["source"] = mapping[edge["source"]]
            edge["target"] = mapping[edge["target"]]
            kept.append(edge)
    out["edges"] = kept
    return out, mapping[subject_id]


def flip_edges(graph, subject_id, rng):
    out = copy.deepcopy(graph)
    for edge in out["edges"]:
        edge["source"], edge["target"] = edge.get("target"), edge.get("source")
    return out, subject_id


def _degrees(graph):
    deg = {e["id"]: 0 for e in graph["entities"]}
    for edge in graph["edges"]:
        s, t = edge.get("source"), edge.get("target")
        if s in deg and t in deg and s != t:
            deg[s] += 1
            deg[t] += 1
    return deg


def _neighbours(graph, subject_id):
    out = set()
    for edge in graph["edges"]:
        s, t = edge.get("source"), edge.get("target")
        if s == subject_id:
            out.add(t)
        elif t == subject_id:
            out.add(s)
    return out


def drop_far_leaf(graph, subject_id, rng):
    deg = _degrees(graph)
    near = _neighbours(graph, subject_id) | {subject_id}
    leaves = sorted(n for n, d in deg.items() if d == 1 and n not in near)
    if not leaves:
        return None, subject_id
    victim = rng.choice(leaves)
    out = copy.deepcopy(graph)
    out["entities"] = [e for e in out["entities"] if e["id"] != victim]
    out["edges"] = [e for e in out["edges"]
                    if e.get("source") != victim and e.get("target") != victim]
    return out, subject_id


def add_far_leaf(graph, subject_id, rng):
    near = _neighbours(graph, subject_id) | {subject_id}
    hosts = sorted(e["id"] for e in graph["entities"] if e["id"] not in near)
    if not hosts:
        return None, subject_id
    host = rng.choice(hosts)
    out = copy.deepcopy(graph)
    new_id = "synthetic-leaf-%d" % rng.randrange(10 ** 9)
    sectors = sorted({e.get("sector") for e in graph["entities"] if e.get("sector")})
    out["entities"].append({"id": new_id, "name": new_id, "type": "org",
                            "sector": rng.choice(sectors) if sectors else "unknown"})
    out["edges"].append({"source": new_id, "target": host, "rel": "employed-by"})
    return out, subject_id


PERTURBATIONS = [
    ("relabel", relabel, True),
    ("flip-edges", flip_edges, True),
    ("drop-far-leaf", drop_far_leaf, False),
    ("add-far-leaf", add_far_leaf, False),
]


def pctile(vals, q):
    v = sorted(vals)
    if not v:
        return float("nan")
    return v[min(int(q * len(v)), len(v) - 1)]


def mde(vals, threshold, power=POWER):
    if not vals:
        return float("nan")
    step = 0.5
    d = 0.0
    while d <= 100.0:
        shifted = [abs(x) + d for x in vals]
        if sum(1 for s in shifted if s > threshold) / len(shifted) >= power:
            return d
        d += step
    return float("nan")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--subjects", type=int, default=10,
                    help="how many top-position subjects to measure")
    ap.add_argument("--trials", type=int, default=12,
                    help="random trials per stochastic perturbation")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if an invariance perturbation moves the index at all")
    args = ap.parse_args(argv)

    taxonomy = load_lenses(os.path.join(ROOT, "detectors"))["network_brokerage"]
    graph = json.load(io.open(GRAPH, encoding="utf-8"))
    report = B.graph_report(GRAPH, top=args.subjects)
    subjects = [r["id"] for r in report["top"]]

    print("GRAPH FLOOR -- network_brokerage, %d nodes, %d subject(s), seed %d"
          % (report["nodes"], len(subjects), SEED))
    print("invariance perturbations must move NOTHING; the leaf perturbations are the floor")
    print()

    rng = random.Random(SEED)
    per_kind = {name: [] for name, _, _ in PERTURBATIONS}
    per_kind_bc = {name: [] for name, _, _ in PERTURBATIONS}
    invariance_failures = []
    seen_indices = set()

    for subject_id in subjects:
        base, base_bc = measure(graph, subject_id, taxonomy)
        seen_indices.add(base)
        for name, fn, is_invariant in PERTURBATIONS:
            trials = 1 if is_invariant else args.trials
            for _ in range(trials):
                mutated, new_subject = fn(graph, subject_id, rng)
                if mutated is None:
                    continue
                got, got_bc = measure(mutated, new_subject, taxonomy)
                seen_indices.add(got)
                delta = got - base
                per_kind[name].append(delta)
                if base_bc is not None and got_bc is not None:
                    per_kind_bc[name].append(got_bc - base_bc)
                if is_invariant and abs(delta) > INVARIANT_TOLERANCE:
                    invariance_failures.append((subject_id, name, base, got))

    print("%-16s %7s %8s %8s %8s %6s" % ("perturbation", "n", "median", "p90", "max", "MDE"))
    floors = {}
    for name, _, is_invariant in PERTURBATIONS:
        vals = per_kind[name]
        if not vals:
            print("%-16s %7s %8s %8s %8s %6s   (not applicable)" % (name, "-", "-", "-", "-", "-"))
            continue
        absv = [abs(v) for v in vals]
        thr = pctile(absv, 1 - ALPHA)
        floors[name] = {"n": len(vals), "median": round(pctile(absv, 0.5), 3),
                        "p90": round(pctile(absv, 0.90), 3), "max": round(max(absv), 3),
                        "threshold": round(thr, 3), "mde": mde(absv, thr),
                        "invariance": is_invariant}
        print("%-16s %7d %8.3f %8.3f %8.3f %6s%s"
              % (name, len(vals), floors[name]["median"], floors[name]["p90"],
                 floors[name]["max"], floors[name]["mde"],
                 "   (must be 0)" if is_invariant else ""))

    leaf = [abs(v) for name in ("drop-far-leaf", "add-far-leaf") for v in per_kind[name]]
    verdict = 0
    print()
    if invariance_failures:
        print("INVARIANCE BROKEN on %d trial(s) -- renaming nodes or flipping edge direction"
              % len(invariance_failures))
        print("changed a score. That is a bug in the detector, not a floor:")
        for subj, name, base, got in invariance_failures[:6]:
            print("   %-34s %-12s %.3f -> %.3f" % (subj[:34], name, base, got))
        verdict = 1
    else:
        print("INVARIANT: relabelling every node and flipping every edge moves nothing.")

    leaf_bc = [abs(v) for name in ("drop-far-leaf", "add-far-leaf")
               for v in per_kind_bc[name]]
    if leaf:
        thr = pctile(leaf, 1 - ALPHA)
        print()
        print("FLOOR from unrelated corpus growth: median %.3f, p90 %.3f, max %.3f index points"
              % (pctile(leaf, 0.5), pctile(leaf, 0.90), max(leaf)))

        # A zero index floor next to a moving metric is quantisation, not precision.
        if max(leaf) <= INVARIANT_TOLERANCE and leaf_bc and max(leaf_bc) > 0:
            print()
            print("THIS IS NOT A CLEAN FLOOR. The index did not move on any trial -- and the")
            print("graph metric underneath it moved on %d of %d, by up to %.4f betweenness"
                  % (sum(1 for v in leaf_bc if v > 0), len(leaf_bc), max(leaf_bc)))
            # No relative-change figure here. An earlier version divided the max by the
            # median and printed "1050%", which is a ratio between two summary statistics
            # and not a percentage of anything. The absolute movement above is the fact.
            print("The index is QUANTISED: this lens has three markers firing at a fixed")
            print("confidence, so it takes only %d distinct value(s) across every subject and"
                  % len(seen_indices))
            print("perturbation measured here:")
            print("   %s" % ", ".join("%.2f" % v for v in sorted(seen_indices)))
            print()
            print("So the honest reading is that a leaderboard gap on this lens is not")
            print("resolvable BELOW the quantisation step, and unrelated corpus growth is not")
            print("what limits it. Reporting 0.000 as the floor would be the most flattering")
            print("possible reading of no resolution.")
            verdict = max(verdict, 1)
        else:
            print("MDE %s -- an index gap below this between two subjects is the width of the"
                  % mde(leaf, thr))
            print("ruler, and it is the width that unrelated research landing adds.")

    if leaf_bc:
        thr_bc = pctile(leaf_bc, 1 - ALPHA)
        print()
        print("The same perturbations on the METRIC (betweenness): median %.5f, p90 %.5f, "
              "max %.5f" % (pctile(leaf_bc, 0.5), pctile(leaf_bc, 0.90), max(leaf_bc)))
        print("That is what a continuous position score would have to beat, and it is the")
        print("number to quote if this lens ever reports centrality rather than a tier.")

    # PER-LENS BLOCK, added 2026-09-03 (CP5). The file recorded the perturbation floors but
    # keyed nothing by lens, so `eval/floors_contract.py` -- the one place that answers "what
    # is this lens's resolution?" for every consumer -- read it and found nothing. The floor
    # was measured and invisible, which is worse than unmeasured: the contract's --check
    # reported network_brokerage as receipts-only, on a lens that had a graph floor all along.
    #
    # revolving_door is deliberately ABSENT rather than given a copy of this number. This
    # harness perturbs an UNDIRECTED adjacency graph and scores brokerage position;
    # revolving_door keys on typed move/funding edges and reads trajectory, so the same
    # perturbations do not describe its null. Handing it a floor measured for a different
    # lens would be exactly the mistake the CP6 renderer nearly shipped -- a resolution
    # presented as qualifying a number it does not describe.
    growth = [f for k, f in floors.items() if k in ("drop-far-leaf", "add-far-leaf")]
    per_lens = {
        "network_brokerage": {
            "subjects": len(subjects),
            "trials": args.trials,
            # The growth perturbations are the floor; relabel and flip are invariants that
            # must be zero and are asserted elsewhere, so they do not set a threshold.
            "threshold_p95": max((f["threshold"] for f in growth), default=None),
            # DEGENERATE NULL -> no MDE, the same rule lens_floor.mde() already enforces. With
            # median and p90 both 0.000 the search returns its own first STEP (0.5), and
            # printing that as a resolution reads as "resolves half an index point" on the
            # strength of nothing -- the exact defect that file's docstring records fixing.
            # One outlier at max does not make a null measurable; it makes it skewed.
            "mde": (None
                    if all(f["median"] == 0 and f["p90"] == 0 for f in growth)
                    else max((f["mde"] for f in growth if f["mde"] is not None), default=None)),
            "mde_note": ("degenerate null: median and p90 both 0, so what this lens can "
                         "resolve is bounded by index quantisation, not by measured noise"
                         if all(f["median"] == 0 and f["p90"] == 0 for f in growth) else None),
            "null": "edge-perturb",
            "note": ("Unrelated corpus growth: a peripheral dossier landing or not landing. "
                     "Relabelling and edge-flipping are invariants and move nothing."),
        },
    }

    # MERGE, do not replace. Two harnesses write this file now -- this one for
    # network_brokerage and eval/revolving_floor.py for revolving_door -- because their nulls
    # are not interchangeable (edge-flip is an invariant here and a change of meaning there).
    # Replacing the file meant whichever ran last silently deleted the other lens's floor, and
    # the floors contract then reported that lens as having no graph floor at all. Caught
    # 2026-09-04 by running this immediately after the new harness.
    blob = {}
    if os.path.exists(OUT):
        try:
            blob = json.load(io.open(OUT, encoding="utf-8"))
        except ValueError:
            blob = {}
    blob.update({"seed": SEED, "nodes": report["nodes"], "subjects": subjects,
                 "trials": args.trials, "perturbations": floors,
                 "invariance_failures": len(invariance_failures)})
    blob.setdefault("lenses", {}).update(per_lens)
    blob["_note"] = ("Graph-lens floors, written by TWO harnesses: network_brokerage from "
                     "eval/graph_floor.py (undirected adjacency) and revolving_door from "
                     "eval/revolving_floor.py (directional, typed move edges). Each updates "
                     "only its own key. The nulls are not interchangeable.")
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(blob, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print()
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return verdict if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
