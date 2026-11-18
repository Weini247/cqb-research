"""Residence generator (v0.4): single-family houses laid out by zones, like an architect would.

Three zones side by side: a private wing (bedrooms on a corridor, a master bedroom with en-suite
bathroom and walk-in closet), a core (entrance hall, hallway, guest WC) and a public wing (living
room, dining room and kitchen joined by wide openings, a utility room). Most houses get a garage
next to the utility room, which makes the footprint L-shaped. Rooms get typed furniture with a
height (`geom.SIGHT_H`: low pieces block bodies but not sight) and windows in exterior walls. A
layout is mirrored at random. Every room is reachable from the entrance; a layout that fails is
drawn again from a derived seed. Inspired by common floorplans in general, not by any specific
plan or picture.
"""

from __future__ import annotations

import numpy as np

from .apartment import Apartment, Door, T, _interior, _leaf, _r
from .geom import SIGHT_H, Floorplan
from .house import _shared, _side, _walls, all_rooms_reachable
from .room import Box

DOOR_W = 0.8
CORNER = 0.15
HALLS = ("Diele", "Flur", "Gang")
# (kind, width along the wall, depth, height) per room type; placed against walls unless "mid"
FURNITURE = {
    "Schlafzimmer": [("bed", 1.6, 2.0, 0.5, "wall"), ("wardrobe", 2.0, 0.6, 2.1, "wall")],
    "Kinderzimmer": [
        ("bed", 0.9, 2.0, 0.5, "wall"),
        ("desk", 1.2, 0.6, 0.75, "wall"),
        ("wardrobe", 1.2, 0.6, 2.0, "wall"),
    ],
    "Arbeitszimmer": [("desk", 1.6, 0.7, 0.75, "wall"), ("shelf", 1.8, 0.4, 2.0, "wall")],
    "Bad": [("bath", 1.7, 0.75, 0.6, "wall"), ("cabinet", 0.8, 0.5, 0.9, "wall")],
    "Bad en suite": [("bath", 1.6, 0.8, 0.6, "wall")],
    "Ankleide": [("shelf", 1.6, 0.5, 2.1, "wall"), ("shelf", 1.6, 0.5, 2.1, "wall")],
    "Wohnzimmer": [
        ("sofa", 2.4, 0.95, 0.85, "wall"),
        ("table", 1.2, 0.6, 0.45, "mid"),
        ("shelf", 2.0, 0.4, 2.0, "wall"),
    ],
    "Esszimmer": [("table", 1.8, 1.0, 0.75, "mid")],
    "Küche": [
        ("counter", 3.0, 0.65, 0.9, "wall"),
        ("fridge", 0.65, 0.65, 2.0, "wall"),
        ("island", 1.8, 0.9, 0.9, "mid"),
    ],
    "Hauswirtschaft": [("shelf", 1.6, 0.5, 2.0, "wall")],
    "Diele": [("wardrobe", 1.2, 0.5, 2.0, "wall")],
    "Garage": [("car", 1.85, 4.5, 1.45, "car"), ("car", 1.85, 4.5, 1.45, "car")],
}


def generate_residence(seed: int = 0, attempts: int = 40, closed_frac: float = 0.0) -> Apartment:
    """Reproducible residence for `seed`; closed_frac as in `generate_house`."""
    for attempt in range(attempts):
        try:
            res = _build(np.random.default_rng([seed, 47, attempt]), seed)
        except RuntimeError:
            continue
        if all_rooms_reachable(res):
            rng_doors = np.random.default_rng([seed, 7])
            for d in res.doors:
                d.closed = bool(
                    closed_frac > 0 and (d.frm == -1 or rng_doors.uniform() < closed_frac)
                )
            return res
    raise RuntimeError(f"no valid residence for seed {seed}")


