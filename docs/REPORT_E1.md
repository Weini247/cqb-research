# Report E1: confirmatory study on 40 held-out rooms

Preregistration: [PREREG_E1_draft.md](PREREG_E1_draft.md), frozen at tag `e1-prereg` (commit
25f8197) before any evaluation of the confirmatory rooms. This study ran on exactly that commit.
Everything in the sections "Preregistered tests" and "Reliability" follows the plan; everything
under "Exploratory" is labelled as such.

All results are **model-internal**. The technique names denote stylized movement models in an
abstract, uncalibrated simulation. No statement about real procedures, real teams or real
rankings follows from them.

## Run

- Rooms: `generated_rooms(2026, 40)`, SHA-256 `90a6edac...4a315`, identical to the value in the
  preregistration (checked by `killhouse-analyze --generated 2026 40`).
- Procedure: four technique families; CEM and CMA-ES, 5 seeds each, 60 x 64 x 4, all ten archives
  pooled; one candidate per technique chosen on 32 planning scenarios and scored on 128 held-out
  scenarios.
- Run on 2026-11-07, 11:58 to 15:51 (3.9 h, 344 s of search per room), outside the app via the
  Windows task scheduler; error log empty. The analysis ran automatically afterwards.
- Data: [`data/e1/results.json.gz`](../data/e1/results.json.gz) (unpack, then
  `killhouse-analyze results.json --generated 2026 40`) and
  [`data/e1/analysis.json`](../data/e1/analysis.json).
- Deviations from the plan: **none**.

## Validity

131 of 160 room-technique pairs are valid. 17 invalid pairs did not clear the room in time, 12
are collisions of the crossing techniques. In G2026-32 no technique is valid. The dead-space step
was added in 18 rooms. No gap is undefined and none is negative.

## Preregistered tests

| | result | decision |
|---|---|---|
| **H1** crisscross gap, corner-fed vs. centre-fed, adjusted for width (31 rooms, 15 corner-fed) | **+10.7 points**, 95 % CI [6.3, 14.8], one-sided p < 0.0001 (no resample <= 0 of 10 000), Holm p < 0.0001 | **supported** |
| **H2** crisscross lower risk than buttonhook (31 rooms where both are valid) | **23 wins, 8 losses, 0 ties (74 %)**, sign test p = 0.0053, Holm p = 0.0053 | **supported** |

H1 also holds for each optimizer family alone: CEM +11.2 points, CI [7.3, 15.2]; CMA-ES +13.5,
CI [7.9, 18.5]. The secondary readings agree: unadjusted difference of medians +9.9 points
(34.2 % vs. 24.4 %), CI [3.8, 16.9]; door in the outer third of the wall +9.0, CI [3.5, 16.8]. The
width ranges of both door classes overlap (3.5-7.75 m and 3.75-7.5 m). H1 is a width-adjusted
association within valid rooms, not a causal door effect.

H2 is limited to rooms where both techniques are valid; in 9 rooms at least one of them was not.
Reported separately without a decision rule: in **centre-fed** rooms crisscross wins in all 16,
in **corner-fed** rooms only in 7 of 15 (47 %).

## Gaps

The gap is the relative risk reduction that the fixed search procedure finds below a technique,
at equal or better time and fratricide. It is a Monte-Carlo estimate for this budget, not a
global optimality gap and not a guaranteed lower bound.

| technique family | n | median | range | with fratricide > 0 |
|---|---|---|---|---|
| crisscross | 31 | 31 % | 16-46 % | 18 |
| buttonhook | 33 | 32 % | 0-52 % | 21 |
| pie + crisscross | 31 | 23 % | 11-32 % | 18 |
| limited penetration | 36 | 32 % | 0-51 % | 13 |
| all | 131 | 29 % | 0-52 % | 70 |

## Reliability (descriptive)

- The two optimizer families agree within 5 points in 85 of 131 pairs (65 %): 73 % in corner-fed
  and 57 % in centre-fed rooms; all pairs agree in 18 of the 39 rooms with a valid technique. CEM
  found the larger gap in 65 pairs, CMA-ES in 44.
- In 10 pairs (all buttonhook or limited penetration) no run found an improvement and the
  technique already has the fastest time in the front. Search failure is not excluded there.
- Of the remaining runs, 94 of 1210 (8 %) stay at the technique. The ten runs of a pair differ by
  16 points (median of max - min). Mean best of 1, 5 and 10 runs: 22 %, 29 %, 31 %.

## Exploratory

- Compared with the dress rehearsal (development rooms), H1 is stronger here (+10.7 vs. +5.8
  points), and the gap depends much less on room width (-0.7 vs. -3.2 points per metre). The
  rehearsal had 32 evaluation scenarios, E1 has 128, and the room sets differ, so the two cannot
  be compared directly.
- The H2 split by door class is the most striking pattern: the crisscross advantage over
  buttonhook comes entirely from centre-fed rooms. Whether this survives other model assumptions
  is a question for a separate study.

## What this does and does not show

It shows that, in this model and with this search procedure, two preregistered comparisons hold
on rooms that were never used for development: the gap of crisscross depends on the door
position at equal width, and crisscross has lower risk than buttonhook where both are valid. It
does not show that either holds outside the model, for real teams or under other assumptions. The
reliability numbers show how much of a single gap depends on the optimizer (35 % of pairs differ
by more than 5 points), which is the main methodological finding for the research question of how
strongly comparisons depend on the evaluation protocol.
