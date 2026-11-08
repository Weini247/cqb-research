"""House generator (v0.3-d): larger single-floor buildings with 8-15 rooms.

Topology first: a hallway layout (`spine`: one long hallway with rooms on both sides and rooms at
the far end; `tee`: an entry hall leading to a cross corridor) is cut into rectangular rooms. A
spanning tree over the room adjacency graph, rooted at the hallway, gives every room a door;
a few extra doors and wide openings add loops and open areas. Walls are derived from the room
rectangles, so shared walls exist once. The result is an `Apartment`, so the clearing model,
`sim2` and the viewer use it unchanged.
"""

from __future__ import annotations

import numpy as np

from .apartment import LEAF, Apartment, Door, T, _interior, _leaf, _r
from .geom import Floorplan, Grid, reachable
from .room import Box

DOOR_W = 0.85
CORNER = 0.15  # m between a door and the end of its wall
MIN_OVERLAP = DOOR_W + 2 * (0.1 + CORNER)  # shared wall length needed for a door (m)
NAMES = [
    "Schlafzimmer",
    "Kinderzimmer",
    "Arbeitszimmer",
    "Gästezimmer",
    "Esszimmer",
    "Hauswirtschaft",
    "Abstellraum",
    "Kinderzimmer 2",
    "Ankleide",
    "Hobbyraum",
]


