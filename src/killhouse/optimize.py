"""Black-box search over the plan space (cross-entropy method) + Pareto archive."""

from __future__ import annotations

import math

import numpy as np

from .doctrine import SIDES
from .entry import OpPlan, Playbook, Result, evaluate
from .room import Room
from .team import Operator

# per operator: delay, tx, pod_x, pod_y, gaze1, gaze2, pie, enter, hold
LO = np.array([0.0, 0, 0, 0, -math.pi, -math.pi, 0, 0, 0])
HI = np.array([6.0, 1, 1, 1, math.pi, math.pi, 1, 1, 2])
PER_OP = len(LO)
ANGLES = [4, 5]


def bounds(n: int) -> tuple[np.ndarray, np.ndarray]:
    return np.tile(LO, n), np.tile(HI, n)


def decode(x: np.ndarray, room: Room, team: list[Operator], name: str = "found") -> Playbook:
    ops = []
    for i, op in enumerate(team):
        dl, tx, px, py, g1, g2, pie, enter, hold = x[i * PER_OP : (i + 1) * PER_OP]
        r = op.radius_m + 0.02
        pod = (r + px * (room.w - 2 * r), r + py * (room.d - 2 * r))
        s, k = SIDES[i]
        pie = pie if pie > 0.05 else 0.0
        ops.append(OpPlan(s, k, bool(enter >= 0.5), dl, tx, pod, g1, g2, pie, hold))
    return Playbook(name, ops)


def encode(pb: Playbook, room: Room, team: list[Operator]) -> np.ndarray:
    v = []
    for op, p in zip(team, pb.ops, strict=True):
        r = op.radius_m + 0.02
        px = (p.pod[0] - r) / (room.w - 2 * r)
        py = (p.pod[1] - r) / (room.d - 2 * r)
        v += [p.delay, p.tx, px, py, p.gaze1, p.gaze2, p.pie, 1.0 if p.enter else 0.0, p.hold]
    lo, hi = bounds(len(team))
    return np.clip(np.array(v, float), lo, hi)


def score(res: Result, w: float) -> float:
    return res.risk + w * res.t_clear + 20 * (res.collision + res.wall) + 5 * res.fratricide


class Archive:
    """All valid evaluations as rows (risk, t_clear, fratricide) + plan vectors."""

    def __init__(self) -> None:
        self.rows: list[tuple[float, float, float]] = []
        self.xs: list[np.ndarray] = []

    def add(self, res: Result, x: np.ndarray) -> None:
        if res.feasible:
            self.rows.append((res.risk, res.t_clear, res.fratricide))
            self.xs.append(x.copy())

    def front(self, fr_max: float = math.inf) -> list[int]:
        """Indices of the (risk, t_clear) Pareto front among rows with fratricide <= fr_max."""
        idx = [i for i, r in enumerate(self.rows) if r[2] <= fr_max + 1e-9]
        out, best_e = [], math.inf
        for i in sorted(idx, key=lambda i: (self.rows[i][1], self.rows[i][0])):
            if self.rows[i][0] < best_e - 1e-9:
                out.append(i)
                best_e = self.rows[i][0]
        return out

    def gap(self, e: float, t: float, fr: float) -> dict:
        """Best found vs a reference point at equal-or-better time / risk / fratricide."""
        ok = [r for r in self.rows if r[2] <= fr + 1e-9]
        e_star = min([r[0] for r in ok if r[1] <= t + 1e-9], default=e)
        t_star = min([r[1] for r in ok if r[0] <= e + 1e-9], default=t)
        return {
            "risk_best": round(e_star, 4),
            "t_best": round(t_star, 3),
            "gap_risk": round(max(0.0, 1 - e_star / e), 4) if e > 0 else 0.0,
            "gap_time": round(max(0.0, 1 - t_star / t), 4) if t > 0 else 0.0,
        }


def cem(
    room: Room,
    team: list[Operator],
    w: float,
    init: list[np.ndarray],
    archive: Archive,
    iters: int = 40,
    pop: int = 40,
    elite: int = 8,
    seed: int = 0,
) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(seed)
    lo, hi = bounds(len(team))
    span = hi - lo
    scored = []
    for x in init:
        res = evaluate(room, decode(x, room, team), team)
        archive.add(res, x)
        scored.append((score(res, w), x))
    scored.sort(key=lambda s: s[0])
    mean, std = scored[0][1].copy(), span * 0.25
    best = scored[0]
    for _ in range(iters):
        xs = mean + std * rng.standard_normal((pop, len(mean)))
        for a in range(len(team)):
            for j in ANGLES:
                c = a * PER_OP + j
                xs[:, c] = (xs[:, c] + math.pi) % (2 * math.pi) - math.pi
        xs = np.clip(xs, lo, hi)
        gen = []
        for x in xs:
            res = evaluate(room, decode(x, room, team), team)
            archive.add(res, x)
            gen.append((score(res, w), x))
        gen.sort(key=lambda s: s[0])
        if gen[0][0] < best[0]:
            best = gen[0]
        el = np.array([g[1] for g in gen[:elite]] + [best[1]])
        mean = 0.7 * el.mean(0) + 0.3 * mean
        std = np.maximum(0.7 * el.std(0) + 0.3 * std, span * 0.01)
    return best[1], best[0]
