"""Single-room geometry for the entry benchmark: rectangle, door in the wall y=0, obstacles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Box = tuple[float, float, float, float]  # x0, y0, x1, y1


@dataclass(frozen=True)
class Room:
    name: str
    w: float
    d: float
    door_x0: float
    door_x1: float
    obstacles: tuple[Box, ...] = ()
    res: float = 0.25
    wall_t: float = 0.2  # entry wall spans -wall_t <= y <= 0
    threat_r: float = 0.25  # a hidden person needs this clearance from walls and furniture

    @property
    def door_c(self) -> float:
        return (self.door_x0 + self.door_x1) / 2

    def points(self) -> np.ndarray:
        m = self.threat_r
        xs = np.arange(m, self.w - m + 1e-9, self.res)
        ys = np.arange(m, self.d - m + 1e-9, self.res)
        p = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
        keep = np.ones(len(p), bool)
        for x0, y0, x1, y1 in self.obstacles:
            inx = (p[:, 0] > x0 - m) & (p[:, 0] < x1 + m)
            keep &= ~(inx & (p[:, 1] > y0 - m) & (p[:, 1] < y1 + m))
        return p[keep]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "w": self.w,
            "d": self.d,
            "door": [self.door_x0, self.door_x1],
            "obstacles": [list(b) for b in self.obstacles],
            "res": self.res,
        }


def _seg_hits_box(px, py, qx, qy, box: Box) -> np.ndarray:
    """Slab test, broadcasting: does segment p->q intersect the box?"""
    x0, y0, x1, y1 = box
    t0 = np.zeros(np.broadcast_shapes(px.shape, qx.shape))
    t1 = np.ones_like(t0)
    for p, q, lo, hi in ((px, qx, x0, x1), (py, qy, y0, y1)):
        d = q - p
        with np.errstate(divide="ignore", invalid="ignore"):
            ta, tb = (lo - p) / d, (hi - p) / d
        inside = (p >= lo) & (p <= hi)
        par = d == 0
        tmin = np.where(par, np.where(inside, -np.inf, np.inf), np.minimum(ta, tb))
        tmax = np.where(par, np.where(inside, np.inf, -np.inf), np.maximum(ta, tb))
        t0, t1 = np.maximum(t0, tmin), np.minimum(t1, tmax)
    return t0 <= t1


def _through_door(room: Room, px, py, qx, qy) -> np.ndarray:
    ok = True
    for y in (0.0, -room.wall_t):
        with np.errstate(divide="ignore", invalid="ignore"):
            xc = px + (qx - px) * (y - py) / (qy - py)
        inside = (xc >= room.door_x0) & (xc <= room.door_x1)
        ok = ok & np.where((py < y) & (qy > y) | (py > y) & (qy < y), inside, True)
    return ok


def los(room: Room, p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Line of sight between observers p (K,2) and room points q (M,2) -> bool (K,M).

    Observers outside (y < 0) see into the room only through the door channel, i.e. the
    sight line must pass the opening at both faces of the wall (y = -wall_t and y = 0).
    """
    px, py = p[:, 0, None], p[:, 1, None]
    qx, qy = q[None, :, 0], q[None, :, 1]
    vis = np.where(py < 0, _through_door(room, px, py, qx, qy), True)
    for box in room.obstacles:
        vis &= ~_seg_hits_box(px, py, qx, qy, box)
    return vis


def generated_rooms(seed: int, n: int) -> list[Room]:
    """Random rectangular rooms for held-out evaluation: size, door position / width, 0-2 boxes."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        w = float(np.round(rng.uniform(3.0, 8.0) * 4) / 4)
        d = float(np.round(rng.uniform(3.0, 7.0) * 4) / 4)
        dw = float(rng.choice([0.8, 0.9, 1.0, 1.2]))
        x0 = float(np.round((0.15 + rng.uniform() * (w - 0.3 - dw)) * 20) / 20)
        boxes: list[Box] = []
        for _ in range(int(rng.choice([0, 1, 2], p=[0.5, 0.35, 0.15]))):
            for _try in range(20):
                bw, bd = rng.uniform(0.6, 1.6), rng.uniform(0.4, 1.0)
                bx = rng.uniform(0.3, max(0.31, w - 0.3 - bw))
                by = rng.uniform(d * 0.45, max(d * 0.45 + 0.01, d - 0.3 - bd))
                b = tuple(round(v, 2) for v in (bx, by, bx + bw, by + bd))
                if all(
                    b[2] + 0.6 < o[0] or o[2] + 0.6 < b[0] or b[3] + 0.6 < o[1] or o[3] + 0.6 < b[1]
                    for o in boxes
                ):
                    boxes.append(b)
                    break
        out.append(Room(f"G{seed}-{i:02d}", w, d, x0, round(x0 + dw, 2), tuple(boxes)))
    return out


def standard_rooms() -> list[Room]:
    """E0 geometry set: 3 sizes x centre/corner-fed door, plus two rooms with furniture."""
    rooms = []
    for size, (w, d) in (("S", (3.5, 3.5)), ("M", (5.0, 5.0)), ("L", (7.0, 6.0))):
        rooms.append(Room(f"{size}-center", w, d, w / 2 - 0.45, w / 2 + 0.45))
        rooms.append(Room(f"{size}-corner", w, d, 0.15, 1.05))
    rooms.append(Room("M-center-box", 5.0, 5.0, 2.05, 2.95, ((1.0, 3.2, 2.2, 3.8),)))
    rooms.append(Room("L-corner-box", 7.0, 6.0, 0.15, 1.05, ((4.2, 2.6, 5.0, 4.4),)))
    return rooms
