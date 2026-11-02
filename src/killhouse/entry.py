"""Single-room entry model: operator plans -> trajectories -> risk / time-to-clear metrics.

See docs/CONCEPT.md for definitions. Everything is vectorized over time with numpy.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field

import numpy as np

from .room import Room, _through_door, los
from .team import Operator

DT = 0.1
HORIZON = 12.0
NT = int(round(HORIZON / DT))
HALF_FOV = math.radians(50)
TURN_RATE = 4.0  # rad/s
DWELL = 0.3  # s a point must spend in some vision cone before it counts as cleared
MUZZLE = math.radians(7)
ENTRY_FACTOR = 1.3  # entry speed relative to walking speed
PIE_R, PIE_A0, PIE_SPEED = 1.4, 0.6, 0.6
STACK_GAP = 0.75
CLEAR_FRAC = 0.005  # room counts as cleared when <= 0.5 % of threat positions are unseen


@dataclass(frozen=True)
class ModelCfg:
    """Perception and duel parameters (sensitivity axes, see docs/CONCEPT.md)."""

    half_fov: float = HALF_FOV
    dwell: float = DWELL
    turn_rate: float = TURN_RATE
    threat_react: float = 0.3  # s a threat needs an operator in view before it can fire
    threat_rate: float = 1.0  # 1/s hit rate of a ready, unengaged threat on the team
    engage_rate: float = 4.0  # 1/s neutralization rate per operator aiming at a detected threat
    n_threats: int = 2  # threats per scenario for the multi-threat risk
    n_scenarios: int = 32  # sampled threat placements (common random numbers per room)


DEFAULT_CFG = ModelCfg()


@dataclass
class OpPlan:
    side: int  # -1 stacked left of the door, +1 right
    slot: int  # 0 = next to the door frame
    enter: bool = True
    delay: float = 0.0  # earliest time to start the entry
    tx: float = 0.5  # threshold crossing point, 0 = left jamb .. 1 = right jamb
    pod: tuple[float, float] = (1.0, 1.0)  # point of domination (room frame, m)
    gaze1: float = 0.0  # gaze target after crossing the threshold (rad)
    gaze2: float = 0.0  # gaze target at the POD (rad)
    pie: float = 0.0  # 0..1 fraction of the pie-slicing arc walked before entry
    hold: float = 0.5  # s to keep gaze1 (own corner) after reaching the POD
    pod2: tuple[float, float] | None = None  # optional second position (clear dead space)
    gaze3: float = 0.0  # gaze target while moving to / holding pod2
    hold2: float = 0.6  # s to hold the sector (gaze2) at the POD before leaving for pod2
    start: tuple[float, float] | None = None  # override of the stack position (multi-room)
    speed: float = 1.0  # entry speed factor (deliberate clearing < 1)


@dataclass
class Playbook:
    name: str
    ops: list[OpPlan]


@dataclass
class Result:
    risk: float  # P(team takes a hit) for one threat at a uniformly random hidden position
    risk_multi: float  # P(team takes a hit) with n_threats threats, one target per operator
    threat_alive: float  # P(threat still active at the horizon)
    exposure: float
    t_clear: float
    uncleared_end: float
    collision: float
    wall: float
    fratricide: float
    pos: np.ndarray | None = field(default=None, repr=False)
    gaze: np.ndarray | None = field(default=None, repr=False)
    first_seen: np.ndarray | None = field(default=None, repr=False)

    def objective(self, key: str) -> float:
        return float(getattr(self, key))

    @property
    def feasible(self) -> bool:
        """Physically valid and room cleared; fratricide is compared separately."""
        return self.collision < 0.02 and self.wall < 0.02 and self.uncleared_end <= CLEAR_FRAC

    def metrics(self) -> dict:
        return {
            "risk": round(self.risk, 4),
            "risk_multi": round(self.risk_multi, 4),
            "threat_alive": round(self.threat_alive, 4),
            "exposure": round(self.exposure, 4),
            "t_clear": round(self.t_clear, 3),
            "uncleared_end": round(self.uncleared_end, 4),
            "collision": round(self.collision, 4),
            "wall": round(self.wall, 4),
            "fratricide": round(self.fratricide, 3),
            "feasible": self.feasible,
        }


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def stack_pos(room: Room, op: Operator, plan: OpPlan) -> np.ndarray:
    if plan.start is not None:
        return np.array(plan.start, float)
    off = 0.35 + plan.slot * STACK_GAP
    x = room.door_x0 - off if plan.side < 0 else room.door_x1 + off
    return np.array([x, -(room.wall_t + op.radius_m + 0.05)])


def threshold_x(room: Room, op: Operator, tx: float) -> float:
    lo, hi = room.door_x0 + op.radius_m, room.door_x1 - op.radius_m
    return room.door_c if hi < lo else lo + tx * (hi - lo)


def _keyframes(room: Room, op: Operator, plan: OpPlan):
    """Piecewise-linear path as (times, points) plus threshold / POD arrival times."""
    p = stack_pos(room, op, plan)
    ts, ps = [0.0], [p]
    v = op.speed_mps * ENTRY_FACTOR * plan.speed

    def go(q, speed):
        q = np.asarray(q, float)
        ts.append(ts[-1] + float(np.linalg.norm(q - ps[-1])) / speed)
        ps.append(q)

    if plan.pie > 0:
        c = np.array([room.door_c, -room.wall_t])
        a0 = math.pi + PIE_A0 if plan.side < 0 else -PIE_A0
        sweep = -plan.side * (math.pi / 2 - PIE_A0) * plan.pie
        go(c + PIE_R * np.array([math.cos(a0), math.sin(a0)]), op.speed_mps)
        for k in range(1, 7):
            a = a0 + sweep * k / 6
            go(c + PIE_R * np.array([math.cos(a), math.sin(a)]), PIE_SPEED)
    if not plan.enter:
        return np.array(ts), np.array(ps), math.inf, math.inf, math.inf
    if ts[-1] < plan.delay:
        ts.append(plan.delay)
        ps.append(ps[-1])
    xt = threshold_x(room, op, plan.tx)
    go((xt, -room.wall_t - 0.4), v)
    t_thr = ts[-1]  # gaze switches to the own corner from the approach point on
    go((xt, 0.5), v)
    go(plan.pod, v)
    t_pod = ts[-1]
    if plan.pod2 is None:
        return np.array(ts), np.array(ps), t_thr, t_pod, math.inf
    t_leave = t_pod + plan.hold + plan.hold2
    ts.append(t_leave)
    ps.append(ps[-1])
    go(plan.pod2, op.speed_mps)
    return np.array(ts), np.array(ps), t_thr, t_pod, t_leave


def trajectories(room: Room, team: list[Operator], pb: Playbook, cfg: ModelCfg = DEFAULT_CFG):
    t = np.arange(NT) * DT
    n = len(team)
    pos = np.zeros((NT, n, 2))
    gaze = np.zeros((NT, n))
    phase = np.zeros((NT, n), int)
    look = np.array([room.door_c, 0.6])
    for i, (op, plan) in enumerate(zip(team, pb.ops, strict=True)):
        ts, ps, t_thr, t_pod, t_leave = _keyframes(room, op, plan)
        ts = np.maximum.accumulate(ts + np.arange(len(ts)) * 1e-9)
        pos[:, i, 0] = np.interp(t, ts, ps[:, 0])
        pos[:, i, 1] = np.interp(t, ts, ps[:, 1])
        phase[:, i] = (t >= t_thr).astype(int) + (t >= t_pod + plan.hold) + (t >= t_leave)
        g = math.atan2(look[1] - pos[0, i, 1], look[0] - pos[0, i, 0])
        for k in range(NT):
            if phase[k, i] == 0:
                tgt = math.atan2(look[1] - pos[k, i, 1], look[0] - pos[k, i, 0])
            else:
                tgt = (plan.gaze1, plan.gaze2, plan.gaze3)[phase[k, i] - 1]
            diff = (tgt - g + math.pi) % (2 * math.pi) - math.pi
            g += max(-cfg.turn_rate * DT, min(cfg.turn_rate * DT, diff))
            gaze[k, i] = g
    return pos, gaze, phase


def _door_los(room: Room, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """LOS between two operator tracks (T,2) through the entry wall only."""
    return _through_door(room, a[:, 0], a[:, 1], b[:, 0], b[:, 1])


def threat_sets(room: Room, m: int, cfg: ModelCfg) -> np.ndarray:
    """Fixed threat placements per room (common random numbers across all plans)."""
    rng = np.random.default_rng(zlib.crc32(room.name.encode()))
    k = min(cfg.n_threats, m)
    return np.array([rng.choice(m, size=k, replace=False) for _ in range(cfg.n_scenarios)])


def multi_threat_risk(looked, detected, h, idx, engage_rate) -> float:
    """Several threats at once; each operator engages one detected threat per step.

    looked (T,n,m): operator has the point in its cone with LOS; detected (T,m); h (T,m): per
    step hit probability of a ready threat; idx (S,K) threat placements. Each operator aims at
    the visible detected threat that is most likely still active, so a second or third gun is
    what keeps a second threat from firing while the first is engaged.
    """
    s_n, k_n = idx.shape
    lk = looked[:, :, idx] & detected[:, idx][:, None]  # (T,n,S,K) engageable
    hh = h[:, idx]  # (T,S,K)
    a = np.ones((s_n, k_n))  # P(threat still active)
    u = np.ones(s_n)  # P(team unhurt)
    onehot = np.eye(k_n, dtype=bool)
    for t in np.nonzero(lk.any(axis=(1, 2, 3)) | hh.any(axis=(1, 2)))[0]:
        score = np.where(lk[t], a[None], -1.0)
        eng = (onehot[score.argmax(2)] & (score.max(2) > 0)[..., None]).sum(0)
        u *= np.prod(1 - a * hh[t], axis=1)
        a *= np.exp(-engage_rate * DT * eng)
    return float(1 - u.mean())


def perception_and_duel(vis, looked, cfg: ModelCfg, threat_idx):
    """Detection (dwell), exposure and the duel risks from (T,n,m) visibility arrays."""
    nt, _, m = vis.shape
    seen = np.cumsum(looked.any(axis=1), axis=0) >= max(1, round(cfg.dwell / DT))
    first = np.where(seen.any(0), seen.argmax(0), nt)
    alive = np.arange(nt)[:, None] < first[None, :]  # not yet detected
    exposure = float((vis & alive[:, None, :]).sum()) / m * DT
    # Duel per threat position: a threat that has had an operator in view for threat_react
    # hits the team at threat_rate until neutralized; neutralization needs detection and then
    # runs at engage_rate per operator currently aiming at it (more guns on a sector help).
    sees = vis.any(axis=1)
    ready = np.cumsum(sees, axis=0) >= max(1, round(cfg.threat_react / DT))
    h = np.where(ready & sees, 1 - math.exp(-cfg.threat_rate * DT), 0.0)
    engaged = looked.sum(axis=1) * ~alive
    q = 1 - np.exp(-cfg.engage_rate * DT * engaged)
    surv = np.cumprod((1 - h) * (1 - q), axis=0)
    before = np.vstack([np.ones((1, m)), surv[:-1]])  # threat active and team unhurt
    risk = float((before * h).sum(0).mean())
    hit_free = np.cumprod(1 - h, axis=0)[-1]
    risk_multi = multi_threat_risk(looked, ~alive, h, threat_idx, cfg.engage_rate)
    threat_alive = float((np.prod(1 - q, axis=0) * hit_free).mean())
    return first, alive, exposure, risk, risk_multi, threat_alive


def evaluate(
    room: Room,
    pb: Playbook,
    team: list[Operator],
    keep: bool = False,
    cfg: ModelCfg = DEFAULT_CFG,
) -> Result:
    pos, gaze, phase = trajectories(room, team, pb, cfg)
    q = room.points()
    m, n = len(q), len(team)
    p = pos.reshape(-1, 2)
    vis = los(room, p, q).reshape(NT, n, m)
    ang = np.arctan2(q[None, :, 1] - p[:, 1, None], q[None, :, 0] - p[:, 0, None])
    fov = np.abs(wrap(ang.reshape(NT, n, m) - gaze[..., None])) <= cfg.half_fov
    looked = vis & fov
    first, alive, exposure, risk, risk_multi, threat_alive = perception_and_duel(
        vis, looked, cfg, threat_sets(room, m, cfg)
    )
    unc = alive.mean(1)
    done = np.nonzero(unc <= CLEAR_FRAC)[0]
    t_clear = float(done[0] * DT) if done.size else HORIZON + 10 * float(unc[-1])

    r = np.array([o.radius_m for o in team])
    x, y = pos[..., 0], pos[..., 1]
    t = room.wall_t
    straddle = (y > -t - r) & (y < r)
    lat = np.maximum(room.door_x0 - (x - r), (x + r) - room.door_x1).clip(0)
    depth = np.minimum(r - y, y + t + r).clip(0)
    wall = np.where(straddle, np.minimum(lat, depth), 0.0)
    inside = y > 0
    wall += np.where(inside, (r - x).clip(0) + (x + r - room.w).clip(0), 0.0)
    wall += np.where(inside, (y + r - room.d).clip(0), 0.0)
    for x0, y0, x1, y1 in room.obstacles:
        depth = np.minimum.reduce([x + r - x0, x1 - (x - r), y + r - y0, y1 - (y - r)])
        wall += depth.clip(0)

    collision = fratricide = 0.0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = pos[:, j] - pos[:, i]
            if j > i:
                collision += float((r[i] + r[j] - np.hypot(d[:, 0], d[:, 1])).clip(0).sum())
            aim = np.abs(wrap(np.arctan2(d[:, 1], d[:, 0]) - gaze[:, i])) < MUZZLE
            mask = aim & (phase[:, i] >= 1) & _door_los(room, pos[:, i], pos[:, j])
            fratricide += float(mask.sum())
    res = Result(
        risk,
        risk_multi,
        threat_alive,
        exposure,
        t_clear,
        float(unc[-1]),
        collision * DT,
        float(wall.sum()) * DT,
        fratricide * DT,
    )
    if keep:
        res.pos, res.gaze, res.first_seen = pos, gaze, first
    return res
