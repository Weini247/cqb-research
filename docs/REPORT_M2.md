# Report M2: method check (reference cases, seeds, budget)

Milestone M2 of the platform roadmap: before any confirmatory run, check that the visibility
code and the optimizer reproduce known answers, and measure how much a gap depends on the
optimizer seed and budget. Code: `src/killhouse/reference.py` (M2a, commit ee64dc1),
`src/killhouse/saturation.py` (M2b, commit b1ca549). Status: exploratory, development rooms only.

**Update (REPORT_G1_rehearsal.md):** the patterns below come from three rooms. On 40 generated
rooms, "corner-fed stable, centre-fed bimodal" does not hold in general, and the measured cost
of the full protocol is 5-7 h, not the estimates given here.

## M2a: reference cases with known solutions

| case | known answer | result |
|---|---|---|
| comb gallery, k = 2, 3, 4 teeth | exactly k observers (disjoint tip-seer sets prove the lower bound) | lower bound holds, greedy cover finds k, everything seen, for all three k |
| L-corridor watchman (straight walk from the start that sees every point) | 4.51 m (exhaustive search, 5 cm grid) | CEM without exploration: 11/20 seeds reach it; with 20 % random immigrants per generation: 20/20 |

The second case found a real optimizer defect: the CEM sampling distribution collapsed onto the
starting point or a poor basin before the optimum was sampled. `optimize.cem_minimize` now
replaces 20 % of every generation with uniform random samples (`explore=0.2`). The benchmark uses
the same function, so the fix applies there too. Tests: `tests/test_reference.py`.

## M2b: seed x budget saturation

Three development rooms (M-center, M-corner, L-center), four budgets (iterations x population:
20x32, 30x64, 60x64, 60x128, each x 4 objective weights), seeds 0-4. Gap = `gap_selected`
(one candidate per technique chosen on planning scenarios, scored on held-out scenarios).
Raw data: `out/saturation.json` (not versioned; regenerate with
`python -m killhouse.saturation`). Wall time about 1 h on the GPU backend.

Mean gap ± standard deviation across 5 seeds (n0 = seeds with gap < 0.5 %):

| room | technique | 20x32 | 30x64 | 60x64 | 60x128 |
|---|---|---|---|---|---|
| M-corner | crisscross | 22 ± 5 | 31 ± 3 | 33 ± 1 | 31 ± 3 |
| M-corner | buttonhook | 49 ± 2 | 52 ± 1 | 52 ± 1 | 52 ± 3 |
| M-corner | pie + crisscross | 18 ± 3 | 23 ± 2 | 23 ± 2 | 22 ± 4 |
| M-corner | limited penetration | 50 ± 2 | 53 ± 1 | 53 ± 1 | 52 ± 2 |
| M-center | crisscross | 0 ± 0 (n0 5) | 2 ± 5 (n0 4) | 14 ± 9 (n0 1) | 15 ± 13 (n0 2) |
| M-center | buttonhook | 1 ± 1 (n0 4) | 0 ± 0 (n0 5) | 6 ± 9 (n0 3) | 16 ± 14 (n0 1) |
| M-center | pie + crisscross | 2 ± 2 | 4 ± 3 | 7 ± 5 | 11 ± 4 |
| M-center | limited penetration | 1 ± 1 (n0 4) | 0 ± 0 (n0 5) | 6 ± 9 (n0 3) | 16 ± 14 (n0 1) |
| L-center | crisscross | 0 ± 0 (n0 5) | 9 ± 8 (n0 1) | 14 ± 7 | 11 ± 11 (n0 2) |
| L-center | buttonhook | 0 ± 0 (n0 5) | 3 ± 8 (n0 4) | 8 ± 13 (n0 3) | 7 ± 11 (n0 3) |
| L-center | pie + crisscross | 3 ± 5 | 9 ± 6 | 10 ± 7 | 13 ± 4 |
| L-center | limited penetration | 0 ± 0 (n0 5) | 3 ± 8 (n0 4) | 7 ± 13 (n0 3) | 6 ± 11 (n0 3) |

(values in %, rounded)

### Findings

1. **Corner-fed door: saturated.** From 30x64 on, the means move by at most 2 points and the
   seed spread is 1-4 points. The best risk found is about 0.375 for every technique and seed.
   Gaps of 22-53 % here are reproducible within this model.
