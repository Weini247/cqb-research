# Stage 5: robustness and an adversary who knows the plan (exploratory)

Model-internal findings with stylized techniques (see TACTICS.md), held-out threat scenarios,
8 development rooms, team of 4. Reproduce:

```
python -m uv run python -m killhouse.adversary    # ~1 min  -> out/adversary.json
python -m uv run python -m killhouse.robustness   # ~15 min -> out/robustness.json
```

## A. Price of predictability

`adversary.py` computes P(team hit) for a single threat at every possible position.
- **Random threat:** the mean over positions, i.e. the usual risk.
- **Adversary who knows the technique:** stands at the worst position (worst case).
- **Team draws its technique at random from a mixture:** the adversary can only respond to
  the mixture. The best mixture is the value of a zero-sum game (grid search on the simplex,
  5 % steps).

Techniques: crisscross, buttonhook, combination (cross first), limited penetration.

| room | worst case, best fixed technique | worst case, best mixture | gain | mixture (cc / bh / comb / lim) |
|---|---:|---:|---:|---|
| S-center | 0.585 | 0.435 | 26 % | 0.55 / 0 / 0 / 0.45 |
| M-center | 0.628 | 0.446 | 29 % | 0.45 / 0.2 / 0.05 / 0.3 |
| L-center | 0.626 | 0.446 | 29 % | 0.45 / 0.25 / 0.05 / 0.25 |
| S-corner | 0.344 | 0.330 | 4 % | 0.7 / 0 / 0.3 / 0 |
| M-corner | 0.364 | 0.346 | 5 % | 0.5 / 0 / 0.5 / 0 |
| L-corner | 0.364 | 0.346 | 5 % | 0.5 / 0 / 0.5 / 0 |
| M-center-box | 0.660 | 0.660 | 0 % | limited only |
| L-corner-box | 0.813 | 0.802 | 1 % | 0.4 / 0 / 0 / 0.6 |

**Reading:** In centre-fed rooms every fixed technique leaves a predictable "worst spot"; varying
the technique lowers the worst-case risk by about a quarter. In corner-fed rooms the geometry
nearly dictates the technique, so predictability costs little. With furniture the dead space
dominates.

## B. Robustness to execution noise

Noise levels 0 / 0.5 / 1 / 2 x base (base: start time 0.25 s, positions 0.25 m, gaze
0.15 rad, speed 10 %), 24 executions per cell. Shown: mean `risk_multi` / share of valid
executions (no body contact, no wall contact, room cleared).

| room | crisscross | buttonhook | comb. cross | two-man | limited | pie+cross | deliberate |
|---|---|---|---|---|---|---|---|
| M-center 0 / 1x / 2x | 0.63 / 0.60 / 0.61<br>valid 1.00 / 0.25 / 0.08 | 0.68 / 0.65 / 0.64<br>1.00 / 0.46 / 0.46 | 0.82 / 0.78 / 0.76<br>1.00 / 0.62 / 0.21 | 0.69 / 0.67 / 0.68<br>1.00 / 0.67 / 0.62 | 0.68 / 0.67 / 0.69<br>1.00 / 0.79 / 0.79 | 0.50 / 0.50 / 0.51<br>1.00 / 0.21 / 0.12 | 0.51 / 0.51 / 0.51<br>1.00 / 0.46 / 0.21 |
| L-corner 0 / 1x / 2x | 0.58 / 0.58 / 0.60<br>1.00 / 0.38 / 0.21 | 0.80 / 0.75 / 0.72<br>1.00 / 0.54 / 0.42 | 0.60 / 0.59 / 0.59<br>1.00 / 0.88 / 0.42 | 0.69 / 0.70 / 0.72<br>1.00 / 0.67 / 0.62 | 0.81 / 0.77 / 0.76<br>1.00 / 0.42 / 0.50 | 0.49 / 0.50 / 0.52<br>1.00 / 0.33 / 0.25 | 0.50 / 0.50 / 0.52<br>1.00 / 0.67 / 0.54 |

All rooms are in `out/robustness.json`.

**Findings:**
1. **Risk is robust, execution is not.** The mean risk changes by at most ±0.04 up to twice
   the base noise. Physical validity, however, collapses for techniques in which two
   operators cross in the doorway: crisscross and pie + crisscross fall to 21-38 % valid
   executions at 1x noise in M/L rooms.
2. **The single-side combination is the robust alternative in corner-fed rooms.** Its risk is
   almost that of crisscross (L-corner 0.59 vs 0.58), but it is 2-3 times more often
   collision-free at 1x noise (0.88 vs 0.38).
3. **Fewer people in the doorway means more robustness:** the two-man entry stays at 62-75 %
   valid across all noise levels; deliberate entry and limited penetration are also robust.
4. **Combined with A:** Low risk (crisscross), low predictability (mixing) and robust
   execution (combination / deliberate) pull in different directions. That is a trade-off
   worth reporting, and a target for the search for new techniques (stage 9).

## Limitations

- Single threat in A (no multi-threat game yet), grid of 5 % steps.
- "Valid" counts any body contact > 0.02 m·s as invalid. That is strict; real teams can absorb
  light contact.
- Noise is independent per operator; real errors are correlated (a slow #1 delays #2).
- Stylized techniques, free parameters (PARAMETERS.md).
