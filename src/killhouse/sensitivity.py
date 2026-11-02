"""One-at-a-time sensitivity of the doctrine ranking to model and geometry assumptions.

Only the stylized doctrines are evaluated (no optimizer), so this runs in seconds.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
from itertools import combinations
from pathlib import Path

from .doctrine import doctrines
from .entry import DEFAULT_CFG, ModelCfg, evaluate
from .optimize import OBJECTIVE
from .room import Room, standard_rooms
from .team import Operator, default_team

AXES: dict[str, list] = {
    "half_fov_deg": [40, 60],
    "dwell": [0.2, 0.5],
    "turn_rate": [3.0, 6.0],
    "threat_react": [0.15, 0.6],
    "threat_rate": [0.5, 2.0],
    "engage_rate": [2.0, 8.0],
    "door_w": [0.8, 1.2],
    "body_scale": [0.85, 1.15],
}


def _variant(axis: str | None, value) -> tuple[ModelCfg, list[Room], list[Operator]]:
    cfg, rooms, team = DEFAULT_CFG, standard_rooms(), default_team()
    if axis == "half_fov_deg":
        cfg = dataclasses.replace(cfg, half_fov=math.radians(value))
    elif axis in ("dwell", "turn_rate", "threat_react", "threat_rate", "engage_rate"):
        cfg = dataclasses.replace(cfg, **{axis: value})
    elif axis == "door_w":
        rooms = [
            dataclasses.replace(r, door_x0=r.door_c - value / 2, door_x1=r.door_c + value / 2)
            if r.door_x0 > 0.5
            else dataclasses.replace(r, door_x1=r.door_x0 + value)
            for r in rooms
        ]
    elif axis == "body_scale":
        team = [dataclasses.replace(o, radius_m=round(o.radius_m * value, 3)) for o in team]
    return cfg, rooms, team


def ranking(cfg: ModelCfg, rooms: list[Room], team: list[Operator]) -> dict[str, dict]:
    out = {}
    for room in rooms:
        rows = {}
        for pb in doctrines(room, team):
            res = evaluate(room, pb, team, cfg=cfg)
            rows[pb.name] = res.objective(OBJECTIVE) if res.feasible else math.inf
        out[room.name] = rows
    return out


def kendall(a: dict[str, float], b: dict[str, float]) -> float:
    """Kendall tau-a over doctrine pairs; pairs with two invalid doctrines are skipped."""
    s = n = 0
    for x, y in combinations(sorted(a), 2):
        da, db = a[x] - a[y], b[x] - b[y]
        if math.isnan(da) or math.isnan(db):
            continue
        n += 1
        s += math.copysign(1, da) * math.copysign(1, db) if da and db else 0
    return s / n if n else float("nan")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-sens")
    ap.add_argument("--out", type=Path, default=Path("out/sensitivity.json"))
    a = ap.parse_args(argv)
    base = ranking(*_variant(None, None))
    best = {r: min(v, key=v.get) for r, v in base.items()}
    results = {"baseline": base, "variants": []}
    print(f"{'axis':14s} {'value':>6s} {'tau':>5s} {'best same':>9s}  changed rooms")
    for axis, values in AXES.items():
        for value in values:
            rk = ranking(*_variant(axis, value))
            taus = [kendall(base[r], rk[r]) for r in base]
            taus = [t for t in taus if not math.isnan(t)]
            changed = [r for r in base if min(rk[r], key=rk[r].get) != best[r]]
            tau = sum(taus) / len(taus)
            results["variants"].append(
                {"axis": axis, "value": value, "tau": tau, "changed": changed, "ranking": rk}
            )
            same = len(base) - len(changed)
            print(f"{axis:14s} {value:6} {tau:5.2f} {same:4d}/{len(base)}  {', '.join(changed)}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(results, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
