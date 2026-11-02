"""Adversary who knows the plan: worst-case threat placement and the value of mixing techniques.

Per threat position the single-threat duel gives P(team hit | threat there). A random threat
yields the mean over positions (`Result.risk`); an adversary who knows the technique stands
at the worst position (max). If the team picks its technique at random from a mixture, the
adversary can only best-respond to the mixture: min over mixtures of max over positions of
the mixed risk is the value of a zero-sum game, and its gap to the best pure technique is
the "price of predictability".
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

from .entry import DT, EVAL_CFG, NT, ModelCfg, Playbook, los, trajectories, wrap
from .room import Room, standard_rooms
from .tactics import build
from .team import Operator, default_team


def point_risk(
    room: Room, pb: Playbook, team: list[Operator], cfg: ModelCfg = EVAL_CFG
) -> np.ndarray:
    """P(team hit) for a single threat at each threat position (same duel as entry.evaluate)."""
    pos, gaze, _ = trajectories(room, team, pb, cfg)
    q = room.points()
    m, n = len(q), len(team)
    p = pos.reshape(-1, 2)
    vis = los(room, p, q).reshape(NT, n, m)
    ang = np.arctan2(q[None, :, 1] - p[:, 1, None], q[None, :, 0] - p[:, 0, None]).reshape(NT, n, m)
    looked = vis & (np.abs(wrap(ang - gaze[..., None])) <= cfg.half_fov)
    seen = np.cumsum(looked.any(1), 0) >= max(1, round(cfg.dwell / DT))
    first = np.where(seen.any(0), seen.argmax(0), NT)
    alive = np.arange(NT)[:, None] < first[None, :]
    identified = ~alive
    if cfg.id_time > 0:
        dist = np.hypot(q[None, :, 0] - p[:, 0, None], q[None, :, 1] - p[:, 1, None]).reshape(
            NT, n, m
        )
        k_id = max(1, round((cfg.dwell + cfg.id_time) / DT))
        identified = np.cumsum((looked & (dist <= cfg.id_range)).any(1), 0) >= k_id
    sees = vis.any(1)
    ready = np.cumsum(sees, 0) >= max(1, round(cfg.threat_react / DT))
    h = np.where(ready & sees, 1 - math.exp(-cfg.threat_rate * DT), 0.0)
    qe = 1 - np.exp(-cfg.engage_rate * DT * looked.sum(1) * identified)
    surv = np.cumprod((1 - h) * (1 - qe), 0)
    before = np.vstack([np.ones((1, m)), surv[:-1]])
    return (before * h).sum(0)


def game_value(r: np.ndarray, step: float = 0.05) -> tuple[float, np.ndarray]:
    """min over mixtures w (simplex grid) of max over positions of w @ r; r is (techniques, M)."""
    k = r.shape[0]
    best, best_w = math.inf, None
    ticks = int(round(1 / step))
    for c in itertools.product(range(ticks + 1), repeat=k - 1):
        if sum(c) > ticks:
            continue
        w = np.array([*c, ticks - sum(c)]) / ticks
        v = float((w @ r).max())
        if v < best:
            best, best_w = v, w
    return best, best_w


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-adversary")
    ap.add_argument(
        "--tactics", nargs="+", default=["crisscross", "buttonhook", "combination-cross", "limited"]
    )
    ap.add_argument("--out", type=Path, default=Path("out/adversary.json"))
    a = ap.parse_args(argv)
    team = default_team()
    rows = []
    hdr = f"{'room':13s} " + " ".join(f"{t[:10]:>10s}" for t in a.tactics)
    print(
        "mean (random threat) / worst case (adversary)\n"
        + hdr
        + f" {'best pure':>10s} {'mixed':>7s}  mixture"
    )
    for room in standard_rooms():
        r = np.array([point_risk(room, build(t, room, team), team) for t in a.tactics])
        mean, worst = r.mean(1), r.max(1)
        pure = float(worst.min())
        mixed, w = game_value(r)
        rows.append(
            {
                "room": room.name,
                "tactics": a.tactics,
                "mean": mean.round(4).tolist(),
                "worst": worst.round(4).tolist(),
                "best_pure_worst": round(pure, 4),
                "mixed_value": round(mixed, 4),
                "mixture": w.round(2).tolist(),
                "price_of_predictability": round(1 - mixed / pure, 4) if pure > 0 else 0.0,
            }
        )
        cells = " ".join(f"{mu:.2f}/{wc:.2f}" for mu, wc in zip(mean, worst, strict=True))
        print(f"{room.name:13s} {cells} {pure:10.3f} {mixed:7.3f}  {np.round(w, 2).tolist()}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rows), encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
