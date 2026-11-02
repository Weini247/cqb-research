# Preregistration draft: E1 (NOT FROZEN)

Status: **draft**. It will be frozen (git tag + upload to a registry such as OSF) only after the
SME review ([SME_REVIEW.md](SME_REVIEW.md)) has been incorporated. Until then, everything below
may change. Changes are logged in the change log at the end.

## 1. Research question

How close are established room-entry techniques, encoded as stylized playbooks, to the best
strategies a black-box optimizer finds in the same plan space? And which room features decide
the size of the gap?

## 2. Model (frozen at tag `e1-prereg`)

- Code: this repository at the tag. Model constants in `killhouse/entry.py` (`DT`, `HORIZON`,
  `DEFAULT_CFG`), the team in `killhouse/team.py`, playbooks in `killhouse/doctrine.py` after
  the SME revision.
- Primary outcome: `risk_multi`, the probability that the team is hit with `n_threats = 2`
  hidden threats at random positions (32 fixed scenarios per room, common random numbers),
  one target per operator.
- Secondary outcomes: `risk` (single threat), `t_clear`, `fratricide`, `exposure`.
- Validity: collision and wall < 0.02, room cleared (<= 0.5 % unseen threat positions within 12 s).

## 3. Geometries

- Development (used for E0, the E1 draft and this pilot, *not* for confirmation): the 8
  standard rooms and `generated_rooms(seed=0..9)`.
- Confirmatory: `generated_rooms(seed=2026, n=40)`, not evaluated before the freeze. The SHA-256 of the
  room list (`rooms_digest(generated_rooms(2026, 40))`) is recorded in the registration
  (current value: `90a6edacd9aee951cb12a38e613c39a41095014147f7ae8b87a369daa75a4315`).

## 4. Procedure

For each confirmatory room: evaluate the four playbooks; run CEM (30 iterations x 32 samples x
4 weights, seeded with the playbooks) with optimizer seeds 0, 1, 2; build the archive per
seed. Gap per technique and room = relative reduction of `risk_multi` at equal-or-better
`t_clear` and fratricide (`gap_risk`). The reported gap is the median over the 3 seeds.

## 5. Hypotheses and decision rules

| | hypothesis | test | supported if |
|---|---|---|---|
| H1 | The crisscross gap is larger in corner-fed rooms (door centre <= 1.6 m from a side wall) than in centre-fed rooms. | difference of median gaps, bootstrap 95 % CI over rooms (10 000 resamples) | CI excludes 0 |
| H2 | Crisscross has lower `risk_multi` than buttonhook. | sign test over valid rooms, one-sided | p < 0.05 and >= 70 % of rooms |
| H3 | The ranking of the four playbooks is robust to the model axes in `sensitivity.py`. | mean Kendall tau per variant vs. baseline | tau >= 0.8 in >= 80 % of variants |
| H4 | A four-operator entry has lower `risk_multi` than the same plan with #3/#4 outside, in rooms >= 4.5 m wide. | paired sign test over rooms x playbooks | p < 0.05 |

All four hypotheses are reported regardless of outcome. Exploratory analyses (for example,
descriptions of the best found strategies) are labelled as such.

## 6. Exclusions and deviations

- A room counts for a technique only if that technique is valid there. Invalid techniques are
  reported as such, not dropped silently.
- No room is excluded after seeing the results. If the generator yields a degenerate room
  (for example, the door wider than the wall), it is regenerated using the documented rule
  (next seed offset), and this is reported.
- Every deviation from this plan is listed in the final report with its reason.

## 7. Known limitations (stated in advance)

Abstract duel model with freely chosen rates (only relative results are meaningful), no active
adversary movement, no doors that open, constant speeds, idealized perception, single-room
scope, stylized playbooks.

## Change log

- 2026-11-02: first draft after the E1 pilot (multi-threat objective, dead-space step,
  room generator).
