"""Clearing a whole apartment: a sequence of room entries with the doctrine playbooks.

Each door defines a local frame in which the entered room is the single-room model
(door in the wall y = 0, room at y > 0), so every playbook of `doctrine.py` is reused
unchanged. Between entries the team walks through cleared space (A* on the grid). Operators
that do not enter hold the hallway (rear security). Metrics are computed over the whole
episode with the same perception and duel model as for single rooms; threats in uncleared
rooms can see the team through open doors.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import doctrine
from .apartment import Apartment, Door, T, generate_apartment
from .entry import (
    CLEAR_FRAC,
    DEFAULT_CFG,
    DT,
    ModelCfg,
    OpPlan,
    Playbook,
    perception_and_duel,
    stack_pos,
    threat_sets,
    trajectories,
    wrap,
)
from .geom import Grid, visibility
from .room import Room
from .team import Operator, default_team

SETTLE = 0.4  # s the team holds after arriving at the stack
CLEAR_HOLD = 1.0  # s held after the last move of an entry
CORRIDOR_W = 2.2  # rooms narrower than this are entered with the corridor technique

TECHNIQUES = {
    "crisscross": doctrine.crisscross,
    "buttonhook": doctrine.buttonhook,
    "limited-penetration": doctrine.limited_penetration,
}


class Frame:
    """Local frame of a door: entered room at y > 0, door wall face at y = 0."""

    def __init__(self, ap: Apartment, door: Door):
        self.door = door
        x0, y0, x1, y1 = ap.fp.regions[door.into][1]
        self.rect = (x0, y0, x1, y1)
        s = door.side
        if s == "bottom":
            self.rot, self.w, self.d = 0.0, x1 - x0, y1 - y0
            self.dx = (door.a - x0, door.b - x0)
        elif s == "top":
            self.rot, self.w, self.d = math.pi, x1 - x0, y1 - y0
            self.dx = (x1 - door.b, x1 - door.a)
        elif s == "left":
            self.rot, self.w, self.d = -math.pi / 2, y1 - y0, x1 - x0
            self.dx = (y1 - door.b, y1 - door.a)
        else:
            self.rot, self.w, self.d = math.pi / 2, y1 - y0, x1 - x0
            self.dx = (door.a - y0, door.b - y0)

    def to_world(self, p: np.ndarray) -> np.ndarray:
        x0, y0, x1, y1 = self.rect
        lx, ly = p[..., 0], p[..., 1]
        s = self.door.side
        if s == "bottom":
            wx, wy = x0 + lx, y0 + ly
        elif s == "top":
            wx, wy = x1 - lx, y1 - ly
        elif s == "left":
            wx, wy = x0 + ly, y1 - lx
        else:
            wx, wy = x1 - ly, y0 + lx
        return np.stack([wx, wy], -1)

    def to_local(self, p: np.ndarray) -> np.ndarray:
        x0, y0, x1, y1 = self.rect
        wx, wy = p[..., 0], p[..., 1]
        s = self.door.side
        if s == "bottom":
            lx, ly = wx - x0, wy - y0
        elif s == "top":
            lx, ly = x1 - wx, y1 - wy
        elif s == "left":
            lx, ly = y1 - wy, wx - x0
        else:
            lx, ly = wy - y0, x1 - wx
        return np.stack([lx, ly], -1)

    def local_room(self, ap: Apartment, name: str) -> Room:
        obstacles = []
        x0, y0, x1, y1 = self.rect
        for b in ap.fp.furniture + ap.fp.doors:
            if b[2] <= x0 or b[0] >= x1 or b[3] <= y0 or b[1] >= y1:
                continue
            c = self.to_local(np.array([[b[0], b[1]], [b[2], b[3]]]))
            lo, hi = c.min(0), c.max(0)
            obstacles.append(
                (max(0.0, lo[0]), max(0.0, lo[1]), min(self.w, hi[0]), min(self.d, hi[1]))
            )
        return Room(name, self.w, self.d, self.dx[0], self.dx[1], tuple(obstacles), wall_t=T)


def corridor_entry(room: Room, team: list[Operator]) -> Playbook:
    """Narrow room / hallway: #1 deep along the corridor, #2 offset behind, #3/#4 hold."""
    r0, r1 = team[0].radius_m + 0.05, team[1].radius_m + 0.05
    p1 = (min(max(room.w * 0.35, r0), room.w - r0), min(3.0, room.d - 0.6))
    p2 = (min(max(room.w * 0.65, r1), room.w - r1), min(1.6, room.d - 0.6))
    ahead = math.pi / 2
    ops = [
        OpPlan(-1, 0, True, 0.0, 0.5, p1, ahead, ahead, hold=0.3),
        OpPlan(1, 0, True, 0.6, 0.5, p2, ahead + 0.6, ahead - 0.4, hold=0.3),
        OpPlan(-1, 1, enter=False),
        OpPlan(1, 1, enter=False),
    ]
    return Playbook("corridor", ops)


