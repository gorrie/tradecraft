#!/usr/bin/env python
"""Refresh the offline Tradecraft web demo's embedded cue data from the taxonomies.

The demo (web/demo.html) is a single self-contained page that runs the DETERMINISTIC cue floor of
the Tradecraft engine entirely in the browser — no server, no key, nothing sent anywhere. It is the
web front door for `detect the method, not the ideology`: paste text, see each lens's method markers
fire with the exact matched spans, never a verdict.

demo.html carries a snapshot of the lens cues inline (so it works as a standalone file / hosted
artifact). This script re-extracts the cues from detectors/*/taxonomy.yaml and rewrites that snapshot
in place. Run it whenever the taxonomies change:

    python web/build-demo.py            # refresh web/demo.html in place

Scope + honesty: this is the cue FLOOR only (literal substring markers). The full engine adds context
verification (drop false positives), cloud/local/abliterated backends, and the network lenses
(revolving_door has no text cues and is intentionally omitted here). The demo says so on the page.
"""
import json, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tradecraft/
DEMO = os.path.join(ROOT, "web", "demo.html")

def extract():
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required: pip install pyyaml")
    lenses = []
    for f in sorted(glob.glob(os.path.join(ROOT, "detectors", "*", "taxonomy.yaml"))):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if not isinstance(d, dict):
            continue
        cfg = d.get("config", {}) or {}
        markers = []
        for m in d.get("markers", []) or []:
            dets = []
            for det in m.get("detections", []) or []:
                cues = [c for c in (det.get("cues") or []) if isinstance(c, str)]
                gold = ""
                g = det.get("gold") or []
                if g and isinstance(g, list) and isinstance(g[0], dict):
                    gold = g[0].get("text", "")
                if cues:
                    dets.append({"id": det.get("id"), "def": (det.get("definition") or "")[:160],
                                 "w": det.get("weight", 0.5), "cues": cues, "gold": gold[:140]})
            if dets:
                markers.append({"id": m.get("id"), "name": m.get("name"),
                                "bw": m.get("base_weight", 0.8), "dets": dets})
        if markers:  # skip lenses with no text cues (e.g. revolving_door)
            lenses.append({"id": d.get("id"), "name": d.get("name"),
                           "desc": (d.get("description") or "")[:220],
                           "cfg": {k: cfg.get(k) for k in
                                   ("w_breadth", "w_intensity", "w_density",
                                    "density_cap_per_1k", "marker_present_threshold")},
                           "tiers": cfg.get("tiers", []), "markers": markers})
    return lenses

def main():
    lenses = extract()
    data = json.dumps(lenses, ensure_ascii=False)
    data = data.replace("</", "<\\/")  # never break out of the <script> tag
    html = open(DEMO, encoding="utf-8").read()
    new, n = re.subn(r"const LENSES = .*?;\nconst SAMPLES",
                     "const LENSES = " + data + ";\nconst SAMPLES", html, count=1, flags=re.S)
    if n != 1:
        sys.exit("could not locate the LENSES snapshot anchor in web/demo.html")
    open(DEMO, "w", encoding="utf-8").write(new)
    cues = sum(len(c["cues"]) for L in lenses for m in L["markers"] for c in m["dets"])
    print(f"refreshed {DEMO}: {len(lenses)} lenses, {cues} cues, {len(new)} bytes")

if __name__ == "__main__":
    main()
