"""CQB episode simulation: team-level state machine over the building.

Phases per objective room: TRANSIT (move to stack points) -> STACK (hold at door)
-> ENTRY (staggered crisscross entry to points of domination) -> CLEAR (cover corners)
-> next room (DFS over the door graph, always entering from an already cleared room).
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from .building import CELL, FLOOR, Building, Door
from .team import Operator

PAD = 6  # floor cells of open ground around the building
DT = 0.1
FRAME_EVERY = 2  # export every 0.2 s
ENTRY_SPEEDUP = 1.35


@dataclass
class OpState:
    op: Operator
    x: float  # padded cell coords
    y: float
    heading: float = 0.0
    path: list[tuple[int, int]] = field(default_factory=list)
    mode: str = "move"
    look: tuple[float, float] | None = None
    fast: bool = False

    @property
    def arrived(self) -> bool:
        return not self.path


class Sim:
    def __init__(self, b: Building, team: list[Operator]):
        self.b = b
        self.W, self.H = b.w + 2 * PAD, b.h + 2 * PAD
        self.grid = [[FLOOR] * self.W for _ in range(self.H)]
        self.room = [[-2] * self.W for _ in range(self.H)]  # -2 outside, -1 wall/door
        for y in range(b.h):
            for x in range(b.w):
                self.grid[y + PAD][x + PAD] = b.grid[y][x]
                self.room[y + PAD][x + PAD] = b.room_of[y][x]
        self.cleared: set[int] = set()
        ent = b.entrances[0]
        sx, sy = ent.cells[0]
        start = self._outside_side(ent, sx + PAD, sy + PAD, far=PAD - 3)
        self.ops = [OpState(o, start[0] + i % 2, start[1] + i // 2) for i, o in enumerate(team)]
        self.t = 0.0
        self.frames: list[dict] = []
        self.events: list[dict] = []
        self.plan = self._plan(ent)

    # ---------- planning ----------
    def _plan(self, ent: Door) -> list[tuple[int, Door, int]]:
        """DFS order of (room, door, source_room); source -2 = outside."""
        order: list[tuple[int, Door, int]] = [(ent.b, ent, -2)]
        seen = {ent.b}

        def door_between(a: int, c: int) -> Door:
            return next(d for d in self.b.doors if {d.a, d.b} == {a, c})

        def dfs(r: int) -> None:
            nbrs = sorted(self.b.neighbors(r), key=lambda n: self.b.rooms[n].kind != "corridor")
            for n in nbrs:
                if n not in seen:
                    seen.add(n)
                    order.append((n, door_between(r, n), r))
                    dfs(n)

        dfs(ent.b)
        return order

    def _outside_side(self, d: Door, x: int, y: int, far: int = 1) -> tuple[int, int]:
        """Cell `far` steps from door cell (x, y) on the side away from room d.b."""
        dx, dy = (1, 0) if d.vertical else (0, 1)
        for s in (1, -1):
            if self.room[y + dy * s][x + dx * s] == d.b:
                return (x - dx * s * far, y - dy * s * far)
        return (x, y)

    def _stack_cells(self, d: Door, src: int) -> list[tuple[int, int]]:
        cells = sorted((x + PAD, y + PAD) for x, y in d.cells)
        ax, ay = (0, 1) if d.vertical else (1, 0)  # along the wall
        (x0, y0), (x1, y1) = cells[0], cells[-1]
        ox, oy = self._outside_side(d, x0, y0)
        nx, ny = ox - x0, oy - y0  # unit normal pointing to source side
        out = []
        for side, (bx, by) in ((-1, (x0, y0)), (1, (x1, y1))):
            for k in (1, 2):
                found = None
                for depth in (1, 2, 3):
                    for extra in (0, 1, 2):
                        cx = bx + ax * side * (k + extra) + nx * depth
                        cy = by + ay * side * (k + extra) + ny * depth
                        if self._passable(cx, cy, {src}) and (cx, cy) not in out:
                            found = (cx, cy)
                            break
                    if found:
                        break
                out.append(found or (x0 + nx * (k + 1), y0 + ny * (k + 1)))
        return out  # [A1, A2, B1, B2] -> ops 0,1 side A; 2,3 side B

    def _entry_points(self, rid: int, d: Door) -> list[tuple[int, int]]:
        r = self.b.rooms[rid]
        x0, y0, x1, y1 = r.x0 + PAD + 1, r.y0 + PAD + 1, r.x1 + PAD - 1, r.y1 + PAD - 1
        dc = sorted((x + PAD, y + PAD) for x, y in d.cells)
        if d.vertical:
            near_x = x0 if dc[0][0] < x0 else x1
            far_x = round(near_x + (x1 - x0) * 0.6 * (1 if near_x == x0 else -1))
            near_a, near_b = (near_x, y0), (near_x, y1)
            far_a, far_b = (far_x, y0 + (y1 - y0) // 3), (far_x, y1 - (y1 - y0) // 3)
        else:
            near_y = y0 if dc[0][1] < y0 else y1
            far_y = round(near_y + (y1 - y0) * 0.6 * (1 if near_y == y0 else -1))
            near_a, near_b = (x0, near_y), (x1, near_y)
            far_a, far_b = (x0 + (x1 - x0) // 3, far_y), (x1 - (x1 - x0) // 3, far_y)
        # crisscross: op0 (side A) -> near corner B, op2 (side B) -> near corner A
        return [near_b, far_b, near_a, far_a]

    # ---------- movement ----------
    def _passable(self, x: int, y: int, allowed: set[int]) -> bool:
        if not (0 <= x < self.W and 0 <= y < self.H) or self.grid[y][x] != FLOOR:
            return False
        r = self.room[y][x]
        return r < 0 or r in allowed

    def _astar(self, s: tuple[int, int], g: tuple[int, int], allowed: set[int]):
        if s == g:
            return []
        openq = [(0.0, s)]
        came: dict[tuple[int, int], tuple[int, int]] = {}
        cost = {s: 0.0}
        while openq:
            _, c = heapq.heappop(openq)
            if c == g:
                path = [c]
                while path[-1] in came:
                    path.append(came[path[-1]])
                return path[::-1][1:]
            cx, cy = c
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not dx and not dy:
                        continue
                    n = (cx + dx, cy + dy)
                    if not self._passable(*n, allowed):
                        continue
                    if (
                        dx
                        and dy
                        and not (
                            self._passable(cx + dx, cy, allowed)
                            and self._passable(cx, cy + dy, allowed)
                        )
                    ):
                        continue
                    nc = cost[c] + (1.4142 if dx and dy else 1.0)
                    if nc < cost.get(n, 1e18):
                        cost[n] = nc
                        came[n] = c
                        heapq.heappush(openq, (nc + math.dist(n, g), n))
        return None

    def _send(self, o: OpState, goal: tuple[int, int], allowed: set[int], fast=False) -> None:
        start = (round(o.x), round(o.y))
        p = self._astar(start, goal, allowed | self.cleared)
        o.path = p if p is not None else []
        o.fast = fast

    def _step_ops(self) -> None:
        for o in self.ops:
            if o.path:
                spd = o.op.speed_mps * (ENTRY_SPEEDUP if o.fast else 1.0) / CELL * DT
                while spd > 0 and o.path:
                    tx, ty = o.path[0]
                    dx, dy = tx - o.x, ty - o.y
                    dist = math.hypot(dx, dy)
                    if dist > 1e-9:
                        o.heading = math.atan2(dy, dx)
                    if dist <= spd:
                        o.x, o.y = tx, ty
                        o.path.pop(0)
                        spd -= dist
                    else:
                        o.x += dx / dist * spd
                        o.y += dy / dist * spd
                        spd = 0
            elif o.look:
                o.heading = math.atan2(o.look[1] - o.y, o.look[0] - o.x)

    # ---------- state machine ----------
    def run(self, max_t: float = 3600.0) -> None:
        tick = 0
        for rid, door, src in self.plan:
            room = self.b.rooms[rid]
            corridor = room.kind == "corridor"
            door_c = tuple(sum(c) / 2 + PAD for c in zip(*door.cells, strict=True))
            rc = (room.center[0] + PAD, room.center[1] + PAD)
            small = room.w < 6 or room.h < 6
            allowed_src = {src} if src >= 0 else set()

            phase = "transit"
            stacks = self._stack_cells(door, src)
            for o, s in zip(self.ops, stacks, strict=True):
                self._send(o, s, allowed_src)
                o.mode, o.look = "move", door_c
            self._event("transit", rid)
            timer = 0.0
            entries = self._entry_points(rid, door)
            entry_order = [0, 2] if small else [0, 2, 1, 3]
            sent: set[int] = set()
            while True:
                if self.t > max_t:
                    raise RuntimeError("episode timeout")
                if phase == "transit" and all(o.arrived for o in self.ops):
                    phase, timer = "stack", (0.4 if corridor else 1.2)
                    for o in self.ops:
                        o.mode = "stack"
                    self._event("stack", rid)
                elif phase == "stack":
                    timer -= DT
                    if timer <= 0:
                        phase, timer = "entry", 0.0
                        self._event("entry", rid)
                elif phase == "entry":
                    gap = 0.35 if corridor else 0.7
                    for k, i in enumerate(entry_order):
                        if i not in sent and timer >= k * gap:
                            sent.add(i)
                            self._send(self.ops[i], entries[i], {rid}, fast=True)
                            self.ops[i].mode, self.ops[i].look = "entry", rc
                    timer += DT
                    if len(sent) == len(entry_order) and all(
                        self.ops[i].arrived for i in entry_order
                    ):
                        phase, timer = "clear", (0.5 if corridor else 1.5)
                        for i, o in enumerate(self.ops):
                            o.mode = "cover" if i in entry_order else "hold"
                        self._event("clear", rid)
                elif phase == "clear":
                    timer -= DT
                    if timer <= 0:
                        self.cleared.add(rid)
                        self._event("cleared", rid)
                        break
                self._step_ops()
                self.t += DT
                tick += 1
                if tick % FRAME_EVERY == 0:
                    self._frame(phase, rid)
        self._frame("done", -1)
        self._event("done", -1)

    def _event(self, kind: str, rid: int) -> None:
        self.events.append({"t": round(self.t, 2), "kind": kind, "room": rid})

    def _frame(self, phase: str, rid: int) -> None:
        self.frames.append(
            {
                "t": round(self.t, 2),
                "phase": phase,
                "room": rid,
                "cleared": sorted(self.cleared),
                "ops": [
                    [
                        round((o.x - PAD + 0.5) * CELL, 3),
                        round((o.y - PAD + 0.5) * CELL, 3),
                        round(o.heading, 3),
                        o.mode,
                    ]
                    for o in self.ops
                ],
            }
        )
