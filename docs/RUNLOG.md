# Run and knowledge log

Required by review R2: which results were known when the model was changed. **All results so
far are exploratory.** They shaped the model, so they cannot count as confirmation. The
confirmatory rooms (`generated_rooms(2026, 40)`, SHA-256 in the prereg) have never been
evaluated; only their hash was computed.

| commit | model state | results known at that point | changes it caused |
|---|---|---|---|
| 8ba1e45 / af816dd / cfff9ca | E0: exposure objective, dwell, wall thickness | E0 gaps; #3/#4 stay outside | duel threat model |
| 831ac9a / 8423fc9 / 74c1851 | E1 draft: single-threat duel | E1-draft gaps, sensitivity | multiple threats, dead space |
| 6027322 / abf6e3a | multi-threat objective, 52-dim plan space | pilot gaps (later shown to be partly overfitting) | budget rule in prereg |
| deb8e15 | tactic catalog, execution noise | catalog table, timing sensitivity | — |
| 4cb99f3 / 12d4281 | review R1: planning vs. held-out scenarios | corrected pilot gaps, extended sensitivity | prereg scope section |
| d9361b0 | GPU batch evaluation (same model) | speed only | — |
| d5ce0ab | apartments: closed doors, identification (`id_time` 0.4) | first door-state comparison | — |
| fe35d94 | adversary, robustness | stage-5 findings | — |
| (R2 commit) | review R2: source status, valid-only stats, prereg tests | — | — |
| ee64dc1 / b1ca549 | M2: reference cases, CEM with random immigrants | saturation study on M-center, M-corner, L-center (5 seeds x 4 budgets) | prereg budget 60x64x4, pooled archives, saturation across seeds |
| b5072b8 / (M2c commit) | pooled estimator, CMA-ES | pooled CEM and CMA-ES on M-center, M-corner, L-center (5 seeds each) | second optimizer family in the prereg, method agreement within 5 points replaces the 2 % seed rule |
| 9f26cab | same model, full E1 protocol | dress rehearsal on `generated_rooms(1, 40)`, in two parts after an interruption (control room G1-29 identical) | prereg: H1 adjusted for width, technique families, method stability descriptive, time floor, fratricide reporting |

**Rule from now on:** every report names its commit and its configuration (`config` in
`results.json`). Changes to the model after the prereg freeze go only into a new, separately
labelled exploratory analysis.
