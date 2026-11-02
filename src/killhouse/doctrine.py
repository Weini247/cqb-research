"""Stylized models of public room-entry techniques, adapted to the room geometry.

These are simplified encodings of textbook descriptions (split stack, #1..#4 = ops 0..3,
stack L, R, L, R). They are a starting point, not an authoritative rendering of any doctrine.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np

from .entry import CLEAR_FRAC, NT, OpPlan, Playbook, evaluate, threshold_x
from .room import Room, los
from .team import Operator

SIDES = [(-1, 0), (1, 0), (-1, 1), (1, 1)]


def _angle(a, b) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


SMALL_ROOM_W = 4.5  # below this only #1/#2 enter, #3/#4 hold outside


def _pods(room: Room):
    w, d, c = room.w, room.d, room.door_c
    y1 = min(1.0, d - 0.5)
    deep_l, deep_r = (min(1.0, c), y1), (max(w - 1.0, c), y1)
    # #3/#4 hold along the entry wall between door and #1/#2, out of their sectors
    sy = min(1.2, d - 0.5)
    shallow_l = ((c + deep_l[0]) / 2, sy)
    shallow_r = ((c + deep_r[0]) / 2, sy)
    # corner-fed: no short-side corner; the short-side operator goes straight in along the
    # near side wall, the following one takes a deeper long-side position
    if c < 1.6:
        deep_l = (0.7, min(2.6, d - 0.8))
        shallow_l = (min(c + 1.4, w - 1.5), min(2.2, d - 0.9))
    if w - c < 1.6:
        deep_r = (w - 0.7, min(2.6, d - 0.8))
        shallow_r = (max(c - 1.4, 1.5), min(2.2, d - 0.9))
    return {"deep_l": deep_l, "deep_r": deep_r, "shallow_l": shallow_l, "shallow_r": shallow_r}


def _plan(room, op, side, slot, target, tx, delay, pie=0.0) -> OpPlan:
    pods = _pods(room)
    pod = pods[target]
    goes_right = target.endswith("_r")
    thr = (threshold_x(room, op, tx), 0.5)
    corner = (room.w, 0.0) if goes_right else (0.0, 0.0)
    far = (room.w * 0.25, room.d) if goes_right else (room.w * 0.75, room.d)
    if target.startswith("shallow"):  # near corner belongs to the deep operator
        far = (room.w, room.d) if goes_right else (0.0, room.d)
        corner = far
    enter = slot == 0 or room.w >= SMALL_ROOM_W
    return OpPlan(side, slot, enter, delay, tx, pod, _angle(thr, corner), _angle(pod, far), pie)


def crisscross(room: Room, team: list[Operator], t0: float = 0.0, pie: float = 0.0) -> Playbook:
    targets = [("deep_r", 0.85), ("deep_l", 0.15), ("shallow_r", 0.7), ("shallow_l", 0.3)]
    ops = [
        _plan(room, team[i], s, k, tg, tx, t0 + 0.6 * i, pie if i == 0 else 0.0)
        for i, ((s, k), (tg, tx)) in enumerate(zip(SIDES, targets, strict=True))
    ]
    return Playbook("pie+crisscross" if pie else "crisscross", ops)


def buttonhook(room: Room, team: list[Operator]) -> Playbook:
    targets = [("deep_l", 0.1), ("deep_r", 0.9), ("shallow_l", 0.3), ("shallow_r", 0.7)]
    ops = [
        _plan(room, team[i], s, k, tg, tx, 0.6 * i)
        for i, ((s, k), (tg, tx)) in enumerate(zip(SIDES, targets, strict=True))
    ]
    return Playbook("buttonhook", ops)


def limited_penetration(room: Room, team: list[Operator]) -> Playbook:
    ops = []
    for i, (s, k) in enumerate(SIDES):
        op = team[i]
        if i >= 2:
            ops.append(OpPlan(s, k, enter=False))
            continue
        x = room.door_x0 - 0.25 if s < 0 else room.door_x1 + 0.25
        x = min(max(x, op.radius_m + 0.05), room.w - op.radius_m - 0.05)
        pod = (x, 0.7)
        tx = 0.2 if s < 0 else 0.8
        thr = (threshold_x(room, op, tx), 0.5)
        near = (0.0, 0.0) if s < 0 else (room.w, 0.0)
        far = (room.w, room.d) if s < 0 else (0.0, room.d)
        ops.append(OpPlan(s, k, True, 0.6 * i, tx, pod, _angle(thr, near), _angle(pod, far)))
    return Playbook("limited-penetration", ops)


def _free_cells(room: Room, r: float) -> np.ndarray:
    xs = np.arange(r + 0.05, room.w - r - 0.05 + 1e-9, 0.5)
    ys = np.arange(r + 0.05, room.d - r - 0.05 + 1e-9, 0.5)
    c = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
    keep = np.ones(len(c), bool)
    for x0, y0, x1, y1 in room.obstacles:
        keep &= ~((c[:, 0] > x0 - r) & (c[:, 0] < x1 + r) & (c[:, 1] > y0 - r) & (c[:, 1] < y1 + r))
    return c[keep]


def with_dead_space_step(room: Room, team: list[Operator], pb: Playbook, k: int = 4) -> Playbook:
    """Doctrinal "clear dead space": if the plan leaves threat positions unseen, send one
    entered operator (preferably #3/#4) to the free spot that sees most of them, after it has
    held its sector. Deterministic search over operator x top-k candidate spots."""
    base = evaluate(room, pb, team, keep=True)
    if base.uncleared_end <= CLEAR_FRAC:
        return pb
    q = room.points()
    unseen = q[base.first_seen >= NT]
    entered = [i for i, o in enumerate(pb.ops) if o.enter]
    order = sorted(entered, key=lambda i: (pb.ops[i].slot == 0, i))  # #3/#4 first
    best, best_key = pb, (base.uncleared_end, base.risk_multi)
    for i in order[:2]:
        cells = _free_cells(room, team[i].radius_m)
        counts = los(room, cells, unseen).sum(1)
        for c in cells[np.argsort(-counts)[:k]]:
            vis = los(room, c[None], unseen)[0]
            tgt = unseen[vis].mean(0) if vis.any() else unseen.mean(0)
            ops = list(pb.ops)
            ops[i] = dataclasses.replace(
                ops[i], pod2=(float(c[0]), float(c[1])), gaze3=_angle(c, tgt)
            )
            cand = Playbook(pb.name + "+dead-space", ops)
            res = evaluate(room, cand, team)
            key = (max(res.uncleared_end, CLEAR_FRAC), res.risk_multi)
            if res.collision < 0.02 and res.wall < 0.02 and key < best_key:
                best, best_key = cand, key
    return best


def doctrines(room: Room, team: list[Operator]) -> list[Playbook]:
    out = [
        crisscross(room, team),
        buttonhook(room, team),
        crisscross(room, team, t0=3.0, pie=1.0),
        limited_penetration(room, team),
    ]
    if room.obstacles:
        out = [with_dead_space_step(room, team, pb) for pb in out]
    return out
