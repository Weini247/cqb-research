"""Black-box search over the plan space (cross-entropy method) + Pareto archive."""

from __future__ import annotations

import math
import os

import numpy as np

from . import fastsim
from .doctrine import SIDES
from .entry import OpPlan, Playbook, Result, evaluate
from .room import Room
from .team import Operator

# per operator: delay, tx, pod_x, pod_y, gaze1, gaze2, pie, enter, hold,
#               use_pod2, pod2_x, pod2_y, gaze3
LO = np.array([0.0, 0, 0, 0, -math.pi, -math.pi, 0, 0, 0, 0, 0, 0, -math.pi])
HI = np.array([6.0, 1, 1, 1, math.pi, math.pi, 1, 1, 2, 1, 1, 1, math.pi])
PER_OP = len(LO)
ANGLES = [4, 5, 12]
OBJECTIVE = "risk_multi"


def backend() -> str:
    """'torch' (GPU batch, default if installed) or 'numpy' (reference); env KILLHOUSE_BACKEND."""
    want = os.environ.get("KILLHOUSE_BACKEND", "auto")
    if want == "numpy" or not fastsim.available():
        return "numpy"
    return "torch"


def evaluate_many(room: Room, pbs: list[Playbook], team: list[Operator]) -> list[Result]:
    if backend() == "torch":
        return fastsim.evaluate_batch(room, pbs, team)
    return [evaluate(room, pb, team) for pb in pbs]


def bounds(n: int) -> tuple[np.ndarray, np.ndarray]:
    return np.tile(LO, n), np.tile(HI, n)


def decode(x: np.ndarray, room: Room, team: list[Operator], name: str = "found") -> Playbook:
    ops = []
    for i, op in enumerate(team):
        dl, tx, px, py, g1, g2, pie, enter, hold, use2, px2, py2, g3 = x[
            i * PER_OP : (i + 1) * PER_OP
        ]
        r = op.radius_m + 0.02
        pod = (r + px * (room.w - 2 * r), r + py * (room.d - 2 * r))
        s, k = SIDES[i]
        pie = pie if pie > 0.05 else 0.0
        pod2 = (r + px2 * (room.w - 2 * r), r + py2 * (room.d - 2 * r)) if use2 >= 0.5 else None
        ops.append(OpPlan(s, k, bool(enter >= 0.5), dl, tx, pod, g1, g2, pie, hold, pod2, g3))
    return Playbook(name, ops)


def encode(pb: Playbook, room: Room, team: list[Operator]) -> np.ndarray:
    v = []
    for op, p in zip(team, pb.ops, strict=True):
        r = op.radius_m + 0.02
        px = (p.pod[0] - r) / (room.w - 2 * r)
        py = (p.pod[1] - r) / (room.d - 2 * r)
        v += [p.delay, p.tx, px, py, p.gaze1, p.gaze2, p.pie, 1.0 if p.enter else 0.0, p.hold]
        if p.pod2 is None:
            v += [0.0, 0.5, 0.5, 0.0]
        else:
            px2 = (p.pod2[0] - r) / (room.w - 2 * r)
            py2 = (p.pod2[1] - r) / (room.d - 2 * r)
            v += [1.0, px2, py2, p.gaze3]
    lo, hi = bounds(len(team))
    return np.clip(np.array(v, float), lo, hi)


def score(res: Result, w: float) -> float:
    return (
        res.objective(OBJECTIVE)
        + w * res.t_clear
        + 20 * (res.collision + res.wall)
        + 5 * res.fratricide
    )


class Archive:
    """All valid evaluations as rows (risk, t_clear, fratricide) + plan vectors."""

    def __init__(self) -> None:
        self.rows: list[tuple[float, float, float]] = []
        self.xs: list[np.ndarray] = []

    def add(self, res: Result, x: np.ndarray) -> None:
        if res.feasible:
            self.rows.append((res.objective(OBJECTIVE), res.t_clear, res.fratricide))
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


def cem_minimize(
    score_batch,
    lo: np.ndarray,
    hi: np.ndarray,
    init: list[np.ndarray],
    iters: int = 40,
    pop: int = 40,
    elite: int = 8,
    seed: int = 0,
    angle_cols: tuple[int, ...] = (),
    explore: float = 0.2,
) -> tuple[np.ndarray, float]:
    """Cross-entropy method used by all optimizations (also by the reference cases in
    `reference.py`). score_batch maps an (k, d) array to k scores (lower is better).

    explore: share of every generation drawn uniformly from the bounds ("random immigrants").
    Without it the sampling distribution can collapse onto a local optimum; the L-corridor
    reference case failed in 2 of 5 seeds that way (see docs/REPORT_M2.md)."""
    rng = np.random.default_rng(seed)
    span = hi - lo
    init = [np.asarray(x, float) for x in init]
    scored = sorted(zip(score_batch(np.array(init)), init, strict=True), key=lambda s: s[0])
    mean, std = scored[0][1].copy(), span * 0.25
    best = scored[0]
    for _ in range(iters):
        xs = mean + std * rng.standard_normal((pop, len(mean)))
        n_exp = int(round(explore * pop))
        if n_exp:
            xs[:n_exp] = rng.uniform(lo, hi, (n_exp, len(mean)))
        for c in angle_cols:
            xs[:, c] = (xs[:, c] + math.pi) % (2 * math.pi) - math.pi
        xs = np.clip(xs, lo, hi)
        gen = sorted(zip(score_batch(xs), xs, strict=True), key=lambda s: s[0])
        if gen[0][0] < best[0]:
            best = gen[0]
        el = np.array([g[1] for g in gen[:elite]] + [best[1]])
        mean = 0.7 * el.mean(0) + 0.3 * mean
        std = np.maximum(0.7 * el.std(0) + 0.3 * std, span * 0.01)
    return best[1], float(best[0])


