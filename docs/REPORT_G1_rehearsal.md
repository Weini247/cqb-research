# Report G1: dress rehearsal of the E1 protocol on 40 development rooms

Purpose: run the planned E1 protocol end to end before the freeze, on rooms that are **not** the
confirmatory ones. Rooms: `generated_rooms(1, 40)`. Status: **exploratory**. These rooms shaped
the changes below, so nothing here counts as confirmation. `generated_rooms(2026, 40)` was not
touched. Code: commit 9f26cab, CEM + CMA-ES, 60x64x4, 5 seeds each, all 10 archives pooled.

The run was interrupted after 30 rooms, probably by an application update on the host (the
cause is not proven; the error log is empty). G1-30 to G1-39 were computed in a second run, with
G1-29 repeated as a control. All 100 result fields of the control room, its number of valid
evaluations and its front were identical, so the two parts can be merged. Raw data:
`out/rehearsal-g1`, `out/rehearsal-g1b`, merged `out/rehearsal-g1-merged/rooms.jsonl`
(not versioned).

## Runtime

Without the repeated control room, the 40 rooms took about 4.9 h of compute (437 s per room).
The earlier estimate of 13 h was wrong. The same room G1-29 took 413 s in the first run and
561 s in the second, so the time depends on other load on the machine as well. Plan for 5-7 h.

## Results

**Validity:** 135 of 160 room-technique pairs are valid. 18 of the 25 invalid pairs are collisions
of the three crossing techniques, which are invalid together in 7 rooms. In G1-39 no technique
is valid. The other 7 did not clear the room in time.

**Gaps** (pooled, one candidate chosen on planning scenarios, scored on held-out scenarios):

| technique family | n | median | mean | range |
|---|---|---|---|---|
| crisscross | 33 | 30 % | 30 % | 12-45 % |
| buttonhook | 33 | 37 % | 36 % | 0-56 % |
| pie + crisscross | 33 | 20 % | 19 % | 2-30 % |
| limited penetration | 36 | 36 % | 33 % | 0-52 % |

No pooled gap is negative. All gaps are lower bounds in the model, not effect sizes in reality.

**Agreement of the optimizers:** 77 of 135 pairs (57 %) are method-stable (at most 5 points
apart), 60 % in corner-fed and 53 % in centre-fed rooms; all pairs agree in 13 of 40 rooms. The
median difference is 3.9 points, the maximum 27.7. CEM has the larger gap in 75 pairs, CMA-ES in
51, 9 are ties. As a rough reference, splitting each pair's ten runs at random into two halves
gives 78 % within 5 points (a proxy that uses the best held-out gap of each half), so even
interchangeable methods would not reach 100 %.

**Runs:** the ten runs of a pair differ by 15 points (median of max - min). The mean best of k
runs (proxy, held-out) is 24.1 % for k = 1, 30.7 % for k = 5 and 32.4 % for k = 10. The pooled
gap averages 30.8 %, the median of the runs 24.3 %. Pooling therefore matters, and more runs
would add little, as far as the runs can show: basins that no run reached stay invisible.

**Time floor:** in 5 pairs no run leaves the technique, all at `t_clear` = 0.9 s, which is also
the fastest time in those rooms' fronts. The "equal or better time" rule leaves no room there,
so these zeros are not search failures. Without them, 90 of 1300 runs (7 %) stay at the technique.

**Overfitting to planning scenarios:** 26 of 1350 runs and 2 single-method gaps
(G1-17 CEM -10 %, G1-28 CMA-ES -11 %) are negative on held-out scenarios. Pooling removed both.

**Fratricide:** 54 of 135 valid pairs have a value above 0, up to 8.1. Validity ignores it. Gaps
are similar with and without it (means 28 % and 31 %).

## Trial of the hypotheses (not a test)

| hypothesis | result on the 40 rehearsal rooms |
|---|---|
| H1 as drafted (door centre <= 1.6 m from a side wall) | 33.9 % (n = 21) vs. 24.6 % (n = 12), difference 9.3 points, CI [2.5, 22.2] |
| H1, CEM alone / CMA-ES alone | 9.2, CI [2.1, 21.1] / 7.3, CI [-0.6, 21.2] |
| H1, door in the outer third of the wall instead | 8.8 points, CI [-1.5, 18.5] |
| H1 adjusted for room width | corner-fed +5.8 points, CI [1.0, 11.3], one-sided p = 0.007; width -3.2 points per metre |
| H1 adjusted, CEM alone / CMA-ES alone | +6.1, CI [-0.1, 14.2], p = 0.027 / +4.8, CI [-1.6, 11.3], p = 0.063 |
| H2 crisscross < buttonhook | 25 of 33 rooms (76 %), one-sided p = 0.002; corner-fed 14 of 21 (67 %), centre-fed 11 of 12 (92 %) |
| H3, H4 | not covered: this run does not produce the data |

All numbers of the adjusted rows come from `killhouse-analyze` on the two result files; it
confirms that they hold exactly `generated_rooms(1, 40)`. The adjusted H1 passes on the pooled gap
but neither optimizer family alone has a CI above 0, so it is a weak effect at this sample size.

After 30 rooms H1 looked much stronger (14 points). The last 10 rooms reduced it, which shows how
unstable a median difference over 12 rooms is. The gap falls with room width (r = -0.68) about as
strongly as with door distance (r = -0.65), and the two are linked (r = 0.59), because in narrow
rooms nearly every door is near a side wall. 7 of 40 rooms change class under the relative
definition.

## What changes against earlier statements

- REPORT_M2 said the corner-fed door is stable and centre-fed doors are bimodal. That came from
  three rooms and does not generalize: agreement is 60 % vs. 53 %, and stuck runs are rare here.
- The optimizer changes the technique with the largest gap in 5 of 33 rooms: real, but a minority.
- Crisscross beats buttonhook in 76 % of generated rooms, against 164/165 in the sensitivity
  variants of the standard rooms. Those numbers answer different questions and must not be mixed.

## Consequences

The changes are in PREREG_E1_draft.md (change log 2026-11-04). The draft is **not frozen**. Still
open before the freeze: a review, and a decision on how H3 and H4 get their data.
