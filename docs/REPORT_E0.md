# E0 report: doctrine vs. best found (exploratory)

Status: exploratory, single optimizer seed per run (seed 0, replication with seed 1 pending
below), stylized doctrines without SME review. Numbers describe *this model*, not real-world
effectiveness. Reproduce: `python -m uv run killhouse-bench --seed 0 --out out/bench-e0`
(~17 min, one core). Interactive report: `out/bench-e0/report.html`.

Model settings: vision cone 100 deg, perception dwell 0.3 s, turn rate 4 rad/s, dt 0.1 s,
horizon 12 s, clear criterion <= 0.5 % unseen threat positions, CEM 30 iterations x 32 samples
x 4 scalarization weights per room, seeded with the doctrine encodings.

## Results (seed 0)

`E` = exposure (s of whole-room line of sight to uncleared threat positions), `T` = time to
clear (s), `fr` = fratricide time (s), `E*` = lowest exposure found at `T* <= T` and `fr* <= fr`.

| room | technique | E | T | fr | E* | gap E | gap T |
|---|---|---:|---:|---:|---:|---:|---:|
| S-center | crisscross | 0.220 | 1.6 | 0.0 | 0.204 | 7 % | 25 % |
| S-center | buttonhook | 0.221 | 1.5 | 0.0 | 0.205 | 7 % | 20 % |
| S-center | pie+crisscross | 0.205 | 4.6 | 0.0 | 0.204 | 1 % | 67 % |
| S-center | limited penetration | 0.220 | 1.5 | 0.0 | 0.205 | 7 % | 20 % |
| S-corner | crisscross | 0.201 | 1.0 | 0.1 | 0.200 | 0 % | 10 % |
| S-corner | buttonhook | 0.308 | 1.6 | 0.1 | 0.200 | 35 % | 44 % |
| S-corner | pie+crisscross | 0.200 | 4.1 | 0.1 | 0.200 | 0 % | 76 % |
| S-corner | limited penetration | 0.301 | 1.6 | 0.1 | 0.200 | 33 % | 44 % |
| M-center | crisscross | 0.241 | 1.7 | 0.0 | 0.209 | 13 % | 24 % |
| M-center | buttonhook | 0.231 | 1.6 | 0.0 | 0.209 | 9 % | 19 % |
| M-center | pie+crisscross | 0.221 | 4.7 | 0.0 | 0.209 | 5 % | 70 % |
| M-center | limited penetration | 0.228 | 1.6 | 0.0 | 0.209 | 8 % | 19 % |
| M-corner | crisscross | 0.200 | 1.0 | 0.6 | 0.200 | 0 % | 20 % |
| M-corner | buttonhook | 0.353 | 1.6 | 0.5 | 0.200 | 43 % | 50 % |
| M-corner | pie+crisscross | 0.200 | 4.1 | 0.6 | 0.200 | 0 % | 78 % |
| M-corner | limited penetration | 0.342 | 1.6 | 0.1 | 0.200 | 41 % | 50 % |
| L-center | crisscross | 0.263 | 1.7 | 0.0 | 0.222 | 16 % | 29 % |
| L-center | buttonhook | 0.249 | 1.6 | 0.0 | 0.222 | 11 % | 25 % |
| L-center | pie+crisscross | 0.236 | 4.7 | 0.0 | 0.216 | 9 % | 68 % |
| L-center | limited penetration | 0.246 | 1.6 | 0.0 | 0.222 | 10 % | 13 % |
| L-corner | crisscross | 0.200 | 1.0 | 0.6 | 0.200 | 0 % | 20 % |
| L-corner | buttonhook | 0.417 | 1.6 | 0.5 | 0.200 | 52 % | 50 % |
| L-corner | pie+crisscross | 0.200 | 4.1 | 0.6 | 0.200 | 0 % | 78 % |
| L-corner | limited penetration | 0.403 | 1.6 | 0.1 | 0.200 | 50 % | 50 % |
| M-center-box | all four | invalid: dead space behind the cabinet never seen | | | | | |
| L-corner-box | crisscross | 0.432 | 4.7 | 0.6 | 0.206 | 52 % | 15 % |
| L-corner-box | buttonhook | 0.644 | 5.6 | 0.5 | 0.206 | 68 % | 29 % |
| L-corner-box | pie+crisscross | 0.427 | 7.7 | 0.6 | 0.206 | 52 % | 48 % |
| L-corner-box | limited penetration | invalid: dead space never seen | | | | | |

## Findings

1. **A perception floor dominates exposure.** In every room the lowest exposure found is
   0.20-0.22 s. That is `(dwell - dt) x` the fraction of the room the first entrant sees at once:
   someone has to look into the room, and every point that sees them stays dangerous until
   perceived. Techniques differ only in *excess* exposure above this floor. The floor follows
   from the dwell assumption, so its size is a modelling choice, not a finding about real rooms.
2. **Door position decides the ranking.** In corner-fed rooms crisscross (crossing to the long
   side) reaches the floor (gap 0 %), while buttonhook and limited penetration are 33-52 % worse:
   hooking toward the short side looks into a part of the room that is nearly empty while the
   long side watches you. In centre-fed rooms all four techniques sit within 1-16 % of the best
   found exposure. This geometry dependence is the clearest result of E0. Whether it matches
   practitioner guidance for corner-fed rooms is a question for the SME review.
3. **In centre-fed rooms the best found strategies are mainly faster.** Exposure gaps are small,
   but the optimizer clears 19-29 % sooner (T* 1.2-1.4 s vs. 1.5-1.7 s), mostly by earlier,
   tighter entry timing.
4. **Slicing the pie buys little exposure for a lot of time.** Pie + crisscross is on or near the
   low-exposure end everywhere (gap E 0-9 %) but needs 2.5-3 s more; at equal exposure the
   optimizer is 67-78 % faster.
5. **Static points of domination fail with furniture.** No stylized technique clears the dead
   space behind a cabinet in M-center-box. In L-corner-box the optimizer finds a valid strategy
   that sends #2 deep to look behind the box (E 0.206 vs. 0.43 for crisscross). In M-center-box
   the search found only one valid strategy: starting from four invalid seeds, the budget is too
   small.
6. **Model warning: entrants without a job.** Many best-found strategies keep #3/#4 outside.
   In this model extra entrants add exposure and never help, because nothing models engaging a
   threat, covering a teammate or holding a sector over time. This is the most important gap to
   close before E1, otherwise the optimizer "discovers" that half the team should stay home.

## What this means for the research question

E0 shows that the pipeline can produce non-trivial, geometry-dependent answers, and that the
gaps are concentrated where the stylized techniques move or look in the wrong direction for the
geometry. Before any headline claim, E1 needs:

- a threat model with engagement (detection gives the operator a reaction-time advantage, more
  guns on a sector reduce risk), so entering with four is not penalized by construction,
- dwell, FOV and turn rate as sensitivity axes (H3), and an exposure metric reported as excess
  over the per-room floor,
- dead-space clearing as an explicit doctrine step, and a larger search budget or restarts for
  furniture rooms,
- more geometries (generated, with held-out seeds), several optimizer seeds, confidence
  intervals,
- SME review of the four playbooks and a proper literature review. A first two-query web search
  found training material and an NPS thesis on audio cues in room-clearing simulation, but no
  quantitative optimization study of entry techniques. That is not yet a novelty claim.

## Replication (seed 1)

Pending: `out/bench-e0-s1/`.
