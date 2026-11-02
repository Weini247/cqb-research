"""Domain-neutral reference cases with known solutions (review R3, milestone M2a).

They check the visibility code and the optimizer against answers that are known
independently of any tactic:

1. **Comb gallery (art-gallery type):** a corridor with k deep, narrow teeth needs exactly k
   observers. Lower bound: the far end of each tooth is visible only from cells of that
   tooth and the corridor strip directly below it, and these sets are pairwise disjoint. Upper
   bound: a greedy cover finds k.
2. **L-corridor watchman:** the shortest straight walk from the start of an L-shaped corridor
   that sees every point. The exact optimum of the discretized problem comes from exhaustive
   search over all cells; the continuous optimum from the geometry. The same CEM that the
   benchmark uses (`optimize.cem_minimize`) must find it from every seed.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .geom import Floorplan, Grid, los_boxes, visibility
from .optimize import cem_minimize

T = 0.2


def comb_gallery(
    k: int, tooth_w: float = 1.0, gap_w: float = 1.0, depth: float = 4.0, base: float = 1.2
) -> Floorplan:
    """Corridor y in [0, base] with k teeth of width tooth_w going up to base + depth."""
    W = k * tooth_w + (k - 1) * gap_w
    H = base + depth
    walls = [
        (-T, -T, W + T, 0.0),
        (-T, H, W + T, H + T),
        (-T, -T, 0.0, H + T),
        (W, -T, W + T, H + T),
    ]
    regions = [("corridor", (0.0, 0.0, W, base))]
    for i in range(k):
        x0 = i * (tooth_w + gap_w)
        regions.append((f"tooth{i}", (x0, base, x0 + tooth_w, H)))
        if i < k - 1:
            walls.append((x0 + tooth_w, base, x0 + tooth_w + gap_w, H))  # solid block between teeth
    return Floorplan(
        (-T, -T, W + T, H + T),
        walls,
        regions=regions,
        walkable=[(0.0, 0.0, W, H)],
        threat_r=0.1,
        point_res=0.25,
    )


def comb_check(k: int) -> dict:
    fp = comb_gallery(k)
    grid, q = Grid(fp, inflate=0.0), fp.points()
    vis = visibility(fp, grid, q)
    free = grid.see_free
    reg = fp.region_of(q)
    # deepest point of every tooth
    tips = [int(np.flatnonzero(reg == j)[np.argmax(q[reg == j][:, 1])]) for j in range(1, k + 1)]
    seers = [set(np.flatnonzero(vis[:, t] & free)) for t in tips]
    disjoint = all(not (a & b) for i, a in enumerate(seers) for b in seers[i + 1 :])
    # greedy set cover over observer cells
    left = np.ones(len(q), bool)
    chosen = []
    cand = np.flatnonzero(free)
    while left.any() and len(chosen) < 3 * k:
        gain = (vis[cand] & left).sum(1)
        c = cand[int(np.argmax(gain))]
        chosen.append(int(c))
        left &= ~vis[c]
    return {
        "k": k,
        "lower_bound_k": disjoint,
        "greedy_guards": len(chosen),
        "all_seen": not left.any(),
    }


def l_corridor(L1: float = 6.0, L2: float = 6.0, w: float = 1.2) -> Floorplan:
    """Horizontal arm x in [0, L1], y in [0, w]; vertical arm x in [L1 - w, L1], y in [0, L2]."""
    walls = [
        (-T, -T, L1 + T, 0.0),
        (-T, -T, 0.0, w + T),
        (L1, -T, L1 + T, L2 + T),
        (L1 - w - T, L2, L1 + T, L2 + T),
        (-T, w, L1 - w, w + T),
        (L1 - w - T, w, L1 - w, L2 + T),
    ]
    regions = [("arm_h", (0.0, 0.0, L1 - w, w)), ("arm_v", (L1 - w, 0.0, L1, L2))]
    return Floorplan(
        (-T, -T, L1 + T, L2 + T),
        walls,
        regions=regions,
        walkable=[(0.0, 0.0, L1, w), (L1 - w, 0.0, L1, L2)],
        threat_r=0.1,
        point_res=0.25,
    )


class Watchman:
    """Single observer walks straight from S to P and sees everything on the way (360 deg)."""

    def __init__(self, fp: Floorplan, start=(0.3, 0.6), step: float = 0.1):
        self.fp, self.q, self.S, self.step = fp, fp.points(), np.array(start), step

    def unseen(self, P: np.ndarray) -> float:
        n = max(2, int(math.ceil(np.linalg.norm(P - self.S) / self.step)) + 1)
        path = self.S + (P - self.S) * np.linspace(0, 1, n)[:, None]
        blocked = ~los_boxes(self.S[None], P[None], self.fp.blockers)[0, 0]
        seen = los_boxes(path, self.q, self.fp.blockers).any(0)
        return 1.0 if blocked else float(1 - seen.mean())

    def score(self, xs: np.ndarray) -> list[float]:
        return [float(np.linalg.norm(x - self.S)) + 100 * self.unseen(x) for x in xs]

    def exhaustive(self, res: float = 0.05) -> tuple[np.ndarray, float]:
        x0, y0, x1, y1 = self.fp.bounds
        best, best_d = None, math.inf
        for x in np.arange(max(x0, 0) + res / 2, x1, res):
            for y in np.arange(max(y0, 0) + res / 2, y1, res):
                P = np.array([x, y])
                d = float(np.linalg.norm(P - self.S))
                if d < best_d and self.unseen(P) == 0.0:
                    best, best_d = P, d
        return best, best_d


def watchman_check(seeds=range(5), iters: int = 30, pop: int = 32) -> dict:
    fp = l_corridor()
    wm = Watchman(fp)
    P_ex, d_ex = wm.exhaustive()
    lo, hi = np.array([0.0, 0.0]), np.array([6.0, 6.0])
    found = []
    for s in seeds:
        x0 = np.random.default_rng(100 + s).uniform(lo, hi)
        x, f = cem_minimize(wm.score, lo, hi, [x0], iters=iters, pop=pop, seed=s)
        found.append(
            {
                "seed": s,
                "P": np.round(x, 3).tolist(),
                "length": round(float(np.linalg.norm(x - wm.S)), 3),
                "unseen": round(wm.unseen(x), 4),
            }
        )
    return {
        "exhaustive_length": round(d_ex, 3),
        "exhaustive_P": np.round(P_ex, 3).tolist(),
        "cem": found,
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-reference")
    ap.add_argument("--out", type=Path, default=Path("out/reference.json"))
    a = ap.parse_args(argv)
    out = {"comb": [comb_check(k) for k in (2, 3, 4)], "watchman": watchman_check()}
    for c in out["comb"]:
        print(
            f"comb k={c['k']}: disjoint tip sets (lower bound k) {c['lower_bound_k']}, "
            f"greedy {c['greedy_guards']} guards, all seen {c['all_seen']}"
        )
    w = out["watchman"]
    print(f"watchman exhaustive: {w['exhaustive_length']} m at {w['exhaustive_P']}")
    for f in w["cem"]:
        print(f"  CEM seed {f['seed']}: {f['length']} m, unseen {f['unseen']}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
