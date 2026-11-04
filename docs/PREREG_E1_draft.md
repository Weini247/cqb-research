# Preregistration draft: E1 (NOT FROZEN)

Status: **draft**. It will be frozen (git tag + upload to a registry such as OSF) only after the
SME review ([SME_REVIEW.md](SME_REVIEW.md)) has been incorporated. Until then, everything below
may change. Changes are logged in the change log at the end.

## 0. Scope and validity limits

This study examines coordinated multi-agent search under geometric constraints and partial
observability. The movement models are algorithmic abstractions; their correspondence to real
tactical procedures is neither shown nor assumed, and technique names denote stylized models.
Optimization results hold only within the defined simulation environment, constraints and
objectives. No superiority of real police or military procedures is inferred from them.
Transfer to human teams needs separate empirical calibration and independent expert
validation. All changes to parameters, hypotheses and conditions are versioned before the
registration is frozen.

**Information model:** All strategies know the floorplan, no strategy knows threat positions
(see [PARAMETERS.md](PARAMETERS.md)). Optimization uses planning scenarios; every confirmatory
number is computed on held-out threat scenarios *and* held-out rooms.

## 1. Research question

**Main question:** How strongly do comparisons of coordinated multi-agent search strategies depend on model assumptions, information access and the evaluation protocol? E1 examines it on the case study below.


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
  standard rooms, `generated_rooms(seed=0..9)` and the dress rehearsal rooms
  `generated_rooms(1, 40)` (REPORT_G1_rehearsal.md).
- Confirmatory: `generated_rooms(seed=2026, n=40)`, not evaluated before the freeze. The SHA-256 of the
  room list (`rooms_digest(generated_rooms(2026, 40))`) is recorded in the registration
  (current value: `90a6edacd9aee951cb12a38e613c39a41095014147f7ae8b87a369daa75a4315`).

## 4. Procedure

For each confirmatory room: evaluate the four playbooks; run **two optimizer families**, CEM
(`optimize.cem_minimize`, 20 % random immigrants) and CMA-ES (`optimize.cmaes_minimize`,
standard parameters), each with **60 iterations x 64 samples x 4 weights**, seeded with the
playbooks, for optimizer seeds 0-4 (budget and second family from REPORT_M2.md). **Pool the
archives of all 10 runs** per room (`killhouse-bench --optimizer cem cmaes --seeds 5`). **Scope of E1: single rooms only**
(apartments are a separate later study). Gap per technique and room = relative reduction of
`risk_multi` at equal-or-better `t_clear` and fratricide (`gap_risk`), computed on held-out
threat scenarios for **one candidate per technique that was selected on planning scenarios
from the pooled archive** (lowest planning risk at equal-or-better time and fratricide). The
optimistic best-of-front value is reported only as secondary. Tests use rooms as the unit.
Expected compute: 5-7 h for 40 rooms (measured in the dress rehearsal).

**Technique families:** "technique" means one of the four families crisscross, buttonhook,
pie + crisscross and limited penetration, as produced by `doctrines()`. In rooms with obstacles
a family includes the dead-space step whenever its plan would otherwise leave threat positions
unseen (name suffix `+dead-space`). Comparisons between techniques are made per family, whether
or not the step was added, and the number of rooms with the step is reported.

**Reliability (judged across runs, not within a run):** a room-technique pair is
**method-stable** when the pooled gaps of the two optimizer families, each computed on its own
five archives, differ by at most 5 points (`METHOD_TOL`). This measure is **descriptive and never
a filter**: all valid pairs stay in every analysis, and all gaps are lower bounds. Its share is
reported next to the rehearsal values (57 % observed, about 78 % for interchangeable methods by
the proxy in REPORT_G1_rehearsal.md). Per pair, the per-run gaps and the number of runs that
leave the seeded playbook are reported as well. H1 is repeated for each optimizer family alone;
a result that holds for one family only is reported as such.

**Time floor:** a pair where no run leaves the playbook and the playbook's `t_clear` equals the
fastest time in the pooled front has no room under the "equal or better time" rule. These pairs
stay in the analyses and are also counted and reported as a separate category, not as search
failures.