def _cells(rng) -> tuple[list[tuple[str, Box]], float, float, Box | None]:
    """Zone layout on wall centrelines (canonical orientation: private wing on the left)."""
    wp, wc, wq = _r(rng, 6.2, 7.2), _r(rng, 2.4, 3.0), _r(rng, 7.4, 9.0)
    W, D = wp + wc + wq, _r(rng, 10.5, 13.0)
    cw = _r(rng, 1.35, 1.5, 0.05)  # private corridor
    mh = _r(rng, 4.4, 5.2)
    ym = D - mh
    cells: list[tuple[str, Box]] = [("Diele", (wp, 0.0, wp + wc, _r(rng, 2.6, 3.4)))]
    de = cells[0][1][3]
    wch = _r(rng, 2.0, 2.4)
    cells += [("Flur", (wp, de, wp + wc, D - wch)), ("WC", (wp, D - wch, wp + wc, D))]
    # private wing: corridor along the core, rooms on its left, master suite on top
    cells.append(("Gang", (wp - cw, 0.0, wp, ym)))
    rooms_x1 = wp - cw
    if ym >= 8.6:
        names = ["Kinderzimmer", "Bad", str(rng.choice(["Kinderzimmer 2", "Arbeitszimmer"]))]
        bath = _r(rng, 2.4, 2.8)
        rest = (ym - bath) / 2
        ys = [0.0, rest, rest + bath, ym]
    else:
        names = ["Kinderzimmer", "Bad"] if rng.uniform() < 0.5 else ["Bad", "Kinderzimmer"]
        bath = _r(rng, 2.4, 2.8)
        ys = [0.0, bath, ym] if names[0] == "Bad" else [0.0, ym - bath, ym]
    cells += [(n, (0.0, a, rooms_x1, b)) for n, a, b in zip(names, ys[:-1], ys[1:], strict=True)]
    es = min(_r(rng, 2.4, 2.8), mh - 1.6)
    cells += [
        ("Bad en suite", (0.0, ym, 2.4, ym + es)),
        ("Ankleide", (0.0, ym + es, 2.4, D)),
        ("Schlafzimmer", (2.4, ym, wp, D)),
    ]
    # public wing: living room at the back, dining room and kitchen in front, utility room
    x0 = wp + wc
    yl = D - _r(rng, 4.5, 5.5)
    xk = x0 + _r(rng, 3.0, min(3.8, wq - 3.6))  # kitchen at least 3.6 m wide (island)
    hh = _r(rng, 2.2, 2.6)
    cells += [
        ("Wohnzimmer", (x0, yl, W, D)),
        ("Esszimmer", (x0, 0.0, xk, yl)),
        ("Küche", (xk, hh, W, yl)),
        ("Hauswirtschaft", (xk, 0.0, W, hh)),
    ]
    garage = None
    if rng.uniform() < 0.85:
        garage = (W, 0.0, W + _r(rng, 6.0, 6.6), min(_r(rng, 6.0, 7.0), yl))
        cells.append(("Garage", garage))
    return cells, W, D, garage