@dataclass
class Episode:
    name: str
    pos: np.ndarray  # (T, n, 2) world
    gaze: np.ndarray  # (T, n)
    steps: list[dict] = field(default_factory=list)  # objectives with start/end time


def objectives(ap: Apartment) -> list[tuple[int, Door]]:
    """Entrance first, then DFS over rooms; hallway doors nearest to the entrance first."""
    ent = ap.entrance
    e = np.array([(ent.a + ent.b) / 2, 0.0])
    order, seen = [(ap.hall, ent)], {ap.hall}

    def door_xy(d: Door) -> np.ndarray:
        c = (d.a + d.b) / 2
        return np.array([c, d.line]) if d.side in ("bottom", "top") else np.array([d.line, c])

    def visit(k):
        nb = [(n, d) for n, d in ap.neighbors(k) if n not in seen]
        for n, d in sorted(nb, key=lambda nd: float(np.linalg.norm(door_xy(nd[1]) - e))):
            if n in seen:
                continue
            seen.add(n)
            order.append((n, d))
            visit(n)

    visit(ap.hall)
    return order


def _walk(path: list[np.ndarray], speed: float) -> tuple[np.ndarray, np.ndarray]:
    pts = np.array(path)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    ts = np.concatenate([[0.0], np.cumsum(seg) / speed])
    return ts, pts


def run_clearing(ap: Apartment, team: list[Operator], technique: str, grid: Grid) -> Episode:
    n = len(team)
    pos_chunks, gaze_chunks, steps = [], [], []
    cleared: set[int] = set()
    cur = None
    cur_gaze = np.zeros(n)
    t_now = 0.0
    for k, door in objectives(ap):
        name = ap.fp.regions[k][0]
        fr = Frame(ap, door)
        room = fr.local_room(ap, name)
        if room.w < CORRIDOR_W:
            pb = corridor_entry(room, team)
        else:
            pb = TECHNIQUES[technique](room, team)
            if room.obstacles:
                pb = doctrine.with_dead_space_step(room, team, pb, strict=True)
        stacks = fr.to_world(
            np.array([stack_pos(room, o, p) for o, p in zip(team, pb.ops, strict=True)])
        )
        # stack spots that fall into walls or uncleared rooms snap to the nearest allowed cell
        allowed = np.isin(grid.region, list(cleared)) | (grid.region < 0)
        ok = grid.walk_free & allowed
        if cur is not None:
            ok &= grid.region != k
        for i in range(n):
            c = int(grid.index(stacks[i]))
            if not ok[c]:
                cand = np.nonzero(ok)[0]
                stacks[i] = grid.centers[
                    cand[np.argmin(np.linalg.norm(grid.centers[cand] - stacks[i], axis=1))]
                ]
                pb.ops[i] = dataclasses.replace(
                    pb.ops[i], start=tuple(fr.to_local(stacks[i]).tolist())
                )
        door_w = fr.to_world(np.array([room.door_c, 0.3]))
        rear = np.array([fr.rot + (math.pi if p.side < 0 else 0.0) for p in pb.ops])
        if cur is None:  # start: team already stacked at the entrance
            cur = stacks.copy()
            cur_gaze = np.arctan2(door_w[1] - cur[:, 1], door_w[0] - cur[:, 0])
        # ---- transit to the stack through cleared space ----
        walks = [_walk(grid.astar(cur[i], stacks[i], allowed), team[i].speed_mps) for i in range(n)]
        dur = max(w[0][-1] for w in walks) + SETTLE
        nt = max(1, int(round(dur / DT)))
        tt = np.arange(nt) * DT
        p_tr = np.zeros((nt, n, 2))
        g_tr = np.zeros((nt, n))
        for i, (ts, pts) in enumerate(walks):
            p_tr[:, i, 0] = np.interp(tt, ts, pts[:, 0])
            p_tr[:, i, 1] = np.interp(tt, ts, pts[:, 1])
            g = cur_gaze[i]
            for s in range(nt):
                v = p_tr[min(s + 1, nt - 1), i] - p_tr[s, i]
                if np.hypot(*v) > 1e-3:
                    tgt = math.atan2(v[1], v[0])
                elif pb.ops[i].enter:
                    tgt = math.atan2(door_w[1] - p_tr[s, i, 1], door_w[0] - p_tr[s, i, 0])
                else:
                    tgt = rear[i]
                g += float(np.clip(wrap(tgt - g), -0.4, 0.4))
                g_tr[s, i] = g
        # ---- entry with the playbook, in the local frame ----
        pos_l, gaze_l, phase = trajectories(room, team, pb)
        moving = np.any(np.abs(np.diff(pos_l, axis=0)) > 1e-6, axis=(1, 2)) | np.any(
            np.diff(phase, axis=0) != 0, axis=1
        )
        last = int(np.nonzero(moving)[0].max()) + 1 if moving.any() else 0
        ne = min(len(pos_l), last + int(round(CLEAR_HOLD / DT)))
        p_en = fr.to_world(pos_l[:ne])
        g_en = gaze_l[:ne] + fr.rot
        for i, p in enumerate(pb.ops):
            if not p.enter:
                p_en[:, i] = p_tr[-1, i]
                g_en[:, i] = rear[i]
        steps.append(
            {
                "room": name,
                "region": k,
                "technique": pb.name,
                "t_transit": round(t_now, 2),
                "t_entry": round(t_now + nt * DT, 2),
                "t_end": round(t_now + (nt + ne) * DT, 2),
            }
        )
        pos_chunks += [p_tr, p_en]
        gaze_chunks += [g_tr, g_en]
        t_now += (nt + ne) * DT
        cur, cur_gaze = p_en[-1].copy(), g_en[-1].copy()
        cleared.add(k)
    tail = int(round(2.0 / DT))
    pos_chunks.append(np.repeat(cur[None], tail, 0))
    gaze_chunks.append(np.repeat(cur_gaze[None], tail, 0))
    return Episode(technique, np.concatenate(pos_chunks), np.concatenate(gaze_chunks), steps)


