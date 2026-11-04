# Big picture (as of 2026-11-02)

## North star (aspirational yardstick)

**An open reference platform for coordinated search under limited visibility.** It makes
spatial planning comparable, explains why methods fail, and tests whether results transfer
to new environments and other model assumptions.

**Guiding question:** Which properties make coordinated search methods under limited
visibility reliable, and how can that reliability be shown independently of individual
environments and modelling choices?

**First concrete sub-question (study 1):** How strongly do rankings of search methods
depend on the optimization budget, information access and evaluation protocol?

**Yardsticks (deliberately ambitious):** an external person reproduces the main results from
a release · new planners plug in through a documented interface · the benchmark exposes
systematic failures of strong methods · a statement holds on unseen floorplans and under
changed assumptions · *far goal:* another research group uses the platform.

CQB remains the defining case study. Transfer to rescue robotics, inspection or human teams
would be separate research with its own tasks and evidence.

## Goal

**Main question (since review R3):** How strongly do comparisons of coordinated multi-agent search strategies depend on model assumptions, information access and the evaluation protocol?

**Case study:** published room-entry techniques vs. the best strategies found in the same
model. Discovering new techniques is deferred until after the first study (dual use).

**Framing:** coordinated multi-agent search under visibility constraints; CQB is the case
study. Transfer to search-and-rescue, fire service and robot teams.

**Purpose:** a serious, reproducible research project. Public GitHub repository as portfolio,
preprint(s), later possibly a thesis.

**Boundaries:**
- abstract duel model, no ballistics or weapon effects
- tactics only at the level of public sources
- findings are model-internal hypotheses, not operational recommendations
- no instructor available, so the target is "source-faithful", not "practitioner-validated"

**Far vision (optional):**
1. a benchmark for spatial reasoning of LLM/VLM planners (stage 7)
2. robot scouts in front of human teams, with a bridge to a separate multi-robot exploration
   project (stage 8)
3. automatic discovery of new tactic families that are robust, unpredictable and simple
   (stage 9)

## Status

| stage | content | status |
|---|---|---|
| 1 | single room: model, 4 doctrines, CEM optimizer, duel and multi-threat risk, dead space, sensitivity, 2D report, 3D viewer | done (exploratory) |
| 2 / 2b | apartments: generator, door swing, closed doors, pass-through window, identification before engagement, room-by-room clearing, door watch, 3D | v1 |
| 3 | tactic catalog with 8 techniques, sources and status, team sizes 2-4, execution noise | done; no instructor review |
| 4 | GPU batch evaluation (PyTorch), about 25x faster in the optimizer | done; gradients missing |
| 5 | adversary who knows the plan (price of predictability), robustness study | done (exploratory) |
| 6 | confirmatory study on 40 held-out rooms, preprint | prereg draft |
| 7-10 | LLM benchmark, robot scouts, tactic discovery, web lab | open |

## Main findings so far (all exploratory, model-internal)

1. **Pairwise comparisons are stable in one-at-a-time sensitivity (20 variants):**
   crisscross < buttonhook in 164/165 cases, pie + crisscross < crisscross in 164/164,
   crisscross < limited penetration in 150/168. The denominators differ (invalid cases are
   excluded), so this is not a single total ranking, and interactions between axes are untested.
2. **Optimizer gaps are low-reliability (revised after R3).** With one candidate selected
   per doctrine and scored on held-out scenarios, gaps are 1-54 % at the full budget, but two
   optimizer seeds differ by up to 20 points (M-center crisscross 20 % vs. 0 %). The earlier
   "0 % for centre-fed doors" came from too small a budget. Gaps are lower bounds on attainable
   improvement in the model, not stable effect sizes. On 40 generated rooms
   (REPORT_G1_rehearsal) the pooled gaps have a median of 29 % (0-56 %), and two optimizer
   families agree within 5 points in 57 % of room-technique pairs. The pattern from three rooms
   in REPORT_M2 (corner-fed stable, centre-fed bimodal) does not generalize.
3. **Apartments may reverse the ranking (low reliability):** limited penetration with the
   dead-space step had the lowest risk in 3 development apartments. In APT1 it did not fully
   clear one room, the comparison population is small, and the hallway explanation is not
   causally identified.
4. **Price of predictability (defined finite game):** the best mixture lowers the
   worst-case single-threat risk by 26-29 % for centre-fed doors and by 4-5 % for corner-fed
   doors. "Mixing is never worse" holds by construction (mixtures include pure techniques);
   the effect size is the finding. The adversary knows the mixture, not the draw, and the 5 %
   grid gives an upper bound on the exact game value.
5. **Risk changes little under execution noise, validity a lot:** crossing techniques stay
   valid in 21-38 % of executions in M/L rooms at 1x noise, the single-side combination in
   62-96 %. "Valid" combines contact, wall and clearance criteria.
6. **Trade-off (hypothesis only):** low risk, unpredictability and robust execution seem to
   pull in different directions; not yet shown on a common data basis.

## Known weaknesses

- Nearly all parameters are free (see PARAMETERS.md).
- Binary perception cone, crude dwell model.
- No misidentification of uninvolved persons yet, no moving threats.
- Results based on 8 development rooms and 1-2 seeds (5 seeds only in the M2 saturation study,
  3 rooms).
- Source page numbers only partly checked. Reviews R1/R2 were AI-assisted, not by instructors.
- Model changes were made after seeing results (RUNLOG.md), so everything is exploratory so far.

## Documents

CONCEPT, ROADMAP, PARAMETERS, TACTICS, RUNLOG, PREREG_E1_draft, REVIEW_R1/R2,
REPORT_E0 / E1_draft / E1_pilot / APARTMENT_v0 / E5.
