# Preregistration: E1 (FROZEN)

Status: **frozen on 2026-11-07 at git tag `e1-prereg`**, after the documented method and source
check (reviews R1-R4, [TACTICS.md](TACTICS.md)). No instructor or other subject-matter expert has
reviewed it. The file keeps its old name so that links stay valid. From the tag on, the plan below
does not change; every deviation is reported in the study report with its reason (§6).

## 0. Scope and validity limits

This study examines coordinated multi-agent search under geometric constraints and partial
observability. The movement models are algorithmic abstractions; their correspondence to real
tactical procedures is neither shown nor assumed, and technique names denote stylized models.
Optimization results hold only within the defined simulation environment, constraints and
objectives. No superiority of real police or military procedures is inferred from them.
Transfer to human teams needs separate empirical calibration and independent expert
validation. All changes to parameters, hypotheses and conditions are versioned before the
registration is frozen. Checked are the implementation, internal consistency and individually
documented source references. Practical validity and real-world rankings are not claimed.

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
  `DEFAULT_CFG`), the team in `killhouse/team.py`, playbooks in `killhouse/doctrine.py`.
- Primary outcome: `risk_multi`, the probability that the team is hit with `n_threats = 2`
  hidden threats at random positions (fixed scenarios per room, common random numbers), one
  target per operator. 32 planning scenarios, 128 evaluation scenarios (`E1_CFG`, see §8).
- Secondary outcomes: `risk` (single threat), `t_clear`, `fratricide`, `exposure`.
- Validity: collision and wall < 0.02, room cleared (<= 0.5 % unseen threat positions within 12 s).
  Validity means geometric and temporal admissibility, not a safety assessment.

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

**Estimand:** the gap measures the performance of this fixed search procedure including its
selection step, not a global optimality gap. The relative gap is a Monte-Carlo estimate for the
fixed search budget, not a guaranteed lower bound. Negative values are kept. If the held-out risk
of a technique is 0, its relative gap is undefined: the pair stays counted, is reported, and is
left out of the gap statistics. Calculations and tests use unrounded values.

Expected compute: 5-7 h for 40 rooms (measured in the dress rehearsal).

**Technique families:** "technique" means one of the four families crisscross, buttonhook,
pie + crisscross and limited penetration, as produced by `doctrines()`. In rooms with obstacles
a family includes the dead-space step whenever its plan would otherwise leave threat positions
unseen (name suffix `+dead-space`). Comparisons between techniques are made per family, whether
or not the step was added, and the number of rooms with the step is reported.

**Reliability (judged across runs, not within a run):** a room-technique pair is
**method-stable** when the pooled gaps of the two optimizer families, each computed on its own
five archives, differ by at most 5 points (`METHOD_TOL`). The limit is a descriptive convention
without a reference value. This measure **never filters**: all valid pairs stay in every
analysis. Per pair, the per-run gaps and the number of runs that leave the seeded playbook are
reported as well. H1 is repeated for each optimizer family alone; a result that holds for one
family only is reported as such.

**No improvement found:** pairs where no run leaves the playbook and the playbook's `t_clear`
equals the fastest time in the pooled front stay in the analyses and are also counted separately.
Under the fixed search budget no improvement above the fixed threshold was found; search failure
is not excluded.

**Fratricide:** every gap and every ranking is reported together with the `fratricide` of the
technique. Validity does not depend on it (§2).

## 5. Hypotheses and decision rules

| | hypothesis | test | supported if |
|---|---|---|---|
| H1 | Within valid rooms, at equal room width, the crisscross gap is larger in corner-fed rooms (door centre <= 1.6 m from a side wall) than in centre-fed rooms. | least-squares regression gap ~ corner-fed + room width over valid rooms, bootstrap over rooms (10 000 resamples); p = share of resamples with a coefficient <= 0 (one-sided); the 95 % CI is reported | Holm-adjusted p < 0.05 |
| H2 | In rooms where both are valid, crisscross has lower `risk_multi` than buttonhook. | sign test, one-sided, ties excluded | Holm-adjusted p < 0.05 and wins in >= 70 % of all rooms where both are valid (ties in the denominator) |

**Analysis code:** §4 and §5 are implemented in `killhouse/analysis.py`
(`killhouse-analyze <result files> --generated 2026 40`), which also checks that the files hold
exactly the confirmatory rooms.

