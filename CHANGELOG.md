# Changelog

## Unreleased (v0.2.1 and first part of v0.3-a, plan in [docs/PLAN_v0.3.md](docs/PLAN_v0.3.md))

- Golden test `tests/test_e1_golden.py`: main must reproduce the archived E1 numbers.
- Replay format `killhouse.replay/2` (`killhouse-replay`, `validate()`), conventions in
  [docs/CONVENTIONS.md](docs/CONVENTIONS.md); the viewer now reads only this format.
- Viewer: agent selection with live speed, heading and attention; attention ray; chase camera
  behind the selected agent; slow cinematic orbit; event marks on the timeline (cleared, door
  opened); share of seen positions; PNG and WebM export.
- Removed the spike-1 prototype (`building.py`, `sim.py`, old `replay.py`, `viewer.html`,
  `cli.py` and its test).

## 0.2.0 (2026-11-07): first confirmatory study

**Study E1**, preregistered and frozen before the run (tag `e1-prereg`), evaluated once on 40
held-out rooms ([REPORT_E1](docs/REPORT_E1.md)). Both hypotheses passed, within the model:

- H1: at equal room width the crisscross gap is 10.7 points larger for corner-fed doors
  (95 % CI 6.3-14.8, p < 0.0001); it holds for each optimizer family alone.
- H2: where both are valid, crisscross has lower risk than buttonhook in 23 of 31 rooms
  (74 %, p = 0.005).
- Two optimizer families agreed within 5 points in 65 % of room-technique pairs.

Methods added on the way:

- Reference cases with known solutions (comb gallery, L-corridor watchman route); they exposed a
  premature collapse of the cross-entropy search, fixed with random immigrants.
- CMA-ES as a second optimizer family; archives of all runs pooled; one candidate per technique
  chosen on planning scenarios and scored on held-out ones.
- Seed x budget saturation study, a dress rehearsal on 40 development rooms, and pre-freeze checks
  whose rules were committed before measuring (128 evaluation scenarios, calibrated H1 test).
- `killhouse-analyze`: the analysis plan as code, with a check of the room set.
- `killhouse-prefreeze`: scenario precision and test calibration on development rooms.
- Unrounded gaps, a zero-denominator rule, per-room crash-safe output.
- Four AI-assisted methodological reviews (R1-R4) with written responses.
- MIT licence.

## 0.1.0 (2026-11-02): first public state

Single-room and apartment models, stylized techniques, threat model, cross-entropy search,
GPU batch evaluation, sensitivity, robustness and adversary analyses, three.js viewer.
