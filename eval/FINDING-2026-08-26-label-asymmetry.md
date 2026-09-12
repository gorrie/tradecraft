# The pejorative-label vocabulary is one-directional, and today's restore doubled it

This is a finding against the program's central claim, verified directly rather than
argued. It is also partly self-inflicted: the restore committed earlier today took the
imbalance from 4–0 to 8–0.

## The claim the taxonomy makes about itself

`tradecraft/detectors/sourcing_asymmetry/taxonomy.yaml:14`:

> METHOD of imbalance, never the position taken; flags with receipts, never a verdict,
> **never a left/right**

## The vocabulary underneath it

Line 67, `pejorative-actor-label`, as shipped after today's restore:

```yaml
cues: ["cronies", "maga extremist", "fringe group", "fringe figure",
       "regime", "far-right", "hardline", "extremist"]
```

Eight cues. Every one is an epithet applied to a right-coded or adversary actor. Probing
eleven mirrors against the **entire 15-lens taxonomy**, not just this detection —
`far-left`, `radical left`, `marxist`, `socialist`, `woke`, `globalist`, `RINO`, `leftist`,
`communist`, `antifa`, `radical democrat` — **none is present anywhere.**

## Reproduction

Two sentences of identical construction, mirrored in political direction:

| input | hits |
|---|---:|
| "The senator, a **far-left radical** and avowed **socialist**, addressed the crowd. Critics called the **marxist** agenda a **globalist** project." | **0** |
| "The senator, a **far-right extremist** and **hardline** nationalist, addressed the crowd. Critics called the **regime** a **fringe** project." | **1** |

The detection can only fire on prose that labels the right. An op-ed calling someone a
far-left radical is invisible to a lens whose stated purpose is catching exactly that move.

(The right-hand sentence scores 1 rather than 4 because `detect_cues` records one hit per
detection and breaks — a separate defect, noted below.)

## How today's work made it worse, and why the measurement did not catch it

`PREREG-2026-08-26-label-cue-restore.md` restored `regime`, `far-right`, `hardline` and
`extremist` on a pre-registered test they won decisively: cues-only lift 1.12 → 1.77,
human-annotated retention 1-of-4 → 12-of-19, with `far-right` scoring 5/5 genuine and
`hardline` 4/4.

**That measurement was valid and it is not the issue.** Precision and symmetry are different
axes, and only one of them was measured. Worse, the two interact in a way that should have
been anticipated: the test corpus is news, news labels the right far more often than the
left, so one-directional cues score *well* on precision precisely because the labelling they
detect is real and one-directional in that corpus. A high genuine rate on `far-right` is
evidence the cue works, and evidence of nothing at all about whether the lens is symmetric.

Before today the list was 4–0 (`cronies`, `maga extremist`, `fringe group`, `fringe
figure`). It is now 8–0. The asymmetry predates this session; the amplification does not.

## What the fix is — and is not

**Not** reverting the restore. That returns the list to 4–0: still one-directional, and now
also worse at detecting, since three of the four original cues (`maga extremist`, `fringe
group`, `fringe figure`) never fire on anything.

The fix is **adding the mirrors** so the detection catches the move in both directions.
That is authoring on the taxonomy — it changes what the Ratchet's instrument detects and it
is a claim about political language — so it is the author's call, not mine to execute.

Whichever way it goes, the symmetry property should stop being an assertion in a comment
and become a **test**: a fixture pair per directional detection, mirrored, asserting equal
firing. A claim the file makes about itself in prose is exactly the kind of thing that
drifts away from the data underneath it.

## Exposure

The cue lists ship to the browser. `tools/export_web.py` emits every cue into
`instrument.json` by design — that is the anti-drift mechanism, and it means view-source on
the public demo shows this list beside the taxonomy's own "never a left/right". One
screenshot, no skill required.

## A related defect, measured

`subculture_register`'s top-firing cue on 371 news articles is **`make america great again`
(4 fires)** — a topic word, not a register tell. It will flag a straight wire report about a
rally as MAGA true-believer register. The lens's own accelerationist-right DEFAMATION NOTE
warns about exactly this opposite-speaker failure.

## What is NOT supported

A wider claim was put to this check and the data does not carry it: that
`subculture_register`'s left-camp cues fire on mainstream prose while its right-camp cues
only fire on the fringe. Across 371 articles the lens fires **4 times total** from 170 cues
— `make america great again` (4), `social kingship`, `white privilege`, `uncle ted` (1
each). That is too thin to support any claim about relative firing rates in either
direction, and the one clear signal points the other way. Recorded because a finding that
sounds right and is unmeasured is the thing this file exists to object to.
