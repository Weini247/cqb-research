"""Checks that must pass before the E1 preregistration is frozen (review R4).

Both run on development rooms only and use the rules fixed in PREREG_E1_draft.md section 8:

- `precision`: Monte-Carlo error of held-out estimates, from independent scenario samples.
  Decides the number of evaluation scenarios.
- `calibration`: false-positive rate of the H1 test when the true door effect is 0.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
from pathlib import Path

import numpy as np

from . import optimize
from .analysis import corner_coefficient, family, is_corner, load_rooms, valid_pairs
from .doctrine import doctrines
from .entry import EVAL_CFG, evaluate
from .optimize import decode
from .room import generated_rooms
from .team import default_team

BLOCK = 32  # scenarios per independent sample
FIRST_SALT = 2  # salts 0 and 1 are the planning and held-out scenarios
SCENARIO_CHOICES = (32, 64, 128, 256, 512)
TARGET_GAP_MEDIAN = 0.02  # Monte-Carlo standard error of a relative gap
TARGET_GAP_P90 = 0.03
TARGET_DIFF_MEDIAN = 0.01  # ... of a paired risk difference between two techniques
CALIBRATION_LIMIT = 0.06  # false-positive rate allowed at nominal one-sided 0.05


def candidate(r: dict, d: dict) -> tuple[np.ndarray, float] | None:
    """Plan of the pooled front with the lowest planning risk under the constraints of d.

    The rehearsal stored fronts, not the selected plans, so this stands in for the selection."""
    ok = [
        p
        for p in r["front_plans"]
        if p["metrics"][1] <= d["t_clear"] + 1e-3 and p["metrics"][2] <= d["fratricide"] + 1e-3
    ]
    if not ok:
        return None
    p = min(ok, key=lambda p: p["metrics"][0])
    return np.array(p["x"]), p["metrics"][0]


def risks(room, pb, team, salts) -> np.ndarray:
    return np.array(
        [
            evaluate(room, pb, team, cfg=dataclasses.replace(EVAL_CFG, scenario_salt=s)).objective(
                optimize.OBJECTIVE
            )
            for s in salts
        ]
    )


def scenario_table(sd_gap: list[float], sd_diff: list[float]) -> dict:
    """Standard errors for each scenario count, from the spread of BLOCK-scenario samples."""
    out = {}
    for n in SCENARIO_CHOICES:
        f = math.sqrt(BLOCK / n)
        gap_med = float(np.median(sd_gap)) * f
        gap_p90 = float(np.percentile(sd_gap, 90)) * f
        diff_med = float(np.median(sd_diff)) * f
        out[n] = {
            "se_gap_median": gap_med,
            "se_gap_p90": gap_p90,
            "se_diff_median": diff_med,
            "meets_target": gap_med <= TARGET_GAP_MEDIAN
            and gap_p90 <= TARGET_GAP_P90
            and diff_med <= TARGET_DIFF_MEDIAN,
        }
    return out


def smallest_sufficient(table: dict) -> int | None:
    return next((n for n in SCENARIO_CHOICES if table[n]["meets_target"]), None)


def precision(rows: list[dict], seed: int, n_rooms: int, n_blocks: int = 16, log=print) -> dict:
    team = default_team()
    rooms = {r.name: r for r in generated_rooms(seed, n_rooms)}
    salts = range(FIRST_SALT, FIRST_SALT + n_blocks)
    sd_gap, sd_diff, ratio_bias, optimism, skipped = [], [], [], [], 0
    for row in rows:
        room = rooms[row["room"]["name"]]
        pbs = {pb.name: pb for pb in doctrines(room, team)}
        base = {}
        for d in row["doctrines"]:
            if not d["feasible"]:
                continue
            base[family(d["name"])] = ref = risks(room, pbs[d["name"]], team, salts)
            c = candidate(row, d)
            if c is None:
                skipped += 1
                continue
            found = risks(room, decode(c[0], room, team), team, salts)
            gaps = 1 - found / ref
            sd_gap.append(float(gaps.std(ddof=1)))
            ratio_bias.append(float(gaps.mean() - (1 - found.mean() / ref.mean())))
            optimism.append(float(found.mean() - c[1]))
        if "crisscross" in base and "buttonhook" in base:
            sd_diff.append(float((base["crisscross"] - base["buttonhook"]).std(ddof=1)))
        log(f"{room.name}: {len(sd_gap)} pairs")
    table = scenario_table(sd_gap, sd_diff)
    return {
        "blocks": n_blocks,
        "block_size": BLOCK,
        "pairs": len(sd_gap),
        "pairs_without_candidate": skipped,
        "technique_comparisons": len(sd_diff),
        "table": table,
        "chosen_scenarios": smallest_sufficient(table),
        "ratio_bias_at_32_mean": float(np.mean(ratio_bias)),
        "planning_optimism_mean": float(np.mean(optimism)),
        "planning_optimism_p90": float(np.percentile(optimism, 90)),
    }


def calibration(rows: list[dict], n_sim: int = 1000, n_boot: int = 2000, seed: int = 0) -> dict:
    """Simulate H1 with a true door effect of 0 on the room design of the given results."""
    pts = [(r, d) for r, d in valid_pairs(rows) if family(d["name"]) == "crisscross"]
    gap = np.array([d["gap_selected"] for _, d in pts])
    corner = np.array([is_corner(r["room"]) for r, _ in pts], float)
    width = np.array([r["room"]["w"] for r, _ in pts])
    X = np.c_[np.ones(len(gap)), corner, width]
    beta = np.linalg.lstsq(X, gap, rcond=None)[0]
    resid = gap - X @ beta
    rng = np.random.default_rng(seed)
    ps = []
    for k in range(n_sim):
        y = beta[0] + beta[2] * width + rng.choice(resid, len(resid))
        ps.append(corner_coefficient(y, corner, width, n_boot, seed=k)["p"])
    ps = np.array(ps)
    return {
        "n_rooms": len(gap),
        "n_sim": n_sim,
        "n_boot": n_boot,
        "rate_at_0.05": float(np.mean(ps < 0.05)),
        "rate_at_0.025": float(np.mean(ps < 0.025)),
        "limit": CALIBRATION_LIMIT,
        "accepted": float(np.mean(ps < 0.05)) <= CALIBRATION_LIMIT,
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-prefreeze")
    ap.add_argument("check", choices=("precision", "calibration"))
    ap.add_argument("files", nargs="+", type=Path, help="result files of development rooms")
    ap.add_argument("--generated", nargs=2, type=int, metavar=("SEED", "N"), default=(1, 40))
    ap.add_argument("--out", type=Path, default=Path("out/prefreeze.json"))
    a = ap.parse_args(argv)
    if a.generated[0] == 2026:
        ap.error("the confirmatory rooms must not be used here")
    rows = load_rooms(a.files)
    res = precision(rows, *a.generated) if a.check == "precision" else calibration(rows)
    print(json.dumps(res, indent=1))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
