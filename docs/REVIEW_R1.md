# Review R1: response and changes

**Type of review:** methodological review based on public research and modelling standards
(received 2026-11-02). The reviewer states explicitly that they cannot claim instructor or
operational experience. So this is **not an SME review**: no technique counts as confirmed,
and the instructor review ([SME_REVIEW.md](SME_REVIEW.md)) remains open. The reviewer only
saw the review packet, not the code.

**Verdict of the reviewer:** "revise". Acceptable as an abstract research model, not as a
validated CQB tactics model. Ready for preregistration only after the P0 issues are fixed and
the hypotheses are narrowed.

## Source check (spot checks)

| claim in the review | check |
|---|---|
| Murtagh et al. 2021: walking speed 1.31 (usual) / 1.47 (medium) m/s, n = 14,015 | confirmed (*Sports Med* 51(1); PMC7806575) |
| police cadets: response times 743-1083 ms | not found; closest match is Heusler & Sutter 2022 (gaze-control training, response time), numbers unconfirmed |
| Cooper et al. 2024, pressure and police performance | not checked |
| VV&A Recommended Practices Guide, ITOP 01-1-002 | not checked; the verification vs. validation distinction is uncontroversial |

## Points and responses

| # | point | priority | response | status |
|---|---|---|---|---|
| 1 | **Information parity:** no strategy may use information that is not observable | P0 | Real leak found: the dead-space step and the optimizer chose plans on the *same* sampled threat placements that were later used for evaluation. Fix: separate planning scenarios (`scenario_salt=0`) from held-out evaluation scenarios (`EVAL_CFG`); the dead-space step now uses only geometry and the exact single-threat expectation. Information model documented: everyone knows the floorplan, nobody knows threat positions. A test enforces it. | ✅ |
| 2 | Technique names imply authenticity | P0 | Names are labelled as stylized, unvalidated movement models in TACTICS.md, the 3D viewer, the report and the prereg; findings are labelled model-internal | ✅ |
| 3 | Document empirical vs. free parameters | P1 | [PARAMETERS.md](PARAMETERS.md) with provenance E / G / F for every parameter | ✅ |
| 4 | 4.5 m two-man threshold is unfounded and creates a discontinuity | P1 | Now a sensitivity axis (3.5 / 5.5 m). It is the most influential axis (tau 0.67 at 3.5 m), so the concern is justified. It remains a documented free rule. | ✅ examined |
| 5 | Perception too coarse (cone, dwell, reaction) | P1 | Extended sensitivity: dwell 0.8 s, threat reaction 1.0 s. A finer perception model (eccentricity-dependent detection probability, detection ≠ identification) remains open. | partly |
| 6 | Separate training and test data | P1 | Rooms: already held out in the prereg (seed 2026). Threat scenarios: now separated too (point 1). | ✅ |
| 7 | Quantify uncertainty | P1 | Prereg already requires bootstrap CIs and 3 seeds; execution-noise distributions in `tactics.robust_eval` | ✅ planned |
| 8 | Metrics: detection errors, misidentification, variance | — | Variance: noise and seed spread. Misidentification is not modelled (no non-threats in the scene); listed as a limitation | open |
| 9 | The 3D viewer suggests validity | — | Notice in viewer and report | ✅ |
| 10 | Corner-fed rule is self-defined | — | Marked as "adapted"; status unchanged | ✅ documented |

## Effect of the fixes (rerun with the same budget, seed 0)

**Held-out threat scenarios** shrink part of the earlier optimality gaps:

| room | crisscross gap: before -> held-out | buttonhook | limited penetration |
|---|---|---|---|
| M-center | 11 % -> 0 % | 19 % -> 0 % | 21 % -> 0 % |
| L-center | 0 % -> 0 % | 5 % -> 0 % | 5 % -> 0 % |
| M-center-box | 16 % -> 10 % | 32 % -> 28 % | 28 % -> 16 % |
| S-/M-/L-corner | 14-39 % -> 14-39 % (stable) | 48-52 % (stable) | 47-53 % (stable) |

So in centre-fed rooms the earlier advantage of the optimizer was largely overfitting to the
sampled threat placements. In corner-fed and small rooms the gaps survive the held-out
evaluation. **The review led to a substantive correction of a result**, not just a change in
wording.

**Extended sensitivity** (20 variants incl. dwell 0.8 s, threat reaction 1.0 s, small-room
threshold; held-out scenarios):

| claim (lower `risk_multi`) | holds in |
|---|---:|
| crisscross < buttonhook | 164 / 165 |
| pie+crisscross < crisscross | 164 / 164 |
| crisscross < limited penetration | 150 / 168 |

## Still open before freezing the preregistration

- A real instructor review (SME_REVIEW.md)
- A finer perception model, or at least a probabilistic detection cone, as a sensitivity variant
- The full confirmatory budget only after the fast simulator (stage 4)
