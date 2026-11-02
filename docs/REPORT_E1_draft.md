# E1 draft: duel threat model, best found strategies, sensitivity

Status: exploratory, not preregistered. It extends [E0](REPORT_E0.md) with a threat model
and a sensitivity analysis. The doctrine models are still not SME-reviewed. Absolute risk values
depend on freely chosen rates; only comparisons are meant to be read.

Reproduce (one core each):

```
python -m uv run killhouse-bench --seed 0 --out out/bench-e1      # ~18 min
python -m uv run killhouse-bench --seed 1 --out out/bench-e1-s1   # ~25 min
python -m uv run killhouse-sens --out out/sensitivity.json        # ~15 s
```

## Why a threat model

E0 optimized raw exposure. There, extra entrants could only add exposure and never helped, so
the optimizer learned to keep #3/#4 outside. The duel model (see [CONCEPT](CONCEPT.md)) gives
every hidden threat a reaction time (0.3 s), a hit rate on the team (1/s) and a
neutralization rate per operator currently aiming at it (4/s). Risk `R` = probability that one
threat at a uniformly random hidden position hits the team.

Check: with the duel model, a four-man entry has equal or lower risk than the same plan with
#3/#4 outside in all 16 room x technique pairs (−0 to −3 %). With exposure alone, the
direction was the opposite.

## Doctrine vs. best found (seed 0 / seed 1)

`R*` = lowest risk found at equal-or-better time and fratricide. Gaps are relative risk
reductions; gap T is the time reduction at equal-or-better risk.

| room | technique | R | T [s] | R* (s0/s1) | gap R (s0/s1) | gap T (s0/s1) |
|---|---|---:|---:|---:|---:|---:|
| S-center | crisscross | 0.277 | 1.6 | 0.220 / 0.229 | 20 / 17 % | 6 / 6 % |
| S-center | buttonhook | 0.316 | 1.5 | 0.221 / 0.229 | 30 / 28 % | 0 / 0 % |
| S-center | pie+crisscross | 0.244 | 4.6 | 0.217 / 0.213 | 11 / 13 % | 67 / 67 % |
| S-center | limited penetration | 0.309 | 1.5 | 0.221 / 0.229 | 29 / 26 % | 0 / 0 % |
| S-corner | crisscross | 0.267 | 1.0 | 0.219 / 0.177 | 18 / 34 % | 10 / 10 % |
| S-corner | buttonhook | 0.401 | 1.6 | 0.189 / 0.176 | 53 / 56 % | 44 / 44 % |
| S-corner | pie+crisscross | 0.242 | 4.1 | 0.189 / 0.176 | 22 / 27 % | 76 / 76 % |
| S-corner | limited penetration | 0.388 | 1.6 | 0.189 / 0.176 | 51 / 55 % | 44 / 44 % |
| M-center | crisscross | 0.287 | 1.7 | 0.237 / 0.228 | 17 / 20 % | 6 / 12 % |
| M-center | buttonhook | 0.323 | 1.6 | 0.245 / 0.241 | 24 / 25 % | 0 / 6 % |
| M-center | pie+crisscross | 0.251 | 4.7 | 0.225 / 0.227 | 10 / 10 % | 66 / 66 % |
| M-center | limited penetration | 0.319 | 1.6 | 0.245 / 0.241 | 23 / 25 % | 0 / 6 % |
| M-corner | crisscross | 0.261 | 1.0 | 0.200 / 0.180 | 23 / 31 % | 10 / 10 % |
| M-corner | buttonhook | 0.419 | 1.6 | 0.189 / 0.180 | 55 / 57 % | 50 / 50 % |
| M-corner | pie+crisscross | 0.241 | 4.1 | 0.189 / 0.180 | 22 / 25 % | 76 / 78 % |
| M-corner | limited penetration | 0.416 | 1.6 | 0.189 / 0.180 | 55 / 57 % | 50 / 50 % |
| L-center | crisscross | 0.296 | 1.7 | 0.248 / 0.254 | 16 / 14 % | 12 / 6 % |
| L-center | buttonhook | 0.332 | 1.6 | 0.248 / 0.264 | 25 / 20 % | 6 / 0 % |
| L-center | pie+crisscross | 0.258 | 4.7 | 0.247 / 0.225 | 4 / 13 % | 68 / 64 % |
| L-center | limited penetration | 0.328 | 1.6 | 0.248 / 0.264 | 24 / 20 % | 6 / 0 % |
| L-corner | crisscross | 0.257 | 1.0 | 0.186 / 0.181 | 28 / 30 % | 10 / 10 % |
| L-corner | buttonhook | 0.448 | 1.6 | 0.182 / 0.181 | 59 / 60 % | 50 / 50 % |
| L-corner | pie+crisscross | 0.241 | 4.1 | 0.182 / 0.181 | 24 / 25 % | 78 / 76 % |
| L-corner | limited penetration | 0.445 | 1.6 | 0.182 / 0.181 | 59 / 59 % | 50 / 50 % |
| M-center-box | all | invalid: 3.3-5.1 % of threat positions never seen | | | | |
| L-corner-box | crisscross | 0.333 | 4.7 | 0.217 / 0.194 | 35 / 42 % | 13 / 19 % |
| L-corner-box | buttonhook | 0.489 | 5.6 | 0.310 / 0.194 | 37 / 60 % | 12 / 32 % |
| L-corner-box | pie+crisscross | 0.318 | 7.7 | 0.217 / 0.194 | 32 / 39 % | 47 / 51 % |
| L-corner-box | limited penetration | invalid: 12.9 % never seen | | | | |

