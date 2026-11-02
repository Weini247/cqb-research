# Big picture (as of 2026-11-02)

## Goal

**Research question:** How close are published room-entry techniques (as described in public
manuals) to the best strategies found in a simulation? And can robust, learnable, better
techniques be found automatically?

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

1. **Ranking among the stylized techniques is very robust across 20 sensitivity variants.**
   Pie + crisscross < crisscross < buttonhook in 164/165 cases. Limited penetration is
   mostly worse.
2. **Optimizer gaps exist mainly for corner-fed doors and small rooms** (14-53 %). For
   centre-fed doors they shrank to 0 % on held-out threat scenarios; R1 uncovered this
   overfitting.
3. **Apartments reverse the ranking:** limited penetration with the dead-space step is best
   there. Probable reason: uncleared rooms look into the hallway.
4. **Price of predictability:** mixing techniques lowers the worst-case risk by 26-29 % for
   centre-fed doors, by 4-5 % for corner-fed doors.
5. **Risk is robust, execution is not:** under execution noise only 21-38 % of crossing
   techniques stay free of body contact, against 62-96 % for the single-side combination.
6. **Trade-off:** low risk, unpredictability and robust execution pull in different directions.

## Known weaknesses

- Nearly all parameters are free (see PARAMETERS.md).
- Binary perception cone, crude dwell model.
- No misidentification of uninvolved persons yet, no moving threats.
- Results based on 8 development rooms and 1-2 seeds.
- Source page numbers only partly checked. Reviews R1/R2 were AI-assisted, not by instructors.
- Model changes were made after seeing results (RUNLOG.md), so everything is exploratory so far.

## Documents

CONCEPT, ROADMAP, PARAMETERS, TACTICS, RUNLOG, PREREG_E1_draft, REVIEW_R1/R2,
REPORT_E0 / E1_draft / E1_pilot / APARTMENT_v0 / E5.
