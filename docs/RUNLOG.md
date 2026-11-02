# Run and knowledge log

Required by review R2: which results were known when the model was changed. **All results so
far are exploratory.** They shaped the model, so they cannot count as confirmation. The
confirmatory rooms (`generated_rooms(2026, 40)`, SHA-256 in the prereg) have never been
evaluated; only their hash was computed.

| commit | model state | results known at that point | changes it caused |
|---|---|---|---|
| b8484b6 / 43bb13d / 8dfae41 | E0: exposure objective, dwell, wall thickness | E0 gaps; #3/#4 stay outside | duel threat model |
| 9f72ea7 / 1a83ecf / 6c6c440 | E1 draft: single-threat duel | E1-draft gaps, sensitivity | multiple threats, dead space |
| 56f4e36 / bb21772 | multi-threat objective, 52-dim plan space | pilot gaps (later shown to be partly overfitting) | budget rule in prereg |
| 9c7163a | tactic catalog, execution noise | catalog table, timing sensitivity | — |
| 1166aaf / 7c10397 | review R1: planning vs. held-out scenarios | corrected pilot gaps, extended sensitivity | prereg scope section |
| 6c0f5bd | GPU batch evaluation (same model) | speed only | — |
| 3a7dfbd | apartments: closed doors, identification (`id_time` 0.4) | first door-state comparison | — |
| ed84a34 | adversary, robustness | stage-5 findings | — |
| (this commit) | review R2: source status, valid-only stats, prereg tests | — | — |

**Rule from now on:** every report names its commit and its configuration (`config` in
`results.json`). Changes to the model after the prereg freeze go only into a new, separately
labelled exploratory analysis.
