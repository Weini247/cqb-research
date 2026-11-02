"""Apartment generator: hallway with rooms on both sides, a living area at the far end,
doors with swing side, wardrobes, and an outside landing in front of the entrance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geom import Floorplan
from .room import Box

T = 0.2  # wall thickness (centreline +- T/2)
LEAF = 0.05


@dataclass
class Door:
    name: str
    side: str  # wall of the *entered* room the door sits in: bottom / top / left / right
    a: float  # opening along the wall axis (world coordinate)
    b: float
    line: float  # wall centreline coordinate
    into: int  # region entered through this door
    frm: int  # region on the other side (-1 = outside landing)
    hinge: int  # -1 hinge at a, +1 hinge at b
    leaf: Box | None = None


@dataclass
class Apartment:
    name: str
    w: float
    d: float
    fp: Floorplan
    doors: list[Door]
    hall: int = 0

    @property
    def entrance(self) -> Door:
        return next(d for d in self.doors if d.frm == -1)

    def neighbors(self, k: int) -> list[tuple[int, Door]]:
        out = []
        for d in self.doors:
            if d.frm == k:
                out.append((d.into, d))
            elif d.into == k and d.frm >= 0:
                out.append((d.frm, d))
        return out

    def to_dict(self) -> dict:
        boxes = [[*b, "wall"] for b in self.fp.walls]
        boxes += [[*b, "door"] for b in self.fp.doors]
        boxes += [[*b, "crate"] for b in self.fp.furniture]
        return {
            "name": self.name,
            "bounds": list(self.fp.bounds),
            "boxes": [[round(v, 3) if isinstance(v, float) else v for v in b] for b in boxes],
            "labels": [
                {"name": n, "x": (r[0] + r[2]) / 2, "y": (r[1] + r[3]) / 2}
                for n, r in self.fp.regions
            ],
            "entrance": [(self.entrance.a + self.entrance.b) / 2, 0.0],
        }


def _r(rng, lo, hi, step=0.25):
    return float(np.round(rng.uniform(lo, hi) / step) * step)


def _interior(x0, y0, x1, y1) -> Box:
    return (x0 + T / 2, y0 + T / 2, x1 - T / 2, y1 - T / 2)


def _wall_boxes(horizontal: bool, c: float, lo: float, hi: float, gaps) -> list[Box]:
    """Boxes of a wall centreline segment minus door gaps (intervals along the axis)."""
    cuts, out, start = sorted(gaps), [], lo - T / 2
    for g0, g1 in cuts + [(hi + T / 2, hi + T / 2)]:
        if g0 - start > 1e-6:
            out.append(
                (start, c - T / 2, g0, c + T / 2)
                if horizontal
                else (c - T / 2, start, c + T / 2, g0)
            )
        start = g1
    return out


def _leaf(door: Door, rooms: list[Box]) -> Box:
    """Open door leaf (90 deg) on the hinge side, inside the entered room."""
    x0, y0, x1, y1 = rooms[door.into]
    dw = door.b - door.a
    h = door.a if door.hinge < 0 else door.b - LEAF
    if door.side == "bottom":
        return (h, y0, h + LEAF, y0 + dw)
    if door.side == "top":
        return (h, y1 - dw, h + LEAF, y1)
    if door.side == "left":
        return (x0, h, x0 + dw, h + LEAF)
    return (x1 - dw, h, x1, h + LEAF)


def generate_apartment(seed: int = 0) -> Apartment:
    rng = np.random.default_rng(seed)
    W, D = _r(rng, 9.0, 12.0), _r(rng, 8.0, 11.0)
    hw = _r(rng, 1.3, 1.6, 0.05)
    xl = _r(rng, 3.2, W - 3.2 - hw)
    xr = xl + hw
    yh = D - _r(rng, 3.5, 4.5)

    def column(n_max):
        if yh >= 5.6 and n_max > 1 and rng.uniform() < 0.8:
            return [0.0, _r(rng, 2.6, yh - 2.6), yh]
        return [0.0, yh]

    left, right = column(2), column(2)
    split_top = None
    if W >= 9.0:
        if xl - 0.5 > 2.8:
            split_top = _r(rng, 2.8, xl - 0.5)
        elif W - 2.8 > xr + 0.5:
            split_top = _r(rng, xr + 0.5, W - 2.8)

    cells: list[tuple[str, tuple[float, float, float, float]]] = [("Flur", (xl, 0.0, xr, yh))]
    for a, b in zip(left[:-1], left[1:], strict=True):
        cells.append(("L", (0.0, a, xl, b)))
    for a, b in zip(right[:-1], right[1:], strict=True):
        cells.append(("R", (xr, a, W, b)))
    if split_top is None:
        cells.append(("Wohnzimmer", (0.0, yh, W, D)))
    else:
        big_left = split_top > xr
        living = (0.0, yh, split_top, D) if big_left else (split_top, yh, W, D)
        kitchen = (split_top, yh, W, D) if big_left else (0.0, yh, split_top, D)
        cells += [("Wohnzimmer", living), ("Küche", kitchen)]
    # name the side rooms by size: smallest is the bathroom
    side = sorted(
        [k for k, (n, _) in enumerate(cells) if n in "LR"],
        key=lambda k: (cells[k][1][2] - cells[k][1][0]) * (cells[k][1][3] - cells[k][1][1]),
    )
    names = ["Bad", "Schlafzimmer", "Kinderzimmer", "Arbeitszimmer"]
    for k, n in zip(side, names, strict=False):
        cells[k] = (n, cells[k][1])
    rooms = [_interior(*c) for _, c in cells]

    doors: list[Door] = []
    gaps: dict[tuple[str, float], list[tuple[float, float]]] = {}

    def add_door(name, side, line, a, b, into, frm):
        d = Door(name, side, round(a, 3), round(b, 3), line, into, frm, int(rng.choice([-1, 1])))
        doors.append(d)
        axis = "h" if side in ("bottom", "top") else "v"
        gaps.setdefault((axis, line), []).append((d.a, d.b))

    hall = rooms[0]
    ent_c = (hall[0] + hall[2]) / 2
    add_door("Wohnungstür", "bottom", 0.0, ent_c - 0.45, ent_c + 0.45, 0, -1)
    for k, (n, (_, _, cx1, cy1)) in enumerate(cells):
        if k == 0:
            continue
        ix0, iy0, ix1, iy1 = rooms[k]
        if cy1 <= yh + 1e-9:  # side room, door in the hallway wall
            feed = rng.choice(["low", "center", "high"])
            a = {"low": iy0 + 0.15, "center": (iy0 + iy1) / 2 - 0.4, "high": iy1 - 0.95}[feed]
            a = min(max(a, 1.3), iy1 - 0.95)  # keep clear of the open entrance door leaf
            side = "right" if cx1 <= xl + 1e-9 else "left"
            line = xl if side == "right" else xr
            add_door(n, side, line, a, a + 0.8, k, 0)
    top = [k for k, (_, c) in enumerate(cells) if c[1] >= yh - 1e-9]
    living = next(k for k in top if cells[k][1][0] <= xl + 1e-9 and cells[k][1][2] >= xr - 1e-9)
    hc = (hall[0] + hall[2]) / 2
    add_door(cells[living][0], "bottom", yh, hc - 0.4, hc + 0.4, living, 0)
    for k in top:
        if k != living:
            iy0, iy1 = rooms[k][1], rooms[k][3]
            side = "left" if cells[k][1][0] >= split_top - 1e-9 else "right"
            a = _r(rng, iy0 + 0.2, iy1 - 1.0, 0.05)
            add_door(cells[k][0], side, split_top, a, a + 0.8, k, living)

    walls: list[Box] = []
    walls += _wall_boxes(True, 0.0, 0.0, W, gaps.get(("h", 0.0), []))
    walls += _wall_boxes(True, D, 0.0, W, [])
    walls += _wall_boxes(False, 0.0, 0.0, D, [])
    walls += _wall_boxes(False, W, 0.0, D, [])
    walls += _wall_boxes(True, yh, 0.0, W, gaps.get(("h", yh), []))
    walls += _wall_boxes(False, xl, 0.0, yh, gaps.get(("v", xl), []))
    walls += _wall_boxes(False, xr, 0.0, yh, gaps.get(("v", xr), []))
    for s in left[1:-1]:
        walls += _wall_boxes(True, s, 0.0, xl, [])
    for s in right[1:-1]:
        walls += _wall_boxes(True, s, xr, W, [])
    if split_top is not None:
        walls += _wall_boxes(False, split_top, yh, D, gaps.get(("v", split_top), []))
    # landing in front of the entrance (stairwell), closed on three sides
    lx0, lx1, ly0 = ent_c - 2.0, ent_c + 2.0, -2.8
    walls += [
        (lx0 - T, ly0 - T, lx1 + T, ly0),
        (lx0 - T, ly0, lx0, -T / 2),
        (lx1, ly0, lx1 + T, -T / 2),
    ]

    leaves = []
    for d in doors:
        d.leaf = _leaf(d, rooms)
        leaves.append(d.leaf)

    furniture: list[Box] = []
    for k, r in enumerate(rooms):
        if k == 0 or rng.uniform() > 0.75:
            continue
        x0, y0, x1, y1 = r
        door_sides = {d.side for d in doors if d.into == k} | {
            {"left": "right", "right": "left", "bottom": "top", "top": "bottom"}[d.side]
            for d in doors
            if d.frm == k
        }
        sides = [s for s in ("bottom", "top", "left", "right") if s not in door_sides]
        if not sides:
            continue
        s = str(rng.choice(sides))
        span = (x1 - x0) if s in ("bottom", "top") else (y1 - y0)
        ln = min(_r(rng, 1.0, 2.0), span - 1.4)
        if ln < 0.8:
            continue
        off = _r(rng, 0.6, span - 0.6 - ln, 0.05)
        dep = 0.6
        box = {
            "bottom": (x0 + off, y0, x0 + off + ln, y0 + dep),
            "top": (x0 + off, y1 - dep, x0 + off + ln, y1),
            "left": (x0, y0 + off, x0 + dep, y0 + off + ln),
            "right": (x1 - dep, y0 + off, x1, y0 + off + ln),
        }[s]
        clear = all(
            box[2] + 0.7 < lf[0]
            or lf[2] + 0.7 < box[0]
            or box[3] + 0.7 < lf[1]
            or lf[3] + 0.7 < box[1]
            for lf in leaves
        )
        if clear:
            furniture.append(tuple(round(v, 3) for v in box))

    fp = Floorplan(
        bounds=(min(-0.3, lx0 - T), ly0 - T, max(W + 0.3, lx1 + T), D + 0.3),
        walls=[tuple(round(v, 3) for v in b) for b in walls],
        doors=leaves,
        furniture=furniture,
        regions=[(n, r) for (n, _), r in zip(cells, rooms, strict=True)],
        walkable=[(-T / 2, -T / 2, W + T / 2, D + T / 2), (lx0, ly0, lx1, 0.0)],
    )
    return Apartment(f"APT{seed}", W, D, fp, doors)