def _build(rng, seed: int) -> Apartment:
    cells, W, D, garage = _cells(rng)
    names = [n for n, _ in cells]
    idx = {n: k for k, n in enumerate(names)}
    # connections: (from, into, kind) with kind door / opening; hallway to hallway is open
    links = [
        ("Diele", "Flur", "opening"),
        ("Flur", "Gang", "opening"),
        ("Flur", "WC", "door"),
        ("Gang", "Schlafzimmer", "door"),
        ("Schlafzimmer", "Bad en suite", "door"),
        ("Schlafzimmer", "Ankleide", "opening"),
        ("Flur", "Wohnzimmer", "door"),
        ("Diele", "Esszimmer", "door"),
        ("Wohnzimmer", "Esszimmer", "wide"),
        ("Esszimmer", "Küche", "wide"),
        ("Küche", "Hauswirtschaft", "door"),
    ]
    links += [
        ("Gang", n, "door")
        for n in names
        if n.startswith(("Kinderzimmer", "Arbeitszimmer")) or n == "Bad"
    ]
    if garage is not None:
        links.append(("Hauswirtschaft", "Garage", "door"))
    gaps: dict[tuple[str, float], list[tuple[float, float]]] = {}
    specs = []  # (from, into, axis, line, a, b, hinge)
    for frm, into, kind in links:
        i, j = idx[frm], idx[into]
        sh = _shared(cells[i][1], cells[j][1])
        if sh is None:
            raise RuntimeError(f"{frm} and {into} do not touch")
        axis, line, lo, hi = sh
        width = {"door": DOOR_W, "opening": DOOR_W, "wide": _r(rng, 2.0, 2.8)}[kind]
        width = min(width, hi - lo - T - 2 * CORNER)
        if width < DOOR_W - 1e-6:
            raise RuntimeError(f"no room for a passage between {frm} and {into}")
        key = (axis, round(line, 6))
        for _ in range(12):
            a = _r(rng, lo + T / 2 + CORNER, hi - T / 2 - CORNER - width, 0.05)
            if all(a + width + 0.5 < u0 or u1 + 0.5 < a for u0, u1 in gaps.get(key, [])):
                break
        else:
            raise RuntimeError("doors too close")
        gaps.setdefault(key, []).append((round(a, 3), round(a + width, 3)))
        if kind == "door":
            specs.append((i, j, axis, line, a, a + width, int(rng.choice([-1, 1]))))
    # entrance and windows in exterior walls (not in hallways, WC or garage)
    diele = cells[idx["Diele"]][1]
    ent_c = (diele[0] + diele[2]) / 2
    gaps.setdefault(("h", 0.0), []).append((round(ent_c - 0.5, 3), round(ent_c + 0.5, 3)))
    windows: list[Box] = []
    for n, (x0, y0, x1, y1) in cells:
        if n in HALLS or n in ("WC", "Garage", "Ankleide"):
            continue
        edges = []
        if abs(y0) < 1e-6:
            edges.append(("h", 0.0, x0, x1))
        if abs(y1 - D) < 1e-6:
            edges.append(("h", D, x0, x1))
        if abs(x0) < 1e-6:
            edges.append(("v", 0.0, y0, y1))
        if abs(x1 - W) < 1e-6 and not (garage is not None and y0 < garage[3] - 1e-6):
            edges.append(("v", W, y0, y1))
        for axis, line, lo, hi in edges[:2]:
            width = min(0.8 if n.startswith("Bad") else _r(rng, 1.2, 2.0), hi - lo - 1.2)
            if width < 0.6:
                continue
            a = round((lo + hi) / 2 - width / 2, 3)
            key = (axis, round(line, 6))
            if any(not (a + width + 0.3 < u0 or u1 + 0.3 < a) for u0, u1 in gaps.get(key, [])):
                continue
            gaps.setdefault(key, []).append((a, round(a + width, 3)))
            windows.append(
                (a, line - T / 2, a + width, line + T / 2)
                if axis == "h"
                else (line - T / 2, a, line + T / 2, a + width)
            )
    xmax = garage[2] if garage else W
    lx0, lx1, ly0 = ent_c - 2.0, ent_c + 2.0, -3.0
    mirror = bool(rng.uniform() < 0.5)

    def mx(b: Box) -> Box:
        return (xmax - b[2], b[1], xmax - b[0], b[3]) if mirror else b

    if mirror:
        cells = [(n, mx(c)) for n, c in cells]
        gaps = {
            (axis, round(xmax - line, 6) if axis == "v" else line): [
                ((round(xmax - b, 3), round(xmax - a, 3)) if axis == "h" else (a, b))
                for a, b in segs
            ]
            for (axis, line), segs in gaps.items()
        }
        windows = [mx(w) for w in windows]
        specs = [
            (
                i,
                j,
                axis,
                xmax - line if axis == "v" else line,
                *((xmax - b, xmax - a) if axis == "h" else (a, b)),
                -hinge,
            )
            for i, j, axis, line, a, b, hinge in specs
        ]
        lx0, lx1, ent_c = xmax - lx1, xmax - lx0, xmax - ent_c
    rooms = [_interior(*c) for _, c in cells]
    doors = [
        Door(
            "Haustür",
            "bottom",
            round(ent_c - 0.5, 3),
            round(ent_c + 0.5, 3),
            0.0,
            idx["Diele"],
            -1,
            -1,
        )
    ]
    for i, j, axis, line, a, b, hinge in specs:
        side = _side(cells[j][1], cells[i][1], axis)
        doors.append(Door(cells[j][0], side, round(a, 3), round(b, 3), round(line, 6), j, i, hinge))
    for d in doors:
        d.leaf = _leaf(d, rooms)
    walls = _walls([c for _, c in cells], gaps)
    walls += [
        (lx0 - T, ly0 - T, lx1 + T, ly0),
        (lx0 - T, ly0, lx0, -T / 2),
        (lx1, ly0, lx1 + T, -T / 2),
    ]
    items = _furnish(rng, cells, rooms, doors, gaps, windows)
    # house body and garage are mirrored here; the landing coordinates already are
    walkable = [mx((-T / 2, -T / 2, W + T / 2, D + T / 2))]
    if garage is not None:
        walkable.append(
            mx((garage[0] - T / 2, garage[1] - T / 2, garage[2] + T / 2, garage[3] + T / 2))
        )
    walkable.append((lx0, ly0, lx1, 0.0))
    fp = Floorplan(
        bounds=(min(-0.3, lx0 - T), ly0 - T, max(xmax + 0.3, lx1 + T), D + 0.3),
        walls=[tuple(round(v, 3) for v in b) for b in walls],
        doors=[d.leaf for d in doors],
        furniture=[b for _, b, h in items if h >= SIGHT_H],
        low=[b for _, b, h in items if h < SIGHT_H],
        items=items,
        regions=[(n, r) for (n, _), r in zip(cells, rooms, strict=True)],
        walkable=walkable,
        windows=windows,
    )
    return Apartment(f"VILLA{seed}", xmax, D, fp, doors, hall=idx["Diele"], style="residence")


