# Tactic catalog

Every technique encoded in `killhouse/tactics.py`, with its source, how it is encoded, where
it applies, and its review status. The encodings stay at the level of geometry and sequence
described in public sources: stack, order, path through the door, point of domination,
sectors and timing. Weapons handling, breaching and anything beyond public descriptions
are deliberately left out.

**Naming (review R1, P0):** The names (crisscross, buttonhook, …) label *stylized,
unvalidated movement models* that are loosely based on the cited descriptions. They do not
claim to reproduce any unit's procedure, and their representativeness is a separate open
question for an instructor review. Results are model-internal optimization findings.

**Status:**
- *coded from source*: follows a public description directly.
- *adapted*: needed my own decisions where the source is not specific, marked below.
- *SME confirmed*: reviewed by an instructor. None yet; see [SME_REVIEW.md](SME_REVIEW.md).
  Review R1 ([REVIEW_R1.md](REVIEW_R1.md)) was a source-based methodological review, not an
  instructor review, and confirms no technique.

Sources are cited as documents and sections. The original text of FM 3-06.11 para. 3-22 has
not yet been checked line by line against the encodings; the current wording comes from the
table of contents plus secondary descriptions. That check is part of the review.

## Sources

- **[FM]** FM 3-06.11 *Combined Arms Operations in Urban Terrain*, US Army, 28 Feb 2002,
  ch. 3 "Urban Combat Skills", para. 3-22 "Techniques for Entering Buildings and Clearing
  Rooms". Successor: ATTP 3-06.11 (2011).
- **[CALL]** CALL Newsletter 97-20, battle drill "Enter building / clear room", US Army
  Center for Army Lessons Learned, 1997.
- **[PR]** Public practitioner material on room entry (police and military training
  articles, e.g. on slicing the pie vs. buttonhook).

## Room entry

| id | technique | stack | encoding | sources | status |
|---|---|---|---|---|---|
| `crisscross` | Crisscross | split | #1 and #2 start on opposite sides, cross through the doorway to the opposite near corners; #3/#4 follow to shallower positions on the opposite side of the operator ahead | FM, CALL | coded from source |
| `buttonhook` | Buttonhook | split | #1 and #2 turn around the frame and stay on their own side, along the entry wall | FM, CALL | coded from source |
| `combination-cross` | Combination, cross first | single side | whole team on one side; #1 crosses to the far side, #2 hooks back to the near side, #3/#4 alternate | FM, PR | adapted: role order and #3/#4 targets |
| `combination-hook` | Combination, hook first | single side | as above, #1 hooks, #2 crosses | FM, PR | adapted |
| `two-man` | Two-man entry | split | crisscross by #1/#2; #3/#4 hold outside (rear security) | FM | adapted: when two-man is chosen |
| `limited` | Limited penetration | split | #1/#2 step in beside the frame and clear from the threshold, near corner first then far corner; #3/#4 outside | PR | adapted: depth 0.7 m |
| `pie-crisscross` | Slicing the pie + crisscross | split | #1 walks an arc (r = 1.4 m) outside the door looking in, then dynamic crisscross | PR | adapted: arc radius, then crisscross |
| `deliberate` | Deliberate entry | split | pie, then entry at 0.6x speed, 1.2 s spacing, 1.0 s corner hold, crisscross geometry | FM, PR | adapted: the numbers |

**Geometry adaptations** (apply to all entries, see `doctrine.py`):
- **Corner-fed doors:** the short-side operator goes straight in along the near side wall.
- **Small rooms (< 4.5 m wide):** only the first two in the order of march enter.
- **Dead space** (furniture, the pocket behind an open door): one entered operator, #3/#4
  first, moves after holding its sector to the free spot that sees most of the hidden area.

## Team sizes

Every entry can be built for 2, 3 or 4 operators; smaller teams use the first n roles.

## Apartments and hallways