2. **Centre-fed doors: not saturated, bimodal.** The best seeds find strategies 15-30 % below the
   technique, while other seeds at the same budget return the technique itself (gap 0). Raising
   the budget makes the successful seeds more frequent but does not remove the zeros, even at
   60x128. A per-seed gap of 0 therefore does **not** mean the technique is optimal; it means this
   run did not leave its starting point.
3. **The within-run saturation criterion in the draft prereg is insufficient.** A run that never
   leaves the seeded technique shows no change in its front and would pass "front changes < 2 %
   over the last 25 % of iterations" while being far from the best known value. Saturation has to
   be judged across seeds.
4. **The median over seeds is a poor estimator here.** With 3 of 5 seeds at 0, the median is 0
   although two seeds show 15-30 %. Pie + crisscross is the exception: it is the strongest
   technique in centre-fed rooms, its gaps are smaller and never 0 at 30x64 or more.

### Consequences for the preregistration (proposed, not yet frozen)

- **Budget:** 60 iterations x 64 samples x 4 weights per seed. It is saturated for the corner-fed
  door. 60x128 doubles the cost without removing the bimodality. Expected cost about 100 s per
  room and seed, roughly 6 h for 40 rooms x 5 seeds.
- **Estimator:** pool the archives of all 5 seeds per room. Then pick one candidate per technique
  on planning scenarios only and score it on held-out scenarios. This is a multi-start search
  with the same leak protection as before. Report the per-seed spread and the number of seeds
  that leave the technique as a reliability measure next to the gap.
- **Saturation check:** across seeds, not within a run. A room counts as saturated when the
  pooled best is reached by at least 3 of 5 seeds within 2 % of risk. Unsaturated rooms are
  reported and kept, with their gaps marked as lower bounds.
- **Interpretation:** all gaps stay lower bounds on what is attainable in the model. Centre-fed
  gaps are expected to be underestimated more than corner-fed ones.

### Pilot of the pooled estimator

Implemented in `bench.py` (`--seeds N`, functions `select` and `saturation`). Pilot:
`killhouse-bench --rooms M-center L-center --iters 60 --pop 64 --seeds 5` (10 min on the GPU).
The per-seed gaps reproduce the 60x64 rows of the saturation study exactly, so the runs are
deterministic per seed.

| room | technique | pooled gap | per-seed gaps (%) | seeds at pooled best | seeds leaving the technique |
|---|---|---|---|---|---|
| M-center | crisscross | 23 % | 11, 17, 19, 0, 23 | 2/5 | 4/5 |
| M-center | buttonhook | 15 % | 0, 0, 15, 0, 16 | 2/5 | 2/5 |
| M-center | pie + crisscross | 15 % | 5, 15, 6, 3, 6 | 1/5 | 5/5 |
| M-center | limited penetration | 15 % | 0, 0, 15, 0, 16 | 2/5 | 5/5 * |
| L-center | crisscross | 26 % | 26, 8, 13, 11, 10 | 1/5 | 5/5 |
| L-center | buttonhook | 30 % | 30, 0, 0, 0, 8 | 1/5 | 2/5 |
| L-center | pie + crisscross | 20 % | 8, 20, 4, 13, 7 | 2/5 | 5/5 |
| L-center | limited penetration | 29 % | 29, 0, 0, 0, 7 | 1/5 | 2/5 |

\* "leaving" is measured on planning risk with a 0.5 % tolerance; here the seeds left by a
fraction of a percent, which does not show on held-out scenarios.

- No centre-fed technique reaches the saturation rule (at least 3 of 5 seeds at the pooled best).
  Under the proposed prereg these gaps would be reported as lower bounds.
- Pooling matters: for M-center buttonhook the median over seeds is 0 %, the pooled gap 15 %.
  The pooled pick is still one candidate chosen on planning scenarios only, so it adds search
  effort, not a held-out selection bias.
- In M-center the pooled best for crisscross, buttonhook and limited penetration is the same
  strategy (planning risk 0.481): the techniques differ, the reachable optimum does not.

## M2c: cross-check with a second optimizer family (CMA-ES)

`optimize.cmaes_minimize`: standard CMA-ES (Hansen's default parameters, full covariance, no
restarts, no tuning on these rooms), same plan space, same starting playbooks, same budget
(60x64 per weight, 5 seeds, pooled). On the reference cases: a shifted sphere is solved, and
the L-corridor watchman optimum is found in 17/20 seeds (CEM with immigrants 20/20, without
11/20). Run: `killhouse-bench --optimizer cmaes --seeds 5 --iters 60 --pop 64`
(`out/cmaes-check`, 12 min), compared with the pooled CEM runs (`out/pooled-pilot`,
`out/pooled-corner`).

