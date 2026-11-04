# Review R4 (preregistration before the freeze): response

**Type:** AI-assisted methodological review (ChatGPT) of PREREG_E1_draft.md, REPORT_G1_rehearsal.md,
`analysis.py` and `bench.py`, static reading, no runs. Not an instructor review.

**Verdict:** freeze after changes. All blockers are accepted, and all of them are implemented.

| point | review | response |
|---|---|---|
| Test family | H3 and H4 have no executable plan, yet the code already reports `supported` under a provisional Holm step | E1 is H1 and H2 only, H3 and H4 become separate studies, `--h4-p` removed |
| Estimand | the gap measures a fixed search procedure incl. selection, not a global optimality gap; a ratio of estimates can be biased, and "lower bound" is not justified | wording replaced, negative values kept, rule for a zero denominator, unrounded values stored and used. The review was also right in practice: gaps were computed from risks rounded to 4 places |
| 32 scenarios | no precision argument | target fixed and committed first (78a88e6), then measured; 32 fails, 128 is used for evaluation (below) |
| H2 population, ties | a joint validity condition selects a subpopulation; share and test used the same denominator | H2 is limited to rooms where both are valid, the sign test excludes ties, the 70 % share uses all such rooms, invalid and tie counts are output |
| Time floor | the fastest archive point proves no structural limit | claim removed, category is now "no improvement found", search failure not excluded; validity is not a safety assessment |
| Expert validation | no SME available | replaced by a documented method and source check; "only relative results are meaningful" removed |
| H1 reading, failure rules (should) | not causal; rank deficiency, missing door class and unbounded resampling; percentile p-value unchecked | wording added, width ranges reported, not-estimable rule with a bounded loop (the endless loop was real), null calibration measured (below) |
| Proxy, `all([])` (should) | the 78 % proxy is not comparable; rooms without valid techniques count as stable | proxy removed from code and documents, 5 points kept as a convention; `rooms_all_stable` corrected from 13/40 to 12/39 |

## Pre-freeze measurements

Rules were committed before measuring (PREREG §8). Development rooms `generated_rooms(1, 40)`,
16 independent samples of 32 scenarios, `killhouse-prefreeze`. Evaluated were the techniques and
a stand-in for the selected plan: the rehearsal stored fronts, not selected plans, so 13 of 135
pairs had no eligible plan and are left out.

| scenarios | SE of gap, median pair | SE of gap, 90th percentile | SE of paired risk difference, median room | target met |
|---|---|---|---|---|
| target | <= 2 points | <= 3 points | <= 0.01 | |
| 32 | 2.9 | 4.8 | 0.018 | no |
| 64 | 2.05 | 3.4 | 0.013 | no |
| 128 | 1.4 | 2.4 | 0.009 | **yes** |
| 256 | 1.0 | 1.7 | 0.006 | yes |

The standard errors for larger counts are scaled from the 32-scenario spread. The ratio bias at 32
scenarios is small (-0.04 points on average). Plans look better on planning scenarios than on
fresh ones by 0.024 risk on average (0.061 at the 90th percentile); this optimism is why the
evaluation stays separate. The search keeps its 32 planning scenarios, as part of the fixed
procedure.

H1 test under a true effect of 0 (rehearsal design, 33 rooms, 1000 simulations, 2000 resamples):
5.3 % rejections at nominal 0.05 and 2.5 % at 0.025. The limit was 6 %, so the bootstrap p-value
stays and the permutation fallback is not used.
