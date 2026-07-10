# Tradecraft web — offline cue-floor demo

`demo.html` is a single self-contained page: paste text, and each lens's method markers fire with the
exact matched spans highlighted. **No server, no key, nothing sent anywhere** — it runs the
deterministic cue floor of the Tradecraft engine entirely in the browser. This is the web front door
for *detect the method, not the ideology*, and the take-home tool the DEFCON talk points its QR at.

Built 2026-07-03 as the prototype for the #1 item in the demo backlog (Tradecraft had a great engine
and no UI). Hosted preview: published as a Claude artifact — reshare from that link, or open
`demo.html` directly.

## What it is / isn't
- **Is:** the offline cue floor — literal substring markers from `detectors/*/taxonomy.yaml`, scored
  breadth × intensity × density per the lens config, with verbatim receipts and gold exemplars. Never a
  verdict; ideology-blind (the same lenses fire on every camp). Runs on a phone, on a Pi, on air-gapped.
- **Isn't (yet):** the full engine. Missing here — context verification (the cue floor over-fires;
  the real tool drops false positives before a hit stands), cloud/local/abliterated backends, and the
  network lenses (`revolving_door` has no text cues, intentionally omitted). The page says all this.

## Regenerate
`demo.html` carries a snapshot of the lens cues inline so it works standalone. Refresh it whenever the
taxonomies change:

```
python web/build-demo.py     # re-extracts cues from detectors/*/taxonomy.yaml, rewrites demo.html in place
```

Requires PyYAML.

## Next steps (to become the real web UI — see the demo backlog)
- Wrap `detect()` / `grade_document()` in a small Flask/FastAPI endpoint so the page can offer
  cloud + local (Ollama/abliterated) backends beyond the cue floor, with the verify-gate applied.
- Add "the Mirror" framing prominently (grade your own writing) — already invited on the page.
- Wire into the Atlas: node-click → run the lenses on that person's corpus, show verified receipts.
- Add the "occult = a register, not a moral fact" caveat to any UI surfacing adept_speech.
