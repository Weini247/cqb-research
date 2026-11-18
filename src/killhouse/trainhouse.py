"""Training-house generator (v0.4): a generic modular indoor training layout.

A grid of square modules (2.8-3.2 m) with one or two corridor bands between the module rows and
sometimes a corridor column. Neighbouring modules are merged into larger rooms at random. Every
room is linked into a spanning tree from the corridors; links are open doorways or doors, and a
few extra links between rooms create loops, as reconfigurable training buildings often have.
Little furniture: low barriers and the odd tall partition. The layout follows the general idea
of a modular training house; it is not modelled on any real facility.
"""

from __future__ import annotations

import numpy as np

from .apartment import Apartment, Door, T, _interior, _leaf, _r
from .geom import SIGHT_H, Floorplan
from .house import _shared, _side, _walls, all_rooms_reachable
from .room import Box

DOOR_W = 0.85
CORNER = 0.15
CORRIDOR = 1.4


def generate_trainhouse(seed: int = 0, attempts: int = 40, closed_frac: float = 0.0) -> Apartment:
    """Reproducible training house for `seed`; closed_frac as in `generate_house`."""
    for attempt in range(attempts):
        try:
            th = _build(np.random.default_rng([seed, 59, attempt]), seed)
        except RuntimeError:
            continue
        if all_rooms_reachable(th):
            rng_doors = np.random.default_rng([seed, 7])
            for d in th.doors:
                d.closed = bool(
                    closed_frac > 0 and (d.frm == -1 or rng_doors.uniform() < closed_frac)
                )
            return th
    raise RuntimeError(f"no valid training house for seed {seed}")


def _bands(
    rng, n_rooms: int, n_corr: int, m: float
) -> tuple[list[tuple[float, float, bool]], float]:
    """Intervals along one axis: room bands of module size and corridor bands in between."""
    pos = sorted(rng.choice(np.arange(1, n_rooms), size=min(n_corr, n_rooms - 1), replace=False))
    out, x = [], 0.0
    for k in range(n_rooms):
        if k in pos:
            out.append((x, round(x + CORRIDOR, 3), True))
            x = round(x + CORRIDOR, 3)
        out.append((x, round(x + m, 3), False))
        x = round(x + m, 3)
    return out, x