| item | encoding | status |
|---|---|---|
| Hallway entry | two-man corridor technique: #1 deep along the hallway, #2 offset behind, #3/#4 hold the landing | adapted |
| Room order | depth first from the hallway, nearest door to the entrance first | adapted |
| Rear security | operators who do not enter aim along the hallway away from the door | adapted |
| **Door watch (hallway discipline)** | while the team moves, #3/#4 aim at open doors of uncleared rooms within 3.5 m | adapted |

First result (3 apartments x 4 techniques): door watch lowers the single-threat risk R1 in
all 12 pairs, by up to 6 points, at unchanged time. The two-threat risk R2 is lower in 9 pairs,
equal in 2, and 0.001 higher in 1.

**Still missing:** L-corners and T-junctions (need a corridor-junction generator), closed
doors, opening doors (push/pull), stairs.

## Execution noise

`tactics.perturb` adds Gaussian noise to each operator's start time (0.25 s), points of
domination (0.25 m per axis), gaze targets (0.15 rad) and entry speed (10 %).
`robust_eval` reports the mean and 90th percentile of the risk over k noisy executions, plus
two fractions: executions that stay valid, and executions that leave threat positions unseen.
This is the base for the robustness question in roadmap stage 5.

## First catalog results (8 standard rooms, 2 threats, 16 noisy executions each)

Reproduce: `python -m uv run killhouse-tactics` (~10 min, one core) -> `out/tactics.json`.

| room | crisscross | buttonhook | comb. cross | comb. hook | two-man | limited | pie+cross | deliberate |
|---|---|---|---|---|---|---|---|---|
| S-center | 0.676 | 0.708 | 0.831 | 0.777 | 0.676 | 0.666 | **0.484** | 0.493 |
| S-corner | 0.656 | 0.802 | 0.667 | 0.802 | 0.656 | 0.778 | 0.517 | **0.515** |
| M-center | 0.609 | 0.696 | 0.773 | 0.777 | 0.680 | 0.713 | **0.480** | 0.481 |
| M-corner | 0.601 | 0.770 | 0.644 | 0.801 | 0.702 | 0.793 | **0.507** | 0.513 |
| L-center | 0.638 | 0.681 | 0.803 | 0.779 | 0.714 | 0.682 | **0.500** | 0.526 |
| L-corner | 0.545 | 0.790 | 0.547 | 0.780 | 0.647 | 0.803 | **0.472** | 0.477 |
| M-center-box | 0.596 | 0.678 | 0.731 | 0.733 | 0.651 | 0.693 | **0.488** | 0.495 (not cleared) |
| L-corner-box | 0.675 | 0.816 | 0.693 | 0.840 | 0.753 | 0.748 | **0.610** | 0.633 |

Values are `risk_multi`; time to clear is 1.0-2.1 s for dynamic entries and 4.1-5.8 s for
pie / deliberate entries in empty rooms.

**Observations (hypotheses for the review, not recommendations):**

1. **Slow entries have the lowest risk, at 2.5-4 s extra time.** Pie + crisscross is best in 7
   of 8 rooms; deliberate entry is almost identical but slower still.
2. **Among dynamic entries, crisscross is best.** With a single-side stack, cross-first is close
   to crisscross in corner-fed rooms (0.547 vs 0.545 in L-corner) but clearly worse in
   centre-fed rooms. Hook-first is the weakest dynamic variant everywhere.
3. **Crossing techniques are timing-sensitive.** Under execution noise the risk barely moves
   (crisscross M-center: nominal 0.609, noisy mean 0.58), but only 25-31 % of noisy crisscross
   executions in M/L rooms stay free of body contact. The two operators meet in the doorway
   when timing slips. Limited penetration stays valid in 94 %, the combination variants in
   50-81 %. "Robust to risk, fragile to coordination" is a candidate result for stage 5.
4. **Diminishing returns of team size:** from 2 to 3 operators, R2 drops clearly (crisscross
   M-center 0.680 -> 0.617, L-corner 0.656 -> 0.548); from 3 to 4 only slightly (0.609 / 0.545).
5. **The deliberate entry does not clear M-center-box:** with the slow timing, the dead-space
   step runs out of the 12 s horizon.