**Fratricide:** every gap and every ranking is reported together with the `fratricide` of the
technique. Validity does not depend on it (§2).

## 5. Hypotheses and decision rules

| | hypothesis | test | supported if |
|---|---|---|---|
| H1 | At equal room width, the crisscross gap is larger in corner-fed rooms (door centre <= 1.6 m from a side wall) than in centre-fed rooms. | least-squares regression gap ~ corner-fed + room width over valid rooms, bootstrap 95 % CI of the corner-fed coefficient over rooms (10 000 resamples) | CI lies above 0 |
| H2 | Crisscross has lower `risk_multi` than buttonhook. | sign test over valid rooms, one-sided | p < 0.05 and >= 70 % of rooms |
| H3 | The ranking of the four playbooks is robust to the model axes in `sensitivity.py`. | mean Kendall tau per variant vs. baseline | tau >= 0.8 in >= 80 % of variants |
| H4 | A four-operator entry has lower `risk_multi` than the same plan with #3/#4 outside, in rooms >= 4.5 m wide. | per room, the mean difference over playbooks; sign test over **rooms** (rooms are the independent unit, not room x playbook) | p < 0.05 |

**Multiple testing:** H1, H2 and H4 form one family and are Holm-corrected at alpha = 0.05.
H3 is a descriptive robustness criterion without a p-value. Rooms are the independent unit
in every test, and seeds are combined within a room first (pooled archive, see §4).

Secondary for H1, without a decision rule: the unadjusted difference of median gaps and the
relative definition (door centre in the outer third of the wall). H2 is reported separately for
corner-fed and centre-fed rooms, also without a decision rule.

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

## Open before the freeze

- External review of this draft. The header names an SME review; no real instructor is available
  so far, so it has to be decided what replaces it.
- A versioned analysis script that computes §4 and §5 from the result files.
- H3 and H4 need data that `killhouse-bench` does not produce: H3 a sensitivity run, H4 a
  comparison with #3/#4 outside. Their room set, budget and script have to be fixed.
- The expected number of valid rooms is low for technique comparisons: the crossing techniques
  were invalid in 7 of 40 rehearsal rooms, mostly through collisions.

## Change log

- 2026-11-04: dress rehearsal on `generated_rooms(1, 40)` (REPORT_G1_rehearsal.md): H1 now
  adjusted for room width, because the gap depends on width as strongly as on door distance;
  technique families defined; method stability declared descriptive; time-floor category and
  fratricide reporting added; expected compute corrected to 5-7 h. These choices were made after
  seeing the rehearsal rooms, not the confirmatory rooms.

- 2026-11-02: method check M2 (REPORT_M2.md): CEM with random immigrants; budget fixed at
  60x64x4; seeds combined by pooling archives instead of the median; saturation judged across
  seeds. Pooled estimator implemented (`bench.py --seeds 5`) and piloted on two development
  rooms: no centre-fed technique saturated (1-2 of 5 seeds at the pooled best).
- 2026-11-03: cross-check M2c (REPORT_M2.md): second optimizer family (CMA-ES) added and pooled;
  the 2 % seed rule replaced by method agreement within 5 points; H1 repeated per family.

- 2026-11-02: first draft after the E1 pilot (multi-threat objective, dead-space step,
  room generator).
- 2026-11-02: pilot (REPORT_E1_pilot.md) showed an under-budgeted search in large rooms; the
  confirmatory budget is now tied to a saturation check.
- 2026-11-02: review R3 (REVIEW_R3.md): E1 limited to single rooms, single pre-selected
  candidate per technique, 5 optimizer seeds, consistent aggregation (median over seeds).
- 2026-11-02: review R2 (REVIEW_R2.md): H4 on room level, Holm correction, explicit test family.
- 2026-11-02: methodological review R1 (REVIEW_R1.md): added scope/validity section,
  information model, separation of planning and held-out threat scenarios, parameter
  provenance (PARAMETERS.md), new sensitivity axes (dwell 0.8 s, threat reaction 1.0 s,
  small-room threshold). H3 now covers the extended grid.