def _build(rng, seed: int) -> Apartment:
    m = _r(rng, 2.8, 3.2, 0.1)
    xs, W = _bands(rng, int(rng.integers(4, 7)), int(rng.random() < 0.5), m)
    ys, D = _bands(rng, int(rng.integers(3, 5)), int(rng.integers(1, 3)), m)
    # corridors: each corridor band is one region; a corridor column is split by the bands
    cells: list[tuple[str, Box]] = []
    corr_rows = [(a, b) for a, b, c in ys if c]
    for k, (a, b) in enumerate(corr_rows):
        cells.append((f"Gang {k + 1}", (0.0, a, W, b)))
    for x0, x1, c in xs:
        if c:
            for y0, y1, cy in ys:
                if not cy:
                    cells.append((f"Gang {len(cells) + 1}", (x0, y0, x1, y1)))
    # rooms: module cells, some merged with a neighbour along the row
    mods = [[(x0, y0, x1, y1) for x0, x1, cx in xs if not cx] for y0, y1, cy in ys if not cy]
    k_room = 0
    for row in mods:
        j = 0
        while j < len(row):
            r = row[j]
            if j + 1 < len(row) and abs(row[j + 1][0] - r[2]) < 1e-6 and rng.random() < 0.3:
                r = (r[0], r[1], row[j + 1][2], r[3])
                j += 1
            k_room += 1
            cells.append((f"Raum {k_room}", r))
            j += 1
    n = len(cells)
    corridors = {i for i, (nm, _) in enumerate(cells) if nm.startswith("Gang")}
    # the entrance opens into the bottom corridor, or into the room it reaches through
    entry = min((i for i in corridors), key=lambda i: cells[i][1][1])
    if cells[entry][1][1] > 1e-6:
        entry = min(
            (i for i in range(n) if cells[i][1][1] < 1e-6 and i not in corridors),
            key=lambda i: abs((cells[i][1][0] + cells[i][1][2]) / 2 - W / 2),
        )
    adj = {
        (i, j): s
        for i in range(n)
        for j in range(i + 1, n)
        if (s := _shared(cells[i][1], cells[j][1])) and s[3] - s[2] >= DOOR_W + T + 2 * CORNER
    }

    def shared(i, j):
        return adj.get((min(i, j), max(i, j)))

    # spanning tree from the entrance, corridors first
    tree, seen, todo = [], {entry}, [entry]
    while todo:
        i = todo.pop(0)
        for j in sorted(
            (j for j in range(n) if j not in seen and shared(i, j)),
            key=lambda j: (j not in corridors, rng.random()),
        ):
            seen.add(j)
            tree.append((i, j))
            todo.insert(0 if j in corridors else len(todo), j)
    if len(seen) < n:
        raise RuntimeError("disconnected layout")
    tree_set = {(min(a, b), max(a, b)) for a, b in tree}
    extra = [(i, j) for (i, j) in adj if (i, j) not in tree_set and rng.random() < 0.3]

    gaps: dict[tuple[str, float], list[tuple[float, float]]] = {}
    doors: list[Door] = []

    def link(i: int, j: int) -> None:
        axis, line, lo, hi = shared(i, j)
        key = (axis, round(line, 6))
        for _ in range(12):
            a = _r(rng, lo + T / 2 + CORNER, hi - T / 2 - CORNER - DOOR_W, 0.05)
            if all(a + DOOR_W + 0.5 < u0 or u1 + 0.5 < a for u0, u1 in gaps.get(key, [])):
                break
        else:
            raise RuntimeError("doorways too close")
        gaps.setdefault(key, []).append((round(a, 3), round(a + DOOR_W, 3)))
        # a door (never opening into a corridor, its leaf would block it), else an open doorway
        if j not in corridors and rng.random() < 0.5:
            side = _side(cells[j][1], cells[i][1], axis)
            doors.append(
                Door(
                    cells[j][0],
                    side,
                    round(a, 3),
                    round(a + DOOR_W, 3),
                    round(line, 6),
                    j,
                    i,
                    int(rng.choice([-1, 1])),
                )
            )

    for i, j in tree + extra:
        link(i, j)
    ex0, _, ex1, _ = cells[entry][1]
    # entrance as close to the middle of the front as the entry room or corridor allows
    ent_c = round(float(np.clip(W / 2 + _r(rng, -1.5, 1.5, 0.05), ex0 + 0.8, ex1 - 0.8)), 3)
    doors.insert(
        0,
        Door("Eingang", "bottom", round(ent_c - 0.5, 3), round(ent_c + 0.5, 3), 0.0, entry, -1, -1),
    )
    gaps.setdefault(("h", 0.0), []).append((doors[0].a, doors[0].b))
    rooms = [_interior(*c) for _, c in cells]
    for d in doors:
        d.leaf = _leaf(d, rooms)
    walls = _walls([c for _, c in cells], gaps)
    lx0, lx1, ly0 = ent_c - 2.5, ent_c + 2.5, -3.5
    walls += [
        (lx0 - T, ly0 - T, lx1 + T, ly0),
        (lx0 - T, ly0, lx0, -T / 2),
        (lx1, ly0, lx1 + T, -T / 2),
    ]
    items = _furnish(rng, cells, rooms, doors, gaps, corridors)
    fp = Floorplan(
        bounds=(min(-0.3, lx0 - T), ly0 - T, max(W + 0.3, lx1 + T), D + 0.3),
        walls=[tuple(round(v, 3) for v in b) for b in walls],
        doors=[d.leaf for d in doors],
        furniture=[b for _, b, h in items if h >= SIGHT_H],
        low=[b for _, b, h in items if h < SIGHT_H],
        items=items,
        regions=[(nm, r) for (nm, _), r in zip(cells, rooms, strict=True)],
        walkable=[(-T / 2, -T / 2, W + T / 2, D + T / 2), (lx0, ly0, lx1, 0.0)],
    )
    return Apartment(f"TRAIN{seed}", W, D, fp, doors, hall=entry, style="trainhouse")


def _furnish(rng, cells, rooms, doors, gaps, corridors) -> list[tuple[str, Box, float]]:
    """Sparse: a low barrier in some rooms, a tall partition in some large rooms."""
    keep = [tuple(d.leaf) for d in doors]
    for (axis, c), segs in gaps.items():
        for a, b in segs:
            keep.append((a, c - 1.2, b, c + 1.2) if axis == "h" else (c - 1.2, a, c + 1.2, b))
    out: list[tuple[str, Box, float]] = []
    for k, (x0, y0, x1, y1) in enumerate(rooms):
        if k in corridors:
            continue
        options = [("barrier", 1.2, 0.5, 0.9)] if rng.random() < 0.45 else []
        if (x1 - x0) > 4.5 and rng.random() < 0.6:
            options.append(("partition", 1.6, 0.12, 2.0))
        for kind, w, d, h in options:
            for _ in range(15):
                vertical = rng.random() < 0.5
                bw, bd = (d, w) if vertical else (w, d)
                if x1 - x0 < bw + 1.61 or y1 - y0 < bd + 1.61:
                    break
                cx, cy = (
                    _r(rng, x0 + 0.8 + bw / 2, x1 - 0.8 - bw / 2),
                    _r(rng, y0 + 0.8 + bd / 2, y1 - 0.8 - bd / 2),
                )
                b = (cx - bw / 2, cy - bd / 2, cx + bw / 2, cy + bd / 2)
                if all(
                    b[2] + 0.6 < o[0] or o[2] + 0.6 < b[0] or b[3] + 0.6 < o[1] or o[3] + 0.6 < b[1]
                    for o in keep + [it[1] for it in out]
                ):
                    out.append((kind, tuple(round(v, 3) for v in b), h))
                    break
    return out
