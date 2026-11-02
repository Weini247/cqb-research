# E1 pilot: several threats, dead space, 52-dim plan space

> **Correction (review R1):** these gaps were computed on the same threat scenarios the
> plans were tuned on. On held-out scenarios the centre-fed gaps shrink to 0 % (M-center,
> L-center); corner-fed and small-room gaps are stable. See [REVIEW_R1.md](REVIEW_R1.md).

Status: exploratory pilot on the 8 development rooms, one optimizer seed (0), reduced budget
(CEM 20 x 32 x 4 weights). Primary outcome `risk_multi`: two hidden threats, 32 fixed
placements per room, one target per operator. Reproduce:
`python -m uv run killhouse-bench --seed 0 --iters 20 --out out/bench-e1b` (~17 min, one core,
with another batch job running in parallel) and
`python -m uv run killhouse-sens --out out/sensitivity-e1b.json`.

## What changed since the E1 draft

- **Several threats:** each operator engages one detected threat at a time, so a second threat
  is only suppressed by a second gun. A four-operator entry now lowers `risk_multi` clearly
  against the same plan with #3/#4 outside (M/L rooms: -5 to -10 points). With one threat,
  the difference had been negligible.
- **Dead space:** if a playbook leaves positions behind furniture unseen, one entered
  operator (#3/#4 first) moves, after holding its sector, to the free spot that sees most of
  them. All four techniques now clear M-center-box (before: none). Limited penetration still
  fails in L-corner-box, by design (only two operators enter).
- **Plan space:** 13 genes per operator, including the second position.

## Results (seed 0)

`R2` = `risk_multi`; `R2*` = best found at equal-or-better time and fratricide.

| room | crisscross R2 / gap | buttonhook R2 / gap | pie+crisscross R2 / gap | limited penetration R2 / gap |
|---|---|---|---|---|
| S-center | 0.676 / 32 % | 0.708 / 35 % | 0.484 / 15 % | 0.666 / 31 % |
| S-corner | 0.656 / 38 % | 0.802 / 49 % | 0.517 / 21 % | 0.778 / 48 % |
| M-center | 0.609 / 11 % | 0.696 / 19 % | 0.480 / 0 % | 0.713 / 21 % |
| M-corner | 0.601 / 14 % | 0.770 / 48 % | 0.507 / 21 % | 0.793 / 50 % |
| L-center | 0.638 / 0 % | 0.681 / 5 % | 0.500 / 9 % | 0.682 / 5 % |
| L-corner | 0.545 / 18 % | 0.790 / 52 % | 0.472 / 20 % | 0.803 / 53 % |
| M-center-box (+dead space) | 0.596 / 16 % | 0.678 / 26 % | 0.488 / 0 % | 0.693 / 27 % |
| L-corner-box | 0.675 / 12 % | 0.816 / 39 % | 0.610 / 19 % | invalid |

## Sensitivity (objective `risk_multi`, 16 variants x 8 rooms + baseline)

| claim (lower `risk_multi`) | holds in |
|---|---:|
| crisscross < buttonhook | 135 / 135 |
| pie+crisscross < crisscross | 135 / 135 |
| crisscross < limited penetration | 125 / 135 (exceptions: S-center, where both are 2-man entries) |

Mean Kendall tau of the ranking vs. baseline is 0.88-1.00 in every variant. The best
technique per room changes only once (L-corner-box at dwell 0.5 s).

## Findings

1. **The ranking is even more stable than with one threat.** Pie + crisscross < crisscross <
   buttonhook holds in every tested variant. Pie + crisscross costs 2.5-3 s.
2. **Gaps grow with several threats in small and corner rooms** (crisscross 14-38 %; buttonhook
   and limited penetration up to 53 %).
3. **Large rooms show small gaps (L-center crisscross 0 %). That is most likely a search
   budget problem, not optimality.** The plan space grew from 36 to 52 dimensions while the
   budget shrank to 20 iterations, and the number of valid evaluations in M/L-center dropped to
   445-549 (vs. 1100-2000 elsewhere). The confirmatory budget can only be fixed after the
   fast simulator (roadmap stage 4).
4. **#3/#4 now have a job.** In M/L-center rooms the best found strategies use all four
   operators. In small and corner rooms they still keep #3/#4 outside.
5. **The corner-fed pattern from the E1 draft appears again** in S-corner (the short-side
   operator #2 enters first, without delay, deep along the near side wall; #1 follows
   0.45 s later). In M/L-corner the best found order is #1 first, then #2 at 0.4-0.65 s. So
   the pattern is not stable across room sizes. Further reason to treat it as a hypothesis.

## Consequences

- Prereg: set the confirmatory budget only after stage 4 and verify search saturation (valid
  evaluations and front stability over iterations) as an explicit precondition.
- SME review: add question 6 (dead-space step) and the finding on #3/#4 in small rooms.