def _furnish(rng, cells, rooms, doors, gaps, windows) -> list[tuple[str, Box, float]]:
    """Typed furniture per room type: against walls (not in front of a door, opening or window)
    or free-standing; cars in the garage side by side."""
    win = {(round(w[0], 3), round(w[2], 3)) for w in windows} | {
        (round(w[1], 3), round(w[3], 3)) for w in windows
    }
    keep = [tuple(d.leaf) for d in doors]  # door leaves, doors and openings: nothing in front
    for (axis, c), segs in gaps.items():
        for a, b in segs:
            if (round(a, 3), round(b, 3)) not in win:
                keep.append((a, c - 1.0, b, c + 1.0) if axis == "h" else (c - 1.0, a, c + 1.0, b))
    # windows: low pieces (counters, beds, desks) may stand below them, tall ones not
    keep_tall = [(w[0] - 0.5, w[1] - 0.5, w[2] + 0.5, w[3] + 0.5) for w in windows]
    out: list[tuple[str, Box, float]] = []

    def free(b: Box, room: Box, margin: float, h: float) -> bool:
        inside = (
            b[0] >= room[0] - 1e-6
            and b[1] >= room[1] - 1e-6
            and b[2] <= room[2] + 1e-6
            and b[3] <= room[3] + 1e-6
        )
        others = keep + [o[1] for o in out] + (keep_tall if h >= SIGHT_H else [])
        return inside and all(
            b[2] + margin < k[0]
            or k[2] + margin < b[0]
            or b[3] + margin < k[1]
            or k[3] + margin < b[1]
            for k in others
        )

    centers = {n: ((r[0] + r[2]) / 2) for (n, _), r in zip(cells, rooms, strict=True)}

    for (name, _), room in zip(cells, rooms, strict=True):
        spec = FURNITURE.get(name.split(" ")[0] if name.startswith(("Kinderzimmer",)) else name, [])
        x0, y0, x1, y1 = room
        cars = 0
        for kind, w, d, h, where in spec:
            if where == "car":
                # side by side, starting at the wall away from the door to the utility room
                gw, away = x1 - x0, 1 if centers[name] > centers["Hauswirtschaft"] else -1
                if cars and gw < 5.2:
                    continue
                edge = x1 if away > 0 else x0
                cx = edge - away * (0.5 + w / 2 + cars * (w + 0.7))
                b = (cx - w / 2, y0 + 0.4, cx + w / 2, y0 + 0.4 + d)
                if free(b, room, 0.25, h):
                    out.append((kind, tuple(round(v, 3) for v in b), h))
                    cars += 1
                continue
            for _ in range(25):
                if where == "mid":
                    if x1 - x0 < w + 1.8 or y1 - y0 < d + 1.8:
                        break
                    cx, cy = (
                        _r(rng, x0 + 0.9 + w / 2, x1 - 0.9 - w / 2),
                        _r(rng, y0 + 0.9 + d / 2, y1 - 0.9 - d / 2),
                    )
                    b = (cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
                    margin = 0.7
                else:
                    side = str(rng.choice(["bottom", "top", "left", "right"]))
                    span = (x1 - x0) if side in ("bottom", "top") else (y1 - y0)
                    ln = min(w * rng.choice([1.0, 1.0, 0.8, 0.65]), span - 0.4)  # shorter if needed
                    if ln < 0.6:
                        continue
                    off = _r(rng, 0.2, max(0.2, span - 0.2 - ln), 0.05)
                    b = {
                        "bottom": (x0 + off, y0, x0 + off + ln, y0 + d),
                        "top": (x0 + off, y1 - d, x0 + off + ln, y1),
                        "left": (x0, y0 + off, x0 + d, y0 + off + ln),
                        "right": (x1 - d, y0 + off, x1, y0 + off + ln),
                    }[side]
                    margin = 0.35
                if free(b, room, margin, h):
                    out.append((kind, tuple(round(v, 3) for v in b), h))
                    break
    return out