| room | technique | CEM pooled gap | CMA-ES pooled gap | CMA-ES per-seed gaps (%) |
|---|---|---|---|---|
| M-center | crisscross | 23 % | 16 % | 0, 0, 16, 0, 7 |
| M-center | buttonhook | 15 % | **22 %** | 0, 0, 22, 0, 14 |
| M-center | pie + crisscross | 15 % | 12 % | 12, 5, 4, 7, 1 |
| M-center | limited penetration | 15 % | **22 %** | 0, 0, 22, 0, 14 |
| M-corner | crisscross | 35 % | 32 % | 24, 27, 32, 27, 22 |
| M-corner | buttonhook | 53 % | 52 % | 46, 46, 51, 52, 44 |
| M-corner | pie + crisscross | 25 % | 22 % | 16, 16, 21, 22, 17 |
| M-corner | limited penetration | 54 % | 47 % | 47, 47, 50, 46, 47 |
| L-center | crisscross | 26 % | 15 % | 0, 15, 0, 20, 14 |
| L-center | buttonhook | 30 % | 22 % | 11, 22, 0, 24, 21 |
| L-center | pie + crisscross | 20 % | 11 % | 15, -2, 8, 11, 1 |
| L-center | limited penetration | 29 % | 22 % | 11, 22, 0, 23, 20 |

### Findings

1. **The centre-fed gaps are not a CEM artefact.** CMA-ES also finds strategies 11-22 % below
   every technique in both centre-fed rooms.
2. **The bimodality is not CEM-specific either.** CMA-ES seeds also split into "stays at the
   technique" (0 %) and 14-24 %. Both methods start from the playbooks, so this points to a
   start basin that is hard to leave, not to one optimizer's weakness.
3. **Neither method dominates.** CEM is better in 10 of 12 cases (by 1-11 points), CMA-ES in
   M-center buttonhook and limited penetration (by 7 points). The gap of a single method is
   therefore a lower bound that can be off by about 10 points.
4. **The gap ranking between techniques depends on the optimizer in centre-fed rooms.** With CEM,
   crisscross has the largest gap in M-center (23 % vs. 15 %); with CMA-ES, buttonhook and limited
   penetration do (22 % vs. 16 %). In the corner-fed room both methods agree on the order
   (limited penetration ~ buttonhook > crisscross > pie + crisscross) and on the size within
   1-7 points. This is a direct instance of the research question: a comparison that looks
   like a property of the techniques is partly a property of the evaluation protocol.
5. **The across-seed rule from M2b is miscalibrated.** With a 2 % risk tolerance even the
   corner-fed room, whose gaps vary by only 1-4 points across seeds, has only 1-2 of 5 seeds
   "at the best". The rule does not separate the stable room from the unstable ones.

### Consequences for the preregistration (proposed, replaces the M2b proposal)

- Run **both optimizer families** (CEM and CMA-ES, 5 seeds each, 60x64x4) and pool all ten
  archives; select one candidate per technique on planning scenarios from the pooled archive.
  Measured cost in the rehearsal: about 4.9 h for 40 rooms (the 13 h estimated here was too high).
- **Agreement instead of the 2 % seed rule:** a room-technique pair is "method-stable" when the
  two single-method pooled gaps differ by at most 5 points. Pairs that are not are kept and
  reported as lower bounds; the share of method-stable pairs is itself a reported outcome.
- Hypotheses about gap *differences between techniques* (H1) are tested on the pooled gap and
  repeated on each method alone; a result that holds for only one method is reported as such.

### Limitations

- Three rooms, five seeds; no confidence intervals beyond the seed spread.
- Two optimizer families, both distribution-based and both started from the playbooks. A
  structurally different searcher (for example a local search on the discrete structure:
  who enters, in which order, which point of domination) is not covered.
- The 5-point agreement tolerance and the decision to run both families were set after seeing
  these three development rooms; they are fixed before the confirmatory rooms are touched.
- With 1-2 of 5 seeds at the best, 5 seeds may be too few for centre-fed rooms; a second
  optimizer family is the more informative next check than a larger CEM budget.
