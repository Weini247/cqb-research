# Model parameters and their provenance

Required by review R1 (P1): which values come from data and which are free modelling choices.
Every free parameter is a sensitivity axis (`killhouse/sensitivity.py`) or marked as missing
one.

**Provenance categories:**
- **E** (empirical): taken from a cited study; the transfer to CQB is still unvalidated.
- **G** (geometric reference): a common building dimension.
- **F** (free): a modelling choice without empirical calibration.

| parameter | value | provenance | source / justification | sensitivity |
|---|---|---|---|---|
| walking speed | 1.35-1.55 m/s per operator | E (order of magnitude) | Murtagh et al. 2021, *Sports Med* 51: usual 1.31, medium 1.47 m/s (35 studies, n = 14,015) | missing: speed axis |
| entry speed factor | x1.3 | F | none; an "entry is faster than walking" assumption | missing |
| deliberate speed factor | x0.6 | F | none | missing |
| stack spacing | 0.75 m | F | plausible body spacing | missing |
| spacing in the order of march | 0.6 s (deliberate 1.2 s) | F | none | execution noise sigma 0.25 s |
| door width | 0.9 m (apartments 0.8 / 0.9 m) | G | common interior and entrance door sizes | 0.8 / 1.2 m |
| wall thickness | 0.2 m | G | interior walls 0.1-0.25 m | missing |
| body radius | 0.21-0.30 m | F (from body widths) | shoulder half-width with kit | x0.85 / x1.15 |
| vision / attention cone | 100° (half-angle 50°) | F | Attention is not the physical field of view; useful-field-of-view research shows dependence on contrast, divided attention and eccentricity. Binary cone = strong simplification | 80° / 120° |
| perception dwell | 0.3 s | F | single threshold, deliberately crude | 0.2 / 0.5 / 0.8 s |
| turn rate | 4 rad/s | F | not calibrated | 3 / 6 rad/s |
| threat reaction | 0.3 s | F | Context-dependent (detection + decision + motor). Response times measured in police cadet studies (e.g. Heusler & Sutter 2022) are higher; an armed person raising a weapon is reported in secondary literature at about 0.36 s (primary source not yet identified) | 0.15 / 0.6 / 1.0 s |
| threat hit rate | 1/s | F | only relative results are meaningful | 0.5 / 2 /s |
| engagement rate | 4/s per aiming operator | F | as above | 2 / 8 /s |
| door opening time | 0.8 s | F | no breaching modelled | missing |
| closed interior doors | 60 % | F | scenario choice | --closed |
| identification | +0.4 s in the cone within 6 m (apartments) | F | detection ≠ identification (review R1) | missing |
| threats per scenario | 2 (32 placements) | F | stress case | missing: 1 vs 2 vs 3 |
| small-room rule | < 4.5 m wide -> only #1/#2 enter | F | review R1: no established threshold, creates an artificial discontinuity | 3.5 / 5.5 m |
| corner-fed rule | door centre < 1.6 m from the side wall | F | own adaptation | missing |
| clear criterion | <= 0.5 % threat positions unseen | F | | missing |
| threat clearance from walls | 0.25 m | G | a person needs space | missing |

**Not modelled at all** (stated as limitations): detection vs. identification vs.
misidentification as separate events, stress and pressure effects on performance (see the
meta-analysis by Cooper et al. 2024 cited in review R1, not yet checked), communication,
fatigue, lighting.

**Information model:** All strategies (playbooks, dead-space step, optimizer) know the
floorplan, like a building plan, and none know threat positions. Playbooks and the dead-space
step use only geometry and the single-threat risk, which is an exact expectation over the
uniform prior. The optimizer tunes on planning scenarios (`scenario_salt=0`), and all
reported numbers use held-out scenarios (`EVAL_CFG`, `scenario_salt=1`). The test
`test_information_model_plans_never_see_sampled_threats` enforces this.
