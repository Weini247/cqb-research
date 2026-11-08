# Changelog

## Unreleased (v0.2.1 and v0.3-a to v0.3-d; plan in [docs/PLAN_v0.3.md](docs/PLAN_v0.3.md))

- House generator `house.py` (v0.3-d): single-floor houses with 8-12 rooms plus hallways, two
  topologies (long hallway, entry hall with cross corridor), spanning-tree doors, extra doors
  and open-plan openings, wall and free-standing furniture, walls derived once from the room
  rectangles; every room is guaranteed reachable (derived seed otherwise). `killhouse-search
  --building house`.
- `geom.visibility_fast`: the same visibility matrix on the GPU in float64 (0.6 s instead of
  16 s for a house), tested for equality; `geom.reachable`.

- Model v0.3 `sim2` ([docs/MODEL_SIM2.md](docs/MODEL_SIM2.md), `killhouse-search`): closed-loop
  agents with separate body heading and attention, per-agent knowledge, delayed messages,
  scripted coordinated search, waiting, side-stepping and giving way, wall clearance. Tests for
  information limits, motion limits and determinism. The E1 model is unchanged.
- Replay: optional per-agent `first_known` and `mode`, model name and
  `attention_equals_heading` from the source; viewer shows the selected agent's knowledge and
  mode, coverage label.

- Golden test `tests/test_e1_golden.py`: main must reproduce the archived E1 numbers.
- Replay format `killhouse.replay/2` (`killhouse-replay`, `validate()`), conventions in
  [docs/CONVENTIONS.md](docs/CONVENTIONS.md); the viewer now reads only this format.
- Viewer: agent selection with live speed, heading and attention; attention ray; chase camera
  behind the selected agent; slow cinematic orbit; event marks on the timeline (cleared, door
  opened); share of seen positions; PNG and WebM export.
- Viewer: side-by-side comparison of two runs with the same camera; animated figures (jointed
  body driven by idle and walk clips through an AnimationMixer, walk blended and time-scaled by
  the simulated speed, neck and head turned only by replayed attention minus heading); figure
  styles animated / test dummy / capsule (model view); image-based environment light; the walk
  cycle now advances in simulation time, also in slow motion.
- Headless viewer test (`tests/test_viewer_smoke.py`, `?selftest`): every run, camera, figure
  style and the split view, finite poses, walk clip at body speed (no foot sliding).
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
