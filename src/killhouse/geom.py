"""General floorplan geometry: axis-aligned blocking boxes, threat points, precomputed visibility.

Line of sight in a multi-room floorplan is expensive to test per step, so visibility is
precomputed once per floorplan from every free observer cell (0.25 m grid) to every threat
point; an evaluation then only looks up rows of that matrix.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np

from .room import Box, _seg_hits_box

OBS_RES = 0.25


@dataclass
class Floorplan:
    bounds: Box  # x0, y0, x1, y1 of everything incl. the outside landing
    walls: list[Box]
    doors: list[Box] = field(default_factory=list)  # open door leaves (block sight and bodies)
    furniture: list[Box] = field(default_factory=list)
    regions: list[tuple[str, Box]] = field(default_factory=list)  # name, interior rect
    walkable: list[Box] = field(default_factory=list)  # areas bodies/observers may occupy at all
    windows: list[Box] = field(default_factory=list)  # block bodies, not sight (pass-throughs)
    threat_r: float = 0.25
    point_res: float = 0.3

    @property
    def blockers(self) -> list[Box]:
        return self.walls + self.doors + self.furniture

    def region_of(self, p: np.ndarray) -> np.ndarray:
        """Index of the region containing each point (-1: none, e.g. doorways, outside)."""
        out = np.full(len(p), -1)
        for k, (_, (x0, y0, x1, y1)) in enumerate(self.regions):
            inside = (p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
            out[inside & (out < 0)] = k
        return out

    def points(self) -> np.ndarray:
        """Threat positions: grid in every region, clear of walls, doors and furniture."""
        m, pts = self.threat_r, []
        for _, (x0, y0, x1, y1) in self.regions:
            xs = np.arange(x0 + m, x1 - m + 1e-9, self.point_res)
            ys = np.arange(y0 + m, y1 - m + 1e-9, self.point_res)
            if len(xs) and len(ys):
                pts.append(np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2))
        p = np.concatenate(pts)
        keep = np.ones(len(p), bool)
        for x0, y0, x1, y1 in self.doors + self.furniture:
            keep &= ~(
                (p[:, 0] > x0 - m) & (p[:, 0] < x1 + m) & (p[:, 1] > y0 - m) & (p[:, 1] < y1 + m)
            )
        return p[keep]


def los_boxes(p: np.ndarray, q: np.ndarray, boxes: list[Box]) -> np.ndarray:
    px, py = p[:, 0, None], p[:, 1, None]
    qx, qy = q[None, :, 0], q[None, :, 1]
    vis = np.ones((len(p), len(q)), bool)
    for b in boxes:
        vis &= ~_seg_hits_box(px, py, qx, qy, b)
    return vis


class Grid:
    """Observer / walking grid over the floorplan bounds."""

    def __init__(self, fp: Floorplan, inflate: float = 0.2):
        x0, y0, x1, y1 = fp.bounds
        self.x0, self.y0 = x0, y0
        self.nx = int(math.ceil((x1 - x0) / OBS_RES)) + 1
        self.ny = int(math.ceil((y1 - y0) / OBS_RES)) + 1
        xs = x0 + np.arange(self.nx) * OBS_RES
        ys = y0 + np.arange(self.ny) * OBS_RES
        self.centers = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)  # index = iy * nx + ix

        def blocked(pad, extra=()):
            c = self.centers
            m = np.ones(len(c), bool) if fp.walkable else np.zeros(len(c), bool)
            for bx0, by0, bx1, by1 in fp.walkable:
                m &= ~((c[:, 0] >= bx0) & (c[:, 0] <= bx1) & (c[:, 1] >= by0) & (c[:, 1] <= by1))
            for bx0, by0, bx1, by1 in list(fp.blockers) + list(extra):
                m |= (
                    (c[:, 0] > bx0 - pad)
                    & (c[:, 0] < bx1 + pad)
                    & (c[:, 1] > by0 - pad)
                    & (c[:, 1] < by1 + pad)
                )
            return m

        self.see_free = ~blocked(0.0)  # an observer can stand here (not inside a wall)
        self.walk_free = ~blocked(inflate, fp.windows)  # a body centre can be here
        self.region = fp.region_of(self.centers)
        # a body centre can round to a cell inside a wall or door leaf (0.25 m grid); such cells
        # borrow the visibility of the nearest free cell instead of being blind
        free = np.nonzero(self.see_free)[0]
        self.see_map = np.arange(len(self.centers))
        for b in np.nonzero(~self.see_free)[0]:
            self.see_map[b] = free[
                np.argmin(np.sum((self.centers[free] - self.centers[b]) ** 2, 1))
            ]

    def see_index(self, p: np.ndarray) -> np.ndarray:
        """Visibility row for a world position (nearest cell an observer can stand in)."""
        return self.see_map[self.index(p)]

    def index(self, p: np.ndarray) -> np.ndarray:
        ix = np.clip(np.rint((p[..., 0] - self.x0) / OBS_RES).astype(int), 0, self.nx - 1)
        iy = np.clip(np.rint((p[..., 1] - self.y0) / OBS_RES).astype(int), 0, self.ny - 1)
        return iy * self.nx + ix

    def astar(self, start: np.ndarray, goal: np.ndarray, allowed: np.ndarray) -> list[np.ndarray]:
        """8-connected path between world points over walkable, allowed cells (no corner cuts).
        Returns waypoints in world coordinates incl. the exact start and goal."""
        ok = self.walk_free & allowed
        s, g = int(self.index(start)), int(self.index(goal))
        ok[s] = ok[g] = True
        nx = self.nx
        dist = {s: 0.0}
        came: dict[int, int] = {}
        heap = [(0.0, s)]
        gx, gy = g % nx, g // nx
        while heap:
            _, c = heapq.heappop(heap)
            if c == g:
                break
            cx, cy = c % nx, c // nx
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    x, y = cx + dx, cy + dy
                    if not (0 <= x < nx and 0 <= y < self.ny):
                        continue
                    n = y * nx + x
                    if not ok[n] or (dx and dy and not (ok[cy * nx + x] and ok[y * nx + cx])):
                        continue
                    nd = dist[c] + (1.4142 if dx and dy else 1.0)
                    if nd < dist.get(n, 1e18):
                        dist[n], came[n] = nd, c
                        heapq.heappush(heap, (nd + math.hypot(x - gx, y - gy), n))
        if g not in dist:
            raise RuntimeError("no path")
        cells = [g]
        while cells[-1] != s:
            cells.append(came[cells[-1]])
        cells = cells[::-1]
        # drop collinear cells to keep the polyline short
        pts = [self.centers[c] for c in cells]
        keep = [pts[0]]
        for a, b in zip(pts[1:-1], pts[2:], strict=False):
            d1, d2 = a - keep[-1], b - a
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) > 1e-9:
                keep.append(a)
        return [np.asarray(start, float)] + keep[1:] + [np.asarray(goal, float)]


def reachable(g: Grid, start: np.ndarray) -> np.ndarray:
    """Walkable cells connected to `start` (8-neighbourhood without cutting corners, as A*)."""
    ok, nx = g.walk_free, g.nx
    seen = np.zeros(len(ok), bool)
    s = int(g.index(start))
    seen[s], todo = True, [s]
    while todo:
        c = todo.pop()
        cx, cy = c % nx, c // nx
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = cx + dx, cy + dy
                if not (dx or dy) or not (0 <= x < nx and 0 <= y < g.ny):
                    continue
                n = y * nx + x
                if (
                    seen[n]
                    or not ok[n]
                    or (dx and dy and not (ok[cy * nx + x] and ok[y * nx + cx]))
                ):
                    continue
                seen[n] = True
                todo.append(n)
    return seen


def visibility(fp: Floorplan, grid: Grid, q: np.ndarray, chunk: int = 256) -> np.ndarray:
    """Bool matrix (cells, points): free observer cell has line of sight to threat point."""
    vis = np.zeros((len(grid.centers), len(q)), bool)
    idx = np.nonzero(grid.see_free)[0]
    for k in range(0, len(idx), chunk):
        sl = idx[k : k + chunk]
        vis[sl] = los_boxes(grid.centers[sl], q, fp.blockers)
    return vis


def visibility_fast(fp: Floorplan, grid: Grid, q: np.ndarray, chunk: int = 1024) -> np.ndarray:
    """Same matrix as `visibility`, computed on the GPU in float64 when PyTorch with CUDA is
    available (houses have several thousand cells x points); otherwise falls back to numpy.
    Tested for equality with `visibility` in tests/test_house.py."""
    from . import fastsim

    if not fastsim.available() or fastsim.device().type != "cuda":
        return visibility(fp, grid, q)
    torch, dev = fastsim.torch, fastsim.device()
    vis = np.zeros((len(grid.centers), len(q)), bool)
    idx = np.nonzero(grid.see_free)[0]
    qt = torch.tensor(q, dtype=torch.float64, device=dev)
    qx, qy = qt[None, :, 0], qt[None, :, 1]
    for k in range(0, len(idx), chunk):
        sl = idx[k : k + chunk]
        p = torch.tensor(grid.centers[sl], dtype=torch.float64, device=dev)
        px, py = p[:, 0, None], p[:, 1, None]
        ok = torch.ones((len(sl), len(q)), dtype=torch.bool, device=dev)
        for b in fp.blockers:
            ok &= ~fastsim._seg_hits_box(px, py, qx, qy, b)
        vis[sl] = ok.cpu().numpy()
    return vis