def cmaes_minimize(
    score_batch,
    lo: np.ndarray,
    hi: np.ndarray,
    init: list[np.ndarray],
    iters: int = 40,
    pop: int = 40,
    seed: int = 0,
    angle_cols: tuple[int, ...] = (),
    sigma0: float = 0.25,
) -> tuple[np.ndarray, float]:
    """CMA-ES (Hansen's standard parameters, full covariance) as a second optimizer family for
    the cross-check in docs/REPORT_M2.md. Same interface and evaluation budget as
    `cem_minimize`. Works in coordinates normalized to [0, 1]; samples outside the bounds are
    clipped for evaluation and penalized by their squared distance, angles wrap."""
    rng = np.random.default_rng(seed)
    span = hi - lo
    n, lam = len(lo), pop
    ang = np.zeros(n, bool)
    ang[list(angle_cols)] = True

    def repair(z: np.ndarray) -> np.ndarray:
        z = z.copy()
        z[:, ang] %= 1.0
        return np.clip(z, 0.0, 1.0)

    def evaluate_z(z: np.ndarray) -> np.ndarray:
        zr = repair(z)
        f = np.asarray(score_batch(lo + zr * span), float)
        return f + ((z - zr)[:, ~ang] ** 2).sum(1)  # wrapped angles are not out of bounds

    z0 = np.array([(np.asarray(x, float) - lo) / span for x in init])
    f0 = evaluate_z(z0)
    best_z, best_f = z0[int(np.argmin(f0))].copy(), float(f0.min())
    m, sigma = best_z.copy(), sigma0
    mu = lam // 2
    wts = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    wts /= wts.sum()
    mueff = 1.0 / (wts**2).sum()
    cc = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
    cs = (mueff + 2) / (n + mueff + 5)
    c1 = 2 / ((n + 1.3) ** 2 + mueff)
    cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff))
    damps = 1 + 2 * max(0.0, math.sqrt((mueff - 1) / (n + 1)) - 1) + cs
    chi_n = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    C, pc, ps = np.eye(n), np.zeros(n), np.zeros(n)
    for g in range(iters):
        D2, B = np.linalg.eigh(C)
        D = np.sqrt(np.maximum(D2, 1e-20))
        y = rng.standard_normal((lam, n)) @ (B * D).T
        z = m + sigma * y
        f = evaluate_z(z)
        order = np.argsort(f)
        if f[order[0]] < best_f:
            best_f, best_z = float(f[order[0]]), repair(z[order[:1]])[0]
        ys = y[order[:mu]]
        yw = wts @ ys
        m = m + sigma * yw
        m[ang] %= 1.0
        m = np.clip(m, -0.1, 1.1)
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * mueff) * (B @ ((B.T @ yw) / D))
        hsig = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (g + 1))) / chi_n < (
            1.4 + 2 / (n + 1)
        )
        pc = (1 - cc) * pc + hsig * math.sqrt(cc * (2 - cc) * mueff) * yw
        C = (
            (1 - c1 - cmu) * C
            + c1 * (np.outer(pc, pc) + (1 - hsig) * cc * (2 - cc) * C)
            + cmu * (ys.T * wts) @ ys
        )
        C = (C + C.T) / 2
        sigma = min(sigma * math.exp((cs / damps) * (np.linalg.norm(ps) / chi_n - 1)), 1.0)
    return lo + best_z * span, best_f


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
    method: str = "cem",
) -> tuple[np.ndarray, float]:
    """Search the plan space for weight w; every valid evaluation goes into the archive.
    method: 'cem' (default) or 'cmaes' (second optimizer family, same budget)."""
    lo, hi = bounds(len(team))

    def score_batch(xs: np.ndarray) -> list[float]:
        out = []
        for x, res in zip(
            xs, evaluate_many(room, [decode(x, room, team) for x in xs], team), strict=True
        ):
            archive.add(res, x)
            out.append(score(res, w))
        return out

    cols = tuple(a * PER_OP + j for a in range(len(team)) for j in ANGLES)
    if method == "cmaes":
        return cmaes_minimize(score_batch, lo, hi, init, iters, pop, seed, cols)
    return cem_minimize(score_batch, lo, hi, init, iters, pop, elite, seed, cols)