def _split(rng, lo: float, hi: float, n: int, min_len: float = 2.6) -> list[float]:
    """Cut [lo, hi] into n parts of at least min_len (fewer if it does not fit)."""
    n = max(1, min(n, int((hi - lo) // min_len)))
    cuts = [lo]
    for k in range(1, n):
        rest = n - k
        a = cuts[-1] + min_len
        b = hi - rest * min_len
        mid = cuts[-1] + (hi - cuts[-1]) / (rest + 1)
        cuts.append(float(np.clip(_r(rng, mid - 0.6, mid + 0.6), a, b)))
    return cuts + [hi]


def _layout(rng, kind: str):
    """Room rectangles on wall centrelines; index 0 is the hallway the entrance opens into."""
    if kind == "spine":
        W, D = _r(rng, 12.0, 16.0), _r(rng, 13.0, 17.0)
        hw = _r(rng, 1.4, 1.8, 0.05)
        xl = _r(rng, (W - hw) / 2 - 1.5, (W - hw) / 2 + 1.5)
        xr = xl + hw
        yh = D - _r(rng, 4.0, 5.0)
        cells = [("Flur", (xl, 0.0, xr, yh))]
        for x0, x1, n in ((0.0, xl, int(rng.integers(3, 6))), (xr, W, int(rng.integers(3, 6)))):
            ys = _split(rng, 0.0, yh, n)
            cells += [("", (x0, a, x1, b)) for a, b in zip(ys[:-1], ys[1:], strict=True)]
        xs = _split(rng, 0.0, W, int(rng.integers(3, 5)), 3.0)
        cells += [("", (a, yh, b, D)) for a, b in zip(xs[:-1], xs[1:], strict=True)]
        return W, D, cells
    # tee: entry hall up to a cross corridor, rooms below on both sides and above in a row
    W, D = _r(rng, 15.0, 19.0), _r(rng, 11.0, 14.0)
    hw = _r(rng, 1.4, 1.7, 0.05)
    xl = _r(rng, W / 2 - 2.0, W / 2 + 1.0)
    xr = xl + hw
    yc = _r(rng, 4.6, 5.6)
    yc1 = yc + hw
    cells = [("Diele", (xl, 0.0, xr, yc)), ("Flur", (0.0, yc, W, yc1))]
    for x0, x1 in ((0.0, xl), (xr, W)):
        xs = _split(rng, x0, x1, int(rng.integers(2, 4)), 2.6)
        cells += [("", (a, 0.0, b, yc)) for a, b in zip(xs[:-1], xs[1:], strict=True)]
    xs = _split(rng, 0.0, W, int(rng.integers(4, 7)), 2.8)
    cells += [("", (a, yc1, b, D)) for a, b in zip(xs[:-1], xs[1:], strict=True)]
    return W, D, cells


def _shared(a: Box, b: Box) -> tuple[str, float, float, float] | None:
    """Shared wall of two rectangles: (axis, line, lo, hi) or None."""
    if abs(a[2] - b[0]) < 1e-6 or abs(b[2] - a[0]) < 1e-6:
        line = a[2] if abs(a[2] - b[0]) < 1e-6 else a[0]
        lo, hi = max(a[1], b[1]), min(a[3], b[3])
        return ("v", line, lo, hi) if hi - lo > 1e-6 else None
    if abs(a[3] - b[1]) < 1e-6 or abs(b[3] - a[1]) < 1e-6:
        line = a[3] if abs(a[3] - b[1]) < 1e-6 else a[1]
        lo, hi = max(a[0], b[0]), min(a[2], b[2])
        return ("h", line, lo, hi) if hi - lo > 1e-6 else None
    return None


def _side(into: Box, frm: Box, axis: str) -> str:
    """Wall of the entered room the door sits in."""
    if axis == "v":
        return "left" if abs(into[0] - frm[2]) < 1e-6 else "right"
    return "bottom" if abs(into[1] - frm[3]) < 1e-6 else "top"


def _merge(segs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for lo, hi in sorted(segs):
        if out and lo <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(a, b) for a, b in out]


def _walls(cells: list[Box], gaps: dict) -> list[Box]:
    """Wall boxes from room rectangles: every edge once, minus door and opening gaps."""
    lines: dict[tuple[str, float], list[tuple[float, float]]] = {}
    for x0, y0, x1, y1 in cells:
        for key, seg in (
            (("h", y0), (x0, x1)),
            (("h", y1), (x0, x1)),
            (("v", x0), (y0, y1)),
            (("v", x1), (y0, y1)),
        ):
            lines.setdefault((key[0], round(key[1], 6)), []).append(seg)
    out = []
    for (axis, c), segs in lines.items():
        for lo, hi in _merge(segs):
            start = lo - T / 2
            cuts = sorted(
                g for g in gaps.get((axis, c), []) if lo - 1e-6 <= g[0] and g[1] <= hi + 1e-6
            )
            for g0, g1 in cuts + [(hi + T / 2, hi + T / 2)]:
                if g0 - start > 1e-6:
                    out.append(
                        (start, c - T / 2, g0, c + T / 2)
                        if axis == "h"
                        else (c - T / 2, start, c + T / 2, g0)
                    )
                start = g1
    return out


def generate_house(seed: int = 0, kind: str | None = None, attempts: int = 30) -> Apartment:
    """Reproducible house for `seed`. Every room must be reachable from the entrance for a body;
    a layout that fails (a leaf or a cupboard in the way) is drawn again from a derived seed."""
    kind = kind or ("spine", "tee")[seed % 2]
    for attempt in range(attempts):
        try:
            house = _build(np.random.default_rng([seed, 31, attempt]), seed, kind)
        except RuntimeError:
            continue
        if all_rooms_reachable(house):
            return house
    raise RuntimeError(f"no valid house for seed {seed}")


def all_rooms_reachable(ap: Apartment) -> bool:
    g = Grid(ap.fp)
    d = ap.entrance
    outside = np.array([(d.a + d.b) / 2, -1.0])
    ok = reachable(g, outside)
    return all(((g.region == k) & ok).any() for k in range(len(ap.fp.regions)))


def _build(rng, seed: int, kind: str) -> Apartment:
    W, D, cells = _layout(rng, kind)
    rooms = [_interior(*c) for _, c in cells]
    n = len(cells)
    hallways = {k for k, (nm, _) in enumerate(cells) if nm in ("Flur", "Diele")}
    adj = {
        (i, j): s
        for i in range(n)
        for j in range(n)
        if i < j and (s := _shared(cells[i][1], cells[j][1])) and s[3] - s[2] >= MIN_OVERLAP
    }

    def shared(i, j):
        return adj.get((min(i, j), max(i, j)))

    # spanning tree from the entrance hallway; hallways first, then the larger rooms
    tree, seen, frontier = [], {0}, [0]
    while frontier:
        i = frontier.pop(0)
        nbrs = [j for j in range(n) if j not in seen and shared(i, j)]
        nbrs.sort(
            key=lambda j: (
                j not in hallways,
                -(rooms[j][2] - rooms[j][0]) * (rooms[j][3] - rooms[j][1]),
            )
        )
        for j in nbrs:
            if j in seen:
                continue
            seen.add(j)
            tree.append((i, j))
            frontier.insert(0 if j in hallways else len(frontier), j)
    if len(seen) < n:  # unreachable fragments are merged away by dropping them
        keep = sorted(seen)
        remap = {k: i for i, k in enumerate(keep)}
        cells = [cells[k] for k in keep]
        rooms = [rooms[k] for k in keep]
        tree = [(remap[a], remap[b]) for a, b in tree]
        hallways = {remap[k] for k in hallways if k in remap}
        n = len(cells)
        adj = {
            (i, j): s
            for i in range(n)
            for j in range(n)
            if i < j and (s := _shared(cells[i][1], cells[j][1])) and s[3] - s[2] >= MIN_OVERLAP
        }

    # names: the largest non-hallway room near the far end is the living room, the smallest the
    # bathroom, then kitchen, then the list
    others = [k for k in range(n) if k not in hallways]
    area = {k: (rooms[k][2] - rooms[k][0]) * (rooms[k][3] - rooms[k][1]) for k in others}
    names = {}
    living = max(others, key=lambda k: (area[k], rooms[k][3]))
    names[living] = "Wohnzimmer"
    rest = sorted((k for k in others if k != living), key=lambda k: area[k])
    if rest:
        names[rest[0]] = "Bad"
    if len(rest) > 2:
        names[rest[1]] = "WC"
    pool = iter(NAMES)
    for k in rest[2:] if len(rest) > 2 else rest[1:]:
        names[k] = (
            "Küche" if "Küche" not in names.values() and area[k] > 9 else next(pool, f"Raum {k}")
        )
    cells = [(names.get(k, nm), c) for k, (nm, c) in enumerate(cells)]

    doors: list[Door] = []
    gaps: dict[tuple[str, float], list[tuple[float, float]]] = {}
    used: dict[tuple[str, float], list[tuple[float, float]]] = {}

    def place(i_from: int, j_into: int, width: float = DOOR_W, opening: bool = False) -> bool:
        axis, line, lo, hi = shared(i_from, j_into)
        key = (axis, round(line, 6))
        # keep clear of corners and other doors on the same wall line
        lo_ok, hi_ok = lo + T / 2 + CORNER, hi - T / 2 - CORNER - width
        if hi_ok < lo_ok:
            return False
        for _ in range(12):
            a = _r(rng, lo_ok, hi_ok, 0.05)
            if all(a + width + 0.6 < u0 or u1 + 0.6 < a for u0, u1 in used.get(key, [])):
                break
        else:
            return False
        used.setdefault(key, []).append((a, a + width))
        gaps.setdefault(key, []).append((round(a, 3), round(a + width, 3)))
        if not opening:
            side = _side(cells[j_into][1], cells[i_from][1], axis)
            doors.append(
                Door(
                    cells[j_into][0],
                    side,
                    round(a, 3),
                    round(a + width, 3),
                    round(line, 6),
                    j_into,
                    i_from,
                    int(rng.choice([-1, 1])),
                )
            )
        return True

    for i, j in tree:
        # between two hallways an open passage: a door leaf would stand across the corridor
        both_halls = i in hallways and j in hallways
        if not place(i, j, width=DOOR_W, opening=both_halls):
            raise RuntimeError(f"no room for a door between {cells[i][0]} and {cells[j][0]}")
    tree_set = {(min(a, b), max(a, b)) for a, b in tree}
    for (i, j), _s in adj.items():
        if (i, j) in tree_set or i in hallways or j in hallways:
            continue
        if {names.get(i), names.get(j)} >= {"Wohnzimmer"} and rng.uniform() < 0.6:
            place(i, j, width=_r(rng, 1.8, 2.6), opening=True)  # open plan
        elif rng.uniform() < 0.2:
            place(i, j)  # loop: a second way between two rooms

    # entrance in the bottom wall of the first hallway
    x0, _, x1, _ = cells[0][1]
    ent_c = (x0 + x1) / 2
    entrance = Door(
        "Haustür", "bottom", round(ent_c - 0.5, 3), round(ent_c + 0.5, 3), 0.0, 0, -1, -1
    )
    doors.insert(0, entrance)
    gaps.setdefault(("h", 0.0), []).append((entrance.a, entrance.b))

    walls = _walls([c for _, c in cells], gaps)
    lx0, lx1, ly0 = ent_c - 2.2, ent_c + 2.2, -3.0
    walls += [
        (lx0 - T, ly0 - T, lx1 + T, ly0),
        (lx0 - T, ly0, lx0, -T / 2),
        (lx1, ly0, lx1 + T, -T / 2),
    ]

    leaves = []
    for d in doors:
        d.leaf = _leaf(d, rooms)
        leaves.append(d.leaf)
    furniture = _furnish(rng, rooms, doors, leaves, hallways, gaps)
    fp = Floorplan(
        bounds=(min(-0.3, lx0 - T), ly0 - T, max(W + 0.3, lx1 + T), D + 0.3),
        walls=[tuple(round(v, 3) for v in b) for b in walls],
        doors=leaves,
        furniture=furniture,
        regions=[(nm, r) for (nm, _), r in zip(cells, rooms, strict=True)],
        walkable=[(-T / 2, -T / 2, W + T / 2, D + T / 2), (lx0, ly0, lx1, 0.0)],
    )
    return Apartment(f"HAUS{seed}", W, D, fp, doors, hall=0)


def _furnish(rng, rooms, doors, leaves, hallways, gaps) -> list[Box]:
    """Wall furniture (cupboards, beds, sofas) and in large rooms a free-standing table; nothing
    in front of a door, opening or leaf."""
    keep_out = [tuple(lf) for lf in leaves]
    for (axis, c), segs in gaps.items():
        for a, b in segs:
            keep_out.append((a, c - 1.0, b, c + 1.0) if axis == "h" else (c - 1.0, a, c + 1.0, b))
    out: list[Box] = []

    def free(b: Box, margin: float) -> bool:
        return all(
            b[2] + margin < k[0]
            or k[2] + margin < b[0]
            or b[3] + margin < k[1]
            or k[3] + margin < b[1]
            for k in keep_out + out
        )

    for k, (x0, y0, x1, y1) in enumerate(rooms):
        if k in hallways:
            continue
        for _ in range(int(rng.integers(1, 3))):
            s = str(rng.choice(["bottom", "top", "left", "right"]))
            span = (x1 - x0) if s in ("bottom", "top") else (y1 - y0)
            ln = min(_r(rng, 1.0, 2.2), span - 1.2)
            if ln < 0.8:
                continue
            off = _r(rng, 0.5, span - 0.5 - ln, 0.05)
            dep = _r(rng, 0.5, 0.9, 0.05)
            box = {
                "bottom": (x0 + off, y0, x0 + off + ln, y0 + dep),
                "top": (x0 + off, y1 - dep, x0 + off + ln, y1),
                "left": (x0, y0 + off, x0 + dep, y0 + off + ln),
                "right": (x1 - dep, y0 + off, x1, y0 + off + ln),
            }[s]
            if free(box, 0.5):
                out.append(tuple(round(v, 3) for v in box))
        if x1 - x0 > 3.6 and y1 - y0 > 3.6 and rng.uniform() < 0.6:
            cx, cy = _r(rng, x0 + 1.6, x1 - 1.6), _r(rng, y0 + 1.6, y1 - 1.6)
            w, h = _r(rng, 0.8, 1.6), _r(rng, 0.7, 1.0)
            box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if free(box, 0.9):
                out.append(tuple(round(v, 3) for v in box))
    return out


__all__ = ["generate_house", "LEAF"]