## Sensitivity of the doctrine ranking

One-at-a-time variation of 8 axes, two values each: vision cone (half angle 40/60 deg), dwell
(0.2/0.5 s), turn rate (3/6 rad/s), threat reaction (0.15/0.6 s), threat hit rate (0.5/2 /s),
engagement rate (2/8 /s), door width (0.8/1.2 m), body radius (x0.85/x1.15). Doctrines only, no
optimizer.

| claim (lower risk) | holds in (variants x rooms) |
|---|---:|
| crisscross < buttonhook | 118 / 118 |
| crisscross < limited penetration | 118 / 118 |
| pie+crisscross < crisscross | 111 / 118 (all exceptions: 1.2 m door) |

Mean Kendall tau of the four-technique ranking vs. baseline is 1.00 for 12 of 16 variants.
It is 0.90 at engagement rate 2/s, 0.76 for 0.8 m doors and for 15 % wider bodies, and 0.67 for
1.2 m doors. With narrow doors or wider bodies, limited penetration becomes physically invalid
(bodies touch the door jambs), so body dimensions measurably matter.

## Findings

1. **The ranking among the stylized techniques is robust; the absolute numbers are not.**
   Crisscross beats buttonhook and limited penetration in every tested variant. Pie + crisscross
   has the lowest risk unless the door is wide, at 2.5-3 s extra time.
2. **All four techniques leave measurable risk on the table.** At equal-or-better time and
   fratricide, the best found strategies have 16-31 % less risk than crisscross and 20-60 % less
   than buttonhook and limited penetration. Results agree across both optimizer seeds within a
   few points, except in the small corner room and the furniture room.
3. **What the best found strategies do differently (corner-fed rooms):** The short-side
   operator (#2) enters first, almost without delay, and walks straight in deep along the near
   side wall. #1 follows 0.4-0.5 s later to a long-side position close to the entry wall. This
   resembles "the first man takes the most dangerous direction", but with the operator order and
   timing reversed. It is a hypothesis worth showing to an SME, not a recommendation.
4. **Centre-fed rooms:** The best found strategies look like a tighter crisscross. #1 goes almost
   immediately (0.0-0.5 s) to the far corner of the entry wall, and #2 follows 0.5 s later. The
   gain comes from timing, not from a different geometry.
5. **#3/#4 matter little against a single threat.** Most of the risk resolves before #3/#4 enter,
   so many best found strategies still keep them outside. With one threat this is near-neutral,
   not harmful. Multiple threats or follow-on rooms are needed to value the full team.
6. **Furniture is still unsolved.** Neither the static doctrines nor the optimizer (2-3 valid
   strategies out of ~4000 evaluations) clear the cabinet room. That needs an explicit
   dead-space move and a search that starts from feasible "walk behind the box" seeds.

## Next steps toward a preregistered E1

- Multiple threats (Poisson number of threats) and an adjoining room, so the full team has a job.
- A dead-space step in the doctrines; more geometries via a generator, with held-out seeds.
- Calibrate the rates against published reaction-time and hit-probability ranges, or report
  everything as functions of the rate ratio.
- SME review of the doctrine encodings and of finding 3. Proper literature review.
- Then freeze and preregister: H1 the gap is larger for corner-fed rooms (supported here for
  buttonhook / limited penetration, mixed for crisscross); H2 crisscross < buttonhook (robust
  here); H3 rankings survive the sensitivity grid.