**Multiple testing:** E1 consists of H1 and H2 only. Both form the Holm family at alpha = 0.05.
The former H3 (robustness over model axes) and H4 (four vs. two operators) are preregistered
separately, as studies with their own data collection and analysis plan, and are never added to
this family. Rooms are the independent unit in every test, and seeds are combined within a room
first (pooled archive, see §4).

**H1 reading and failure rules:** H1 tests a linearly width-adjusted association within valid
rooms, not a causal door effect. The width range of both door classes is reported. If one door
class is missing, the design has rank < 3, or the bootstrap cannot draw enough usable resamples
(limit 20 x 10 000), H1 counts as not estimable and not supported. The specification of H1 was
chosen on the rehearsal rooms, so those rooms are development data; only E1 can confirm it.

Secondary for H1, without a decision rule: the unadjusted difference of median gaps and the
relative definition (door centre in the outer third of the wall). H2 is reported separately for
corner-fed and centre-fed rooms, also without a decision rule.

Both hypotheses are reported regardless of outcome. Exploratory analyses (for example,
descriptions of the best found strategies) are labelled as such.

## 6. Exclusions and deviations

- A room counts for a technique only if that technique is valid there. Invalid techniques are
  reported as such, not dropped silently. H2 therefore speaks only about rooms where both
  techniques are valid. The numbers of invalid rooms and of ties are reported separately.
- No room is excluded after seeing the results. If the generator yields a degenerate room
  (for example, the door wider than the wall), it is regenerated using the documented rule
  (next seed offset), and this is reported.
- Every deviation from this plan is listed in the final report with its reason.

## 7. Known limitations (stated in advance)

Abstract duel model with freely chosen rates (relative results do not gain external validity
either, because the model is not calibrated), no active
adversary movement, no doors that open, constant speeds, idealized perception, single-room
scope, stylized playbooks.

## 8. Pre-freeze checks (rules fixed before measuring)

Both checks run on development rooms only (`killhouse/prefreeze.py`), and their rules were
committed before the measurement.

- **Evaluation scenarios:** independent samples of 32 scenarios give the Monte-Carlo standard error
  of held-out estimates. The number of evaluation scenarios is the smallest of 32, 64, 128, 256
  and 512 with a standard error of the relative gap of at most 2 points in the median pair and
  3 points at the 90th percentile, and of a paired risk difference between two techniques of
  at most 0.01 in the median room. If none qualifies, 512 is used and the shortfall is reported.
  Planning scenarios are part of the search procedure and are judged separately. The count is
  never changed on the basis of confirmatory results.
- **H1 test calibration:** with a true door effect of 0, on the rehearsal room design, the test must
  reject at nominal one-sided 0.05 in at most 6 % of simulations. If it does not, H1 uses a
  residual permutation test (Freedman-Lane) instead of the bootstrap p-value.

**Results (REVIEW_R4.md):** 32 scenarios miss the target (2.9 and 4.8 points, 0.018), 64 as well,
128 meets it (1.4 and 2.4 points, 0.009), so E1 evaluates on 128. The H1 test rejects in 5.3 % of
simulations, so the bootstrap p-value stays.

## Noted at the freeze

- The expected number of valid rooms is low for technique comparisons: the crossing techniques
  were invalid in 7 of 40 rehearsal rooms, mostly through collisions.

## Change log

- 2026-11-07: frozen at tag `e1-prereg`. The confirmatory rooms had not been evaluated.

- 2026-11-04: review R4 (REVIEW_R4.md): E1 reduced to H1 and H2, H3 and H4 become separate
  studies; estimand stated (search procedure incl. selection, no guaranteed lower bound); zero
  denominator and unrounded values fixed; H2 limited to rooms where both are valid, ties defined;
  "time floor" replaced by "no improvement found"; expert validation replaced by a method and
  source check; failure rules for H1; interchangeability proxy removed; pre-freeze checks added
  and run: 128 evaluation scenarios, H1 bootstrap p-value kept.

- 2026-11-04: analysis script `killhouse/analysis.py` added. Writing it showed that the H1 rule
  ("CI excludes 0") could not enter the Holm step, so H1 now has a bootstrap p-value and H1, H2
  and H4 all decide on Holm-adjusted p.
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
