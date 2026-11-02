"""Procedural building generator.

Grid of 0.5 m cells (idea inspired by BSP floorplans, independent implementation).
Binary space partition into rooms; the upper split levels insert 2 m corridors.
Doors (1 m = 2 cells) connect rooms via a random spanning tree plus every
room-corridor adjacency plus a few extra loops. Several entrances on the outer wall.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

CELL = 0.5
WALL, FLOOR = 1, 0


@dataclass
class Room:
    id: int
    x0: int  # interior cell bounds, inclusive
    y0: int
    x1: int
    y1: int
    kind: str  # "room" | "corridor"

    @property
    def w(self) -> int:
        return self.x1 - self.x0 + 1

    @property
    def h(self) -> int:
        return self.y1 - self.y0 + 1

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class Door:
    a: int  # room id (or -1 for outside)
    b: int
    cells: list[tuple[int, int]]
    vertical: bool  # True: door in a vertical wall (passage along x)


@dataclass
class BuildingParams:
    width_m: float = 30.0
    height_m: float = 40.0
    min_room_cells: int = 8  # 4 m
    corridor_cells: int = 4  # 2 m
    corridor_depth: int = 2  # split levels that get a corridor
    n_entrances: int = 3
    extra_loops: float = 0.15
    seed: int = 0


@dataclass
class Building:
    params: BuildingParams
    w: int
    h: int
    grid: list[list[int]]
    rooms: list[Room] = field(default_factory=list)
    doors: list[Door] = field(default_factory=list)
    room_of: list[list[int]] = field(default_factory=list)

    def is_floor(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h and self.grid[y][x] == FLOOR

    def neighbors(self, rid: int) -> list[int]:
        out = []
        for d in self.doors:
            if d.a == rid and d.b >= 0:
                out.append(d.b)
            elif d.b == rid and d.a >= 0:
                out.append(d.a)
        return out

    @property
    def entrances(self) -> list[Door]:
        return [d for d in self.doors if d.a == -1]


def generate(params: BuildingParams | None = None) -> Building:
    p = params or BuildingParams()
    rng = random.Random(p.seed)
    w, h = int(p.width_m / CELL), int(p.height_m / CELL)
    grid = [[WALL] * w for _ in range(h)]
    rects: list[tuple[int, int, int, int, str]] = []

    def split(x0: int, y0: int, x1: int, y1: int, depth: int) -> None:
        # rect given by wall lines x0..x1, y0..y1 (walls on the border)
        iw, ih = x1 - x0 - 1, y1 - y0 - 1
        m = p.min_room_cells
        corridor = depth < p.corridor_depth
        extra = p.corridor_cells + 1 if corridor else 0
        can_v = iw >= 2 * m + 1 + extra
        can_h = ih >= 2 * m + 1 + extra
        big = iw * ih > (m * 2.2) ** 2
        if not (can_v or can_h) or (not big and rng.random() < 0.3 and depth > 2):
            rects.append((x0 + 1, y0 + 1, x1 - 1, y1 - 1, "room"))
            return
        vertical = (
            can_v if not can_h else (can_v and (iw > ih or (iw == ih and rng.random() < 0.5)))
        )
        lo, hi = (x0, x1) if vertical else (y0, y1)
        s = rng.randint(lo + m + 1, hi - m - 1 - extra)
        if corridor:
            s2 = s + p.corridor_cells + 1
            if vertical:
                split(x0, y0, s, y1, depth + 1)
                rects.append((s + 1, y0 + 1, s2 - 1, y1 - 1, "corridor"))
                split(s2, y0, x1, y1, depth + 1)
            else:
                split(x0, y0, x1, s, depth + 1)
                rects.append((x0 + 1, s + 1, x1 - 1, s2 - 1, "corridor"))
                split(x0, s2, x1, y1, depth + 1)
        elif vertical:
            split(x0, y0, s, y1, depth + 1)
            split(s, y0, x1, y1, depth + 1)
        else:
            split(x0, y0, x1, s, depth + 1)
            split(x0, s, x1, y1, depth + 1)

    split(0, 0, w - 1, h - 1, 0)

    rooms: list[Room] = []
    room_of = [[-1] * w for _ in range(h)]
    for i, (a, b, c, d, kind) in enumerate(rects):
        rooms.append(Room(i, a, b, c, d, kind))
        for y in range(b, d + 1):
            for x in range(a, c + 1):
                grid[y][x] = FLOOR
                room_of[y][x] = i

    # door candidates: wall cells with distinct rooms on opposite sides
    cand: dict[tuple[int, int, bool], list[tuple[int, int]]] = {}
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if grid[y][x] != WALL:
                continue
            for vert, (lft, r) in (
                (True, (room_of[y][x - 1], room_of[y][x + 1])),
                (False, (room_of[y - 1][x], room_of[y + 1][x])),
            ):
                if lft >= 0 and r >= 0 and lft != r:
                    key = (min(lft, r), max(lft, r), vert)
                    cand.setdefault(key, []).append((x, y))

    def door_cells(cells: list[tuple[int, int]], vert: bool) -> list[tuple[int, int]] | None:
        # longest contiguous run, pick 2 cells away from corners
        cells = sorted(cells, key=lambda c: c[1] if vert else c[0])
        runs, cur = [], [cells[0]]
        for c in cells[1:]:
            prev = cur[-1]
            if (vert and c[1] == prev[1] + 1) or (not vert and c[0] == prev[0] + 1):
                cur.append(c)
            else:
                runs.append(cur)
                cur = [c]
        runs.append(cur)
        run = max(runs, key=len)
        if len(run) < 4:
            return None
        i = rng.randint(1, len(run) - 3)
        return run[i : i + 2]

    pairs = []
    for (a, b, vert), cells in cand.items():
        dc = door_cells(cells, vert)
        if dc:
            pairs.append((a, b, vert, dc))
    rng.shuffle(pairs)

    parent = list(range(len(rooms)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    doors: list[Door] = []
    for a, b, vert, dc in pairs:
        corridor_link = rooms[a].kind == "corridor" or rooms[b].kind == "corridor"
        joined = find(a) != find(b)
        if joined or corridor_link or rng.random() < p.extra_loops:
            parent[find(a)] = find(b)
            doors.append(Door(a, b, dc, vert))

    # entrances: outer-wall openings, prefer corridors, spread out
    outer: list[tuple[int, list[tuple[int, int]], bool]] = []
    for r in rooms:
        if r.y0 == 1 and r.w >= 4:
            outer.append((r.id, [(r.x0 + r.w // 2 - 1, 0), (r.x0 + r.w // 2, 0)], False))
        if r.y1 == h - 2 and r.w >= 4:
            outer.append((r.id, [(r.x0 + r.w // 2 - 1, h - 1), (r.x0 + r.w // 2, h - 1)], False))
        if r.x0 == 1 and r.h >= 4:
            outer.append((r.id, [(0, r.y0 + r.h // 2 - 1), (0, r.y0 + r.h // 2)], True))
        if r.x1 == w - 2 and r.h >= 4:
            outer.append((r.id, [(w - 1, r.y0 + r.h // 2 - 1), (w - 1, r.y0 + r.h // 2)], True))
    outer.sort(key=lambda o: (rooms[o[0]].kind != "corridor", rng.random()))
    chosen: list[tuple[int, list[tuple[int, int]], bool]] = []
    for o in outer:
        if len(chosen) >= p.n_entrances:
            break
        cx, cy = o[1][0]
        if all(abs(cx - c[1][0][0]) + abs(cy - c[1][0][1]) > (w + h) / 4 for c in chosen):
            chosen.append(o)
    for o in outer:  # fill up if spacing was too strict
        if len(chosen) >= p.n_entrances:
            break
        if o not in chosen:
            chosen.append(o)
    for rid, cells, vert in chosen:
        doors.append(Door(-1, rid, cells, vert))

    for d in doors:
        for x, y in d.cells:
            grid[y][x] = FLOOR
    return Building(p, w, h, grid, rooms, doors, room_of)


def is_connected(b: Building) -> bool:
    if not b.rooms:
        return False
    seen = {0}
    q = deque([0])
    while q:
        r = q.popleft()
        for n in b.neighbors(r):
            if n not in seen:
                seen.add(n)
                q.append(n)
    return len(seen) == len(b.rooms)
