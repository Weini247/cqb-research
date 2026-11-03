# Claims register

Review R3 (M1): every main claim has a data reference or is labelled a hypothesis. Status:
**supported (exploratory)** = backed by result files from the development rooms;
**hypothesis** = plausible but not shown on a common basis; **retracted** = withdrawn.
Nothing here is confirmatory (see RUNLOG.md).

| # | claim | status | evidence (file, commit) | open check |
|---|---|---|---|---|
| C1 | Crisscross < buttonhook in pairwise risk comparisons across 20 one-at-a-time variants (164/165) | supported (exploratory) | `out/sensitivity-r1.json`, 4cb99f3 | interactions between axes; common denominator |
| C2 | Pie + crisscross < crisscross (164/164) at 2.5-3 s more time | supported (exploratory) | same | as C1 |
| C3 | The optimizer finds lower-risk strategies than every stylized technique (1-54 %) | supported, **low reliability** | `out/bench-r3`, `out/bench-r3-s1`, f4f44ee | seeds differ by up to 20 points; see C3a/C3b |
| C3a | Corner-fed M room: gaps are saturated and seed-stable from 30x64 on (22-53 %, spread 1-4 points) | supported (exploratory) | `out/saturation.json`, REPORT_M2, b1ca549 | held-out rooms |
| C3b | Centre-fed rooms: outcomes are bimodal across seeds (0 % or 15-30 %) even at 60x128; a per-seed gap of 0 does not show the technique is optimal | supported (exploratory) | same + `out/pooled-pilot` (pooled 5 seeds: 15-30 %, 1-2/5 seeds at best) | second optimizer family |
| C12 | Visibility code and CEM reproduce known reference answers (comb gallery k = 2-4; L-corridor watchman 4.51 m in 20/20 seeds after the random-immigrant fix) | supported | `tests/test_reference.py`, REPORT_M2, ee64dc1 | more reference cases (multi-agent) |
| C4 | "Gaps only for corner-fed / small rooms; 0 % for centre-fed" | **retracted** | an artefact of too small a budget (bench-r1 vs. bench-r3) | — |
| C5 | In apartments, limited penetration + dead-space step has the lowest risk | hypothesis | `out/apartment`, 3 apartments, d2214df | more apartments, completion-adjusted comparison, cause analysis |
| C6 | Mixing techniques lowers the worst-case single-threat risk by 26-29 % (centre-fed) vs. 4-5 % (corner-fed) | supported for the defined game | `out/adversary.json`, fe35d94 | exact LP value, multi-threat game |
| C7 | Crossing techniques lose validity under execution noise (21-38 % valid at 1x, M/L rooms) | supported (exploratory) | `out/robustness.json`, fe35d94 | breakdown by cause, correlated noise, CIs |
| C8 | Trade-off between risk, predictability and robustness | hypothesis | C6 + C7 on different bases | common instances and assumptions |
| C9 | A four-operator entry lowers `risk_multi` vs. two in M/L rooms | supported (exploratory) | `tactics.json` team-size rows, deb8e15 | prereg H4 on held-out rooms |
| C10 | Door watch lowers single-threat risk in apartments (12/12 pairs) | supported (exploratory) | ad-hoc run, see TACTICS.md | result file not archived |
| C11 | Closed doors lower risk and add time (APT5: 0.965 -> 0.913, 46.8 -> 60.1 s) | supported (exploratory) | ad-hoc run, d5ce0ab | more apartments, archived file |
