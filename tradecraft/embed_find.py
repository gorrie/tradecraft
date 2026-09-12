"""A find stage that has no vocabulary: semantic similarity to definitions and gold.

WHY THIS EXISTS

`detect_cues` is a hand-written keyword list and it fails in three measured ways that are
properties of the method rather than of the effort put in:

  * 621 cues, 58 of which fire on 371 news articles. On 20 Federal Register rulemaking
    documents -- the register these lenses were written FOR -- the whole taxonomy fires
    twice. The words are in the text (`compliance` 128x, `standards` 110x); the cues
    do not capture the concept.
  * The cut criterion used to prune it (background frequency) turned out anti-correlated
    with precision: restoring four "too common" cues raised lift 1.12 -> 1.77 and
    human-annotated retention from 1-of-4 to 12-of-19.
  * `sourcing_asymmetry/pejorative-actor-label` shipped eight cues, every one a
    right-directed epithet, under a file header reading "never a left/right". No amount
    of curation discipline fixes that, because a keyword list can only ever contain what
    its author thought to type. It is a property of the representation.

The taxonomy's real assets were never the cues. They are the 130 `definition` strings and
the 157 sourced `gold` exemplars -- Webb's actual words, Lippmann's actual phrase. This
makes those the detector.

HOW IT WORKS

Anchors: every detection contributes its definition and each of its gold spans as an
embedding. At detection time the document is cut into overlapping sentence windows, each
window is embedded, and a detection fires when a window's cosine similarity to one of its
anchors clears that detection's threshold. The receipt is the window plus the nearest
anchor plus the score -- "scores 0.71 against Webb 1923" rather than "contains the string
'permeation'".

THRESHOLDS ARE CALIBRATED, NOT AUTHORED

Per detection, the threshold is a high quantile of the similarity distribution over a
NEUTRAL CONTROL corpus (`corpus/_calibration-cache`, Federal Register rulemaking). Routine
institutional prose defines the noise floor, and only text that is more similar to the
method than routine prose ever is surfaces. Nobody types a magic number, and the control
corpus is not a labelled resource, so it cannot be Goodharted the way `cue_exclusivity`'s
generic-share was -- there is no label to optimise toward.

WHAT IT GIVES UP, SAID PLAINLY

The literal-string receipt. A reader can no longer ctrl-F the exact cue; they get a passage,
a sourced exemplar, and a number. That is a weaker epistemic claim than "this string is
present" -- and the string receipts it replaces were exact and exactly wrong 16 times per
136 fires. Also: exact determinism becomes bounded determinism (identical within a runtime,
cross-runtime drift must be gated numerically rather than by equality), and the browser
demo gains a one-time model download instead of a pure-JS engine.

    python -c "from tradecraft.embed_find import build_anchors; build_anchors()"
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[1]

#: multilingual on purpose. The cue matcher could never go multilingual -- a substring list
#: would need re-authoring per language, by someone fluent, with the same bias exposure
#: each time. A semantic anchor set transfers, which makes non-English a threshold
#: recalibration rather than a rewrite.
DEFAULT_MODEL = "intfloat/multilingual-e5-small"

#: e5 models are trained with these prefixes and degrade noticeably without them.
Q_PREFIX = "query: "
D_PREFIX = "passage: "

#: Window geometry, in sentences. Overlapping so a method spanning a sentence boundary is
#: not cut in half by the tokeniser's idea of where a thought ends.
WINDOW_SENTENCES = 3
WINDOW_STRIDE = 1

#: Quantile of the neutral-control similarity distribution that a window must beat. 0.995
#: means "more similar to this method than 99.5% of routine rulemaking prose is". Chosen
#: before any evaluation run and recorded here rather than tuned per lens, so that moving
#: it is a visible, reviewable act rather than a knob someone nudged until a number looked
#: better.
CONTROL_QUANTILE = 0.995

#: Floor beneath which a hit is refused no matter what the control quantile says. A lens
#: whose control distribution is unusually tight could otherwise produce a "significant"
#: threshold of 0.2, where nothing is really similar to anything.
ABSOLUTE_FLOOR = 0.60

ANCHORS = REPO / "data" / "anchors.json"
THRESHOLDS = REPO / "data" / "thresholds.json"


@dataclass
class Anchor:
    lens: str
    detection: str
    kind: str          # "definition" | "gold"
    text: str
    source: Optional[str] = None


def collect_anchors(detectors_dir: Optional[str] = None) -> list[Anchor]:
    """Every definition and gold span in the taxonomy, as embedding anchors."""
    from tradecraft.loader import load_lenses
    lenses = load_lenses(detectors_dir or str(REPO / "detectors"))
    out: list[Anchor] = []
    for lid, tax in sorted(lenses.items()):
        for m in tax.markers:
            for d in m.detections:
                if d.definition:
                    out.append(Anchor(lid, d.id, "definition", d.definition.strip()))
                for g in (d.gold or []):
                    t = (g.get("text") or "").strip()
                    if t:
                        out.append(Anchor(lid, d.id, "gold", t, g.get("source")))
    return out


_SENT = re.compile(r"(?<=[.!?])\s+")


def windows(text: str, n: int = None, stride: int = None):
    """Overlapping sentence windows, with their character offsets in the original text.

    Offsets are tracked against the ORIGINAL string rather than recomputed from the joined
    window -- the same discipline `detect_cues` had to learn the hard way when lowercasing
    shifted every span after a Turkish dotted I.
    """
    # Read the module globals HERE, not in the signature. A default argument binds once at
    # definition time, so `embed_find.WINDOW_SENTENCES = 1` from outside silently did
    # nothing -- a recalibration run "at 1 sentence" produced byte-identical 3-sentence
    # thresholds, and only comparing the numbers caught it.
    n = WINDOW_SENTENCES if n is None else n
    stride = WINDOW_STRIDE if stride is None else stride
    sents, pos = [], 0
    for part in _SENT.split(text):
        if not part:
            continue
        idx = text.find(part, pos)
        if idx < 0:
            idx = pos
        sents.append((idx, idx + len(part), part))
        pos = idx + len(part)
    for i in range(0, max(1, len(sents) - n + 1), stride):
        chunk = sents[i:i + n]
        if not chunk:
            continue
        yield chunk[0][0], chunk[-1][1], " ".join(c[2] for c in chunk)


def load_model(name: str = DEFAULT_MODEL):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)


def build_anchors(model_name: str = DEFAULT_MODEL, detectors_dir: Optional[str] = None,
                  kinds=("definition", "gold")) -> dict:
    """Embed the anchor set once and commit it. Cheap (a few hundred short strings)."""
    import numpy as np
    # `kinds` exists to test a specific hypothesis: a DEFINITION describes a method,
    # and a passage performing that method need not resemble a description of it, so
    # definition anchors may be diluting rather than helping. Gold exemplars ARE instances.
    anchors = [a for a in collect_anchors(detectors_dir) if a.kind in kinds]
    model = load_model(model_name)
    vecs = model.encode([D_PREFIX + a.text for a in anchors],
                        normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    ANCHORS.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "model": model_name,
        "note": ("Embedded definitions and gold exemplars, the anchor set for the "
                 "embedding find stage. Regenerate with build_anchors() after any "
                 "taxonomy edit; the vectors are derived and must never be hand-edited."),
        "dim": int(vecs.shape[1]),
        "kinds": list(kinds),
        "anchors": [{"lens": a.lens, "detection": a.detection, "kind": a.kind,
                     "text": a.text, "source": a.source,
                     "vec": [round(float(x), 6) for x in v]}
                    for a, v in zip(anchors, np.asarray(vecs))],
    }
    ANCHORS.write_text(json.dumps(blob), encoding="utf-8", newline="\n")
    return {"anchors": len(anchors), "dim": blob["dim"], "model": model_name}


_ANCHOR_CACHE = None


def load_anchors():
    """Anchor matrix + row metadata. Raises if stale against the current taxonomy, because
    silently scoring against yesterday's definitions is the drift this project exists to
    prevent."""
    import numpy as np
    global _ANCHOR_CACHE
    if _ANCHOR_CACHE is not None:
        return _ANCHOR_CACHE
    if not ANCHORS.is_file():
        raise RuntimeError("no anchors.json -- run build_anchors()")
    blob = json.loads(ANCHORS.read_text(encoding="utf-8"))
    rows = blob["anchors"]
    kinds = {r["kind"] for r in rows} or {"definition", "gold"}
    live = {(a.lens, a.detection, a.kind, a.text)
            for a in collect_anchors() if a.kind in kinds}
    have = {(r["lens"], r["detection"], r["kind"], r["text"]) for r in rows}
    if live != have:
        raise RuntimeError(
            f"anchors.json is stale: taxonomy has {len(live)} anchors, file has {len(have)}, "
            f"{len(live ^ have)} differ -- re-run build_anchors()")
    mat = np.asarray([r["vec"] for r in rows], dtype="float32")
    # Cached: the staleness check re-parses the whole taxonomy, which is correct once and
    # ruinous per-document across a 371-article evaluation.
    _ANCHOR_CACHE = (blob, rows, mat)
    return _ANCHOR_CACHE


def _score_windows(text, model, mat, rows, n_sent=None):
    """(window, per-detection best similarity) for every window in the document."""
    import numpy as np
    wins = list(windows(text, n_sent))
    if not wins:
        return [], {}
    vecs = model.encode([Q_PREFIX + w[2] for w in wins], normalize_embeddings=True,
                        batch_size=64, show_progress_bar=False)
    sims = np.asarray(vecs, dtype="float32") @ mat.T          # windows x anchors
    best = {}
    for j, r in enumerate(rows):
        key = (r["lens"], r["detection"])
        col = sims[:, j]
        prev = best.get(key)
        best[key] = col if prev is None else np.maximum(prev, col)
    return wins, best


def calibrate(control_dir: Optional[Path] = None, model=None,
              quantile=CONTROL_QUANTILE, n_sent=None):
    """Per-detection threshold from a NEUTRAL control corpus.

    The threshold answers "how similar to this method does routine institutional prose get,
    by accident?" and puts the bar just above it. Nobody types a number, and the control
    corpus carries no labels, so there is nothing here to optimise toward -- which is the
    structural difference from the generic-share metric that the cue cut Goodharted.
    """
    import numpy as np
    control_dir = Path(control_dir or (REPO / "corpus" / "_calibration-cache"))
    docs = sorted(control_dir.glob("*.txt"))
    if not docs:
        raise RuntimeError(f"no control documents in {control_dir} -- run "
                           f"corpus/calibrate_register.py --fetch 20")
    model = model or load_model()
    _, rows, mat = load_anchors()
    pools: dict[tuple, list] = {}
    for p in docs:
        _, best = _score_windows(p.read_text(encoding="utf-8", errors="replace"),
                                 model, mat, rows, n_sent)
        for k, col in best.items():
            pools.setdefault(k, []).append(col)
    out = {}
    for k, cols in pools.items():
        allv = np.concatenate(cols)
        thr = float(np.quantile(allv, quantile))
        out[f"{k[0]}::{k[1]}"] = {
            "threshold": round(max(thr, ABSOLUTE_FLOOR), 4),
            "control_quantile": quantile,
            "control_max": round(float(allv.max()), 4),
            "control_median": round(float(np.median(allv)), 4),
            "floored": thr < ABSOLUTE_FLOOR,
        }
    THRESHOLDS.parent.mkdir(parents=True, exist_ok=True)
    THRESHOLDS.write_text(json.dumps({
        "note": ("Per-detection similarity thresholds, derived from the neutral control "
                 "corpus at corpus/_calibration-cache (Federal Register rulemaking). A "
                 "detection fires when a window beats its threshold. Derived: never "
                 "hand-edit, re-run calibrate()."),
        "control_documents": len(docs),
        "quantile": quantile,
        "window_sentences": n_sent if n_sent is not None else WINDOW_SENTENCES,
        "absolute_floor": ABSOLUTE_FLOOR,
        "thresholds": dict(sorted(out.items())),
    }, indent=1), encoding="utf-8", newline="\n")
    return out


def detect_embed(text, taxonomy, model=None, thresholds=None, top_k=12,
                 n_sent=None):
    """Embedding find stage. Returns DetectionHit objects, so it drops into the existing
    grader and verifier unchanged -- the point is to replace the find stage, not the
    pipeline around it."""
    from tradecraft.schema import DetectionHit
    model = model or load_model()
    _, rows, mat = load_anchors()
    if thresholds is None:
        thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))["thresholds"]
    wins, best = _score_windows(text, model, mat, rows, n_sent)
    if not wins:
        return []
    nearest = {}
    for j, r in enumerate(rows):
        nearest.setdefault((r["lens"], r["detection"]), []).append(r)
    hits = []
    for (lens, det), col in best.items():
        if lens != taxonomy.id:
            continue
        cfg = thresholds.get(f"{lens}::{det}")
        if not cfg:
            continue
        i = int(col.argmax())
        score = float(col[i])
        if score < cfg["threshold"]:
            continue
        lo, hi, wtext = wins[i]
        anchors_here = nearest[(lens, det)]
        hits.append(DetectionHit(
            detection_id=det,
            confidence=round(min(1.0, score), 4),
            span=wtext,
            char_start=lo,
            char_end=hi,
            rationale=(f"semantic match {score:.3f} >= threshold {cfg['threshold']:.3f} "
                       f"(control q{cfg['control_quantile']}); nearest anchor: "
                       f"{anchors_here[0]['kind']} {anchors_here[0]['text'][:90]!r}"),
        ))
    hits.sort(key=lambda h: -h.confidence)
    return hits[:top_k]
