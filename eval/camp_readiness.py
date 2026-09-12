#!/usr/bin/env python3
"""Per-camp readiness: which factions are ready to validate, and which need work first.

WHY THIS EXISTS
---------------
The goal is a detection for every camp that signals with language. `subculture_register` already
carries 27 of them, and `BACKLOG-shibboleth-corpus-study.md` specifies exactly how each is
validated: assemble the camp's canon, mine its coined idiom, then prove recall on the camp's OWN
works and precision against the OTHER camps' works and a benign control.

Nothing said which camps are ready for that and which are not. `eval/cue_exclusivity.py`
measures generic-share per LENS, so all 27 camps collapse into one number and a camp with three
cues and no gold looks exactly like a camp with nineteen and four. This reports per CAMP.

WHAT IT MEASURES, AND WHY EACH ONE IS A READINESS QUESTION

  cues            A camp with 3 cues cannot be validated: the method requires recall on >=2 of
                  its own primary works, and a 3-cue set has no room to lose one to an FP audit.
  gold            The repo's own rule is that every detection carries a sourced gold example.
                  A camp with no gold has nothing to regression-test against.
  collisions      A cue appearing in TWO camps is not a shibboleth for either. This is the
                  cheapest real defect to find and it needs no corpus at all.
  generic         A cue occurring in the benign news control is, by the study's definition, not
                  a shibboleth -- it identifies "activist-speak generally" rather than THIS
                  discourse. Flagged for review.
  fixtures        Whether any should_fire fixture exercises the camp, i.e. whether the eval
                  suite would notice if the camp broke.

WHAT THIS IS NOT, AND THIS MATTERS
----------------------------------
**Not a cut list.** The generic-share metric has been Goodharted in this repository once
already: the 2026-08-26 background-frequency cut removed four "too common" cues and restoring
them raised lift 1.12 -> 1.77 and human-annotated retention from 1-of-4 to 12-of-19. Frequency
in ordinary prose is a REVIEW PROMPT, never a verdict, and nothing here should be wired to
delete anything. The output is a work list for a human assembling canon.

It is also not a capability claim. A camp marked ready-to-validate has a cue set worth testing,
not a demonstrated detection -- and the 2026-09-03 enumeration ceiling
(`RESULTS-2026-09-03-cue-enumeration-ceiling.md`) says the test must be against the camp's own
prose, because these phrases are near-absent from news by construction.

    python eval/camp_readiness.py                 # every camp, ranked by what it needs
    python eval/camp_readiness.py --lens subculture_register
    python eval/camp_readiness.py --markdown      # table for a backlog or results doc
    python eval/camp_readiness.py --collisions    # just the cross-camp cue collisions
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.loader import load_lenses  # noqa: E402

OUT = os.path.join(HERE, "camp-readiness.json")
CONTROL = os.path.join(ROOT, "corpus", "_news-control")
FIXTURES = os.path.join(HERE, "fixtures.json")

#: Below this a camp cannot survive an FP audit with anything left over. The study's recall bar
#: is two of the camp's own works, and a cue set this small has no redundancy.
THIN_CUES = 5

#: A camp with fewer gold examples than this cannot be regression-tested meaningfully.
MIN_GOLD = 1


def control_docs():
    out = []
    for path in sorted(glob.glob(os.path.join(CONTROL, "*.txt"))):
        out.append(io.open(path, encoding="utf-8", errors="replace").read().lower())
    return out


def load_fixture_markers():
    """Marker ids exercised by any should_fire fixture, so a camp's coverage is checkable.

    The field is `expect_any`. The first draft of this guessed `markers` / `expect_markers`,
    found nothing, and reported all 27 camps as lacking a fixture -- which would have sent
    someone to write 27 fixtures that already exist. A column that reads the same for every
    row is a broken measurement, not a finding, and that is now the third time this shape has
    come up today. The assertion in tests/test_camp_readiness.py holds it.
    """
    if not os.path.exists(FIXTURES):
        return set()
    raw = json.load(io.open(FIXTURES, encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("fixtures", raw)
    seen = set()
    for f in items:
        if not isinstance(f, dict) or not f.get("should_fire"):
            continue
        for m in f.get("expect_any") or []:
            seen.add(m)
    return seen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lens", action="append", help="restrict to these lens ids")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--collisions", action="store_true",
                    help="report only cues shared between camps")
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    if args.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(args.lens)}
    if not lenses:
        print("no lenses matched")
        return 1

    # Camp = marker. Collect its cues and gold across all its detections.
    camps = {}
    owners = {}          # cue -> [camp keys], for collision detection
    for lens_id, tax in sorted(lenses.items()):
        for marker in tax.markers:
            key = "%s/%s" % (lens_id, marker.id)
            cues, gold = [], 0
            for det in marker.detections:
                cues.extend(det.cues or [])
                gold += len(det.gold or [])
            camps[key] = {"lens": lens_id, "marker": marker.id,
                          "cues": sorted(set(c.lower() for c in cues)),
                          "n_detections": len(marker.detections),
                          "gold": gold}
            for cue in set(c.lower() for c in cues):
                owners.setdefault(cue, []).append(key)

    collisions = {c: sorted(k) for c, k in owners.items() if len(set(k)) > 1}

    if args.collisions:
        print("CROSS-CAMP CUE COLLISIONS -- a cue in two camps is a shibboleth for neither")
        if not collisions:
            print("  none. Every cue belongs to exactly one camp.")
            return 0
        for cue, keys in sorted(collisions.items()):
            print("  %-38s %s" % (repr(cue), ", ".join(keys)))
        print("\n%d collision(s). Each needs one camp to keep the cue and the other to lose it,"
              % len(collisions))
        print("or the cue is generic and belongs to neither.")
        return 0

    control = control_docs()
    fixture_markers = load_fixture_markers()

    for key, rec in camps.items():
        generic = {}
        for cue in rec["cues"]:
            n = sum(1 for t in control if cue in t)
            if n:
                generic[cue] = n
        rec["generic_in_control"] = dict(sorted(generic.items(), key=lambda kv: -kv[1]))
        rec["collides"] = sorted(c for c in rec["cues"] if c in collisions)
        rec["has_fixture"] = rec["marker"] in fixture_markers

        needs = []
        if len(rec["cues"]) < THIN_CUES:
            needs.append("cues")
        if rec["gold"] < MIN_GOLD:
            needs.append("gold")
        if rec["collides"]:
            needs.append("collisions")
        if generic:
            needs.append("review-generic")
        if not rec["has_fixture"]:
            needs.append("fixture")
        rec["needs"] = needs
        rec["verdict"] = "ready-to-validate" if not needs else "needs: " + ", ".join(needs)

    payload = {
        "_note": ("Per-camp readiness for the shibboleth study. A REVIEW LIST, never a cut "
                  "list: frequency in ordinary prose has been Goodharted here before. "
                  "Regenerate with python eval/camp_readiness.py"),
        "control_documents": len(control),
        "thin_cues_below": THIN_CUES,
        "collisions": collisions,
        "camps": camps,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    order = sorted(camps.items(), key=lambda kv: (len(kv[1]["needs"]) == 0,
                                                  len(kv[1]["cues"])))
    if args.markdown:
        print("| camp | cues | gold | collides | generic | fixture | needs |")
        print("|---|---:|---:|---:|---:|:-:|---|")
        for key, r in order:
            print("| `%s` | %d | %d | %d | %d | %s | %s |"
                  % (key, len(r["cues"]), r["gold"], len(r["collides"]),
                     len(r["generic_in_control"]), "yes" if r["has_fixture"] else "**no**",
                     ", ".join(r["needs"]) or "—"))
        return 0

    ready = [k for k, r in camps.items() if not r["needs"]]
    print("PER-CAMP READINESS -- %d camp(s) across %d lens(es), %d control document(s)"
          % (len(camps), len(lenses), len(control)))
    print("A REVIEW LIST, not a cut list. Generic-share has been Goodharted here before.")
    print("")
    print("%-46s %5s %5s %5s %5s %4s" % ("camp", "cues", "gold", "coll", "gen", "fix"))
    for key, r in order:
        print("%-46s %5d %5d %5d %5d %4s   %s"
              % (key[:46], len(r["cues"]), r["gold"], len(r["collides"]),
                 len(r["generic_in_control"]), "y" if r["has_fixture"] else "NO",
                 ", ".join(r["needs"])))
    print("")
    print("%d of %d camps are ready to validate as they stand." % (len(ready), len(camps)))
    if collisions:
        print("%d cue(s) belong to more than one camp -- see --collisions." % len(collisions))
    print("Thin camps are the cheap wins: they need canon assembled and idiom mined, which is")
    print("desk work with no measurement blocked behind it.")
    print("")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