def evaluate_episode(
    ap: Apartment,
    ep: Episode,
    grid: Grid,
    vmat: np.ndarray,
    q: np.ndarray,
    cfg: ModelCfg = DEFAULT_CFG,
) -> dict:
    nt, n, _ = ep.pos.shape
    m = len(q)
    vis = vmat[grid.see_index(ep.pos)]  # (T, n, m)
    ang = np.arctan2(
        q[None, None, :, 1] - ep.pos[..., 1, None], q[None, None, :, 0] - ep.pos[..., 0, None]
    ).astype(np.float32)
    fov = np.abs(wrap(ang - ep.gaze[..., None].astype(np.float32))) <= cfg.half_fov
    looked = vis & fov
    first, alive, exposure, risk, risk_multi, threat_alive = perception_and_duel(
        vis, looked, cfg, threat_sets(ap, m, cfg)
    )
    unc = alive.mean(1)
    done = np.nonzero(unc <= CLEAR_FRAC)[0]
    reg = ap.fp.region_of(q)
    per_room = {}
    for k, (name, _) in enumerate(ap.fp.regions):
        f = first[reg == k]
        per_room[name] = round(float(f.max() * DT), 1) if f.size and f.max() < nt else None
    return {
        "risk": round(risk, 4),
        "risk_multi": round(risk_multi, 4),
        "threat_alive": round(threat_alive, 4),
        "exposure": round(exposure, 3),
        "t_clear": round(float(done[0] * DT), 1) if done.size else None,
        "duration": round(nt * DT, 1),
        "uncleared_end": round(float(unc[-1]), 4),
        "feasible": bool(done.size),
        "room_clear_s": per_room,
        "_first": first,
    }


def run(seed: int, techniques: list[str], team: list[Operator] | None = None) -> dict:
    team = team or default_team()
    ap = generate_apartment(seed)
    grid = Grid(ap.fp)
    q = ap.fp.points()
    vmat = visibility(ap.fp, grid, q)
    replays = []
    for tech in techniques:
        ep = run_clearing(ap, team, tech, grid)
        met = evaluate_episode(ap, ep, grid, vmat, q)
        first = met.pop("_first")
        replays.append(
            {
                "name": tech,
                "metrics": met,
                "steps": ep.steps,
                "pos": np.round(ep.pos, 2).tolist(),
                "gaze": np.round(ep.gaze, 2).tolist(),
                "first_seen": first.tolist(),
            }
        )
    return {
        "room": {**ap.to_dict(), "kind": "apartment"},
        "points": q.round(3).tolist(),
        "replays": replays,
    }


def main(argv: list[str] | None = None) -> None:
    from .viewer3d import to_html

    ap = argparse.ArgumentParser(prog="killhouse-apartment")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1])
    ap.add_argument("--techniques", nargs="+", default=list(TECHNIQUES))
    ap.add_argument("--out", type=Path, default=Path("out/apartment"))
    a = ap.parse_args(argv)
    team = default_team()
    scenarios = []
    for seed in a.seeds:
        sc = run(seed, a.techniques, team)
        scenarios.append(sc)
        print(f"{sc['room']['name']}: {[lb['name'] for lb in sc['room']['labels']]}")
        for rp in sc["replays"]:
            m = rp["metrics"]
            print(
                f"  {rp['name']:20s} R2={m['risk_multi']:.3f} R1={m['risk']:.3f} "
                f"T={m['t_clear']} s (episode {m['duration']} s) rooms={m['room_clear_s']}"
            )
    data = {
        "schema": "killhouse.apartment/0",
        "config": {
            "dt": DT,
            "half_fov_deg": round(math.degrees(DEFAULT_CFG.half_fov), 1),
            "objective": "risk_multi",
        },
        "team": [o.to_dict() for o in team],
        "rooms": scenarios,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "results.json").write_text(json.dumps(data), encoding="utf-8")
    (a.out / "viewer3d.html").write_text(to_html(data), encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
