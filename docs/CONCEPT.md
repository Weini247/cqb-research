# Concept: How close are established CQB room-entry techniques to the optimum?

Status: exploratory. Current model version: see `docs/RUNLOG.md` (plan space 52 dimensions,
13 per operator; primary outcome `risk_multi`). This document originally described E0. Nothing here is preregistered yet; E0 exists to make the model,
metrics and optimizer good enough that a preregistered study (E1) is worth running.

## Research question

Established room-entry techniques (crisscross, buttonhook, slicing the pie, limited
penetration) are human-derived heuristics for a hard problem: coordinated search of an
unknown space under visibility constraints, where every unseen point may hide a threat
that can see you before you see it (related theory: pursuit-evasion, graph clearing,
art-gallery / watchman problems).

**RQ:** On a family of room geometries, how large is the gap between stylized models of
these techniques and the best strategies found by black-box optimization in the *same*
action space, measured on the trade-off between exposure and time-to-clear?

Sub-questions:

1. Which geometry features (door position centre/corner, room size, obstacles) decide
   which technique is best?
2. Do optimized strategies resemble a known technique, a hybrid, or something new?
3. How sensitive are rankings to model assumptions (field of view, turn rate, body size,
   door width)?

## Model (single-room entry, `killhouse.entry`)

- Rectangular room `W x D`, entry wall at `y = 0`, door `[x0, x1]`, optional box obstacles;
  hallway outside (`y < 0`).
- Four operators with individual radius, height and speed, split stack (L, R, L, R).
- Per operator plan: entry start time, threshold crossing point, point of domination (POD),
  gaze target while moving and at the POD, optional pie-slicing arc before entry,
  enter / stay outside, how long to hold the own corner at the POD. Gaze turns with a limited rate; vision is a cone (default 100 deg).
- Threats are not simulated as agents. Every unseen floor point (0.25 m grid, at least
  0.25 m from walls and furniture) is a potential
  static threat with 360 deg vision; a point is cleared once it has spent a cumulative
  `DWELL = 0.3 s` inside some operator's vision cone with line of sight (perception is not
  instant: without dwell, standing in the doorway would clear a centre-fed room in 0.3 s at zero
  exposure, which is the opposite of the fatal-funnel experience).

- **Duel model (E1 draft).** For a single hidden threat at a uniformly random position: once
  it has had an operator in view for `threat_react = 0.3 s` it hits the team at
  `threat_rate = 1/s` while it still sees someone; after detection it is neutralized at
  `engage_rate = 4/s` per operator currently aiming at it. Risk `R` is the resulting
  probability that the team takes a hit. This replaces raw exposure as the primary objective:
  with exposure alone, extra entrants only add exposure and never help, so the optimizer kept
  #3/#4 outside. All three rates are sensitivity axes; only relative results are meaningful.

## Metrics

| metric | definition |
|---|---|
| risk `R` | P(team hit) under the duel model, averaged over threat positions (primary) |
| exposure `E` | sum over operators and time of the fraction of floor points that are still uncleared and have line of sight to the operator (seconds of whole-room exposure) |
| time to clear `T` | first time at which <= 0.5 % of points are uncleared |
| collision | integrated body overlap between operators (m*s) |
| wall | integrated body intrusion into walls, door jambs, obstacles (m*s) |
| fratricide | time an inside operator's muzzle line (+-7 deg) covers a visible teammate |

A strategy is valid if collision and wall < 0.02 and the room is cleared within the 12 s
horizon. Strategies are compared on the Pareto front of (R, T). The **optimality gap** of a
technique is the relative risk reduction that the best valid found strategy achieves at
equal-or-better time *and* equal-or-lower fratricide (`gap_risk`); `gap_time` is the
analogue for time at equal-or-better risk. Constraining fratricide relative to the doctrine
avoids tuning a hard threshold.

## Optimizer

Cross-entropy method over the 36-dim plan vector (9 per operator), seeded with the doctrine encodings,
scalarized `R + w*T + penalties` for several `w`; every feasible evaluation enters an archive
whose non-dominated set is the reported front. "Best found", not proven optimal.

## Known limitations (to be stated in every result)

No human factors (reaction time, stress, hit probability), no active adversary, no doors
that open, constant speeds, idealized perception. The doctrine models are stylized from
public descriptions and must be reviewed by a subject-matter expert before E1.

## Path to E1 (preregistered)

1. Literature review (room-clearing simulation, visibility-based search) and novelty check.
2. SME review of the doctrine playbooks.
3. Freeze geometry generator, metrics, optimizer budget, held-out geometry seeds.
4. Preregister hypotheses, e.g. H1: the gap is larger for corner-fed than centre-fed doors;
   H2: the best technique changes with room size; H3: rankings survive FOV 80-120 deg.
