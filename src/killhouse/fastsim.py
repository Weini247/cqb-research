"""Batched single-room evaluation on the GPU (PyTorch), numerically matching `entry.evaluate`.

Trajectories are still built per plan on the CPU (cheap); visibility, perception, the duel
and the multi-threat risk run for a whole population at once. Optional dependency:
`python -m uv sync --extra gpu`. Without CUDA it falls back to the PyTorch CPU backend.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from .entry import (
    CLEAR_FRAC,
    DEFAULT_CFG,
    DT,
    HORIZON,
    MUZZLE,
    NT,
    ModelCfg,
    Playbook,
    Result,
    _keyframes,
    threat_sets,
)
from .room import Room
from .team import Operator

try:  # optional
    import torch
except ImportError:  # pragma: no cover
    torch = None


def available() -> bool:
    return torch is not None


@lru_cache(maxsize=1)
def device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _wrap(a):
    return torch.remainder(a + math.pi, 2 * math.pi) - math.pi


def _seg_hits_box(px, py, qx, qy, box):
    x0, y0, x1, y1 = box
    t0 = torch.zeros(torch.broadcast_shapes(px.shape, qx.shape), device=px.device)
    t1 = torch.ones_like(t0)
    inf = torch.tensor(float("inf"), device=px.device)
    for p, q, lo, hi in ((px, qx, x0, x1), (py, qy, y0, y1)):
        d = q - p
        par = d == 0
        dd = torch.where(par, torch.ones_like(d), d)
        ta, tb = (lo - p) / dd, (hi - p) / dd
        inside = (p >= lo) & (p <= hi)
        tmin = torch.where(par, torch.where(inside, -inf, inf), torch.minimum(ta, tb))
        tmax = torch.where(par, torch.where(inside, inf, -inf), torch.maximum(ta, tb))
        t0, t1 = torch.maximum(t0, tmin), torch.minimum(t1, tmax)
    return t0 <= t1


def _through_door(room: Room, px, py, qx, qy):
    ok = None
    for y in (0.0, -room.wall_t):
        den = qy - py
        den = torch.where(den == 0, torch.full_like(den, 1e-30), den)
        xc = px + (qx - px) * (y - py) / den
        inside = (xc >= room.door_x0) & (xc <= room.door_x1)
        cross = ((py < y) & (qy > y)) | ((py > y) & (qy < y))
        r = torch.where(cross, inside, torch.ones_like(inside))
        ok = r if ok is None else ok & r
    return ok


def batch_trajectories(room: Room, team: list[Operator], pbs: list[Playbook], cfg: ModelCfg):
    """Same as entry.trajectories for a list of plans; the gaze turn loop runs over all
    plans and operators at once."""
    P, n = len(pbs), len(team)
    t = np.arange(NT) * DT
    pos = np.zeros((P, NT, n, 2))
    phase = np.zeros((P, NT, n), int)
    tg = np.zeros((P, 3, n))
    for b, pb in enumerate(pbs):
        for i, (op, plan) in enumerate(zip(team, pb.ops, strict=True)):
            ts, ps, t_thr, t_pod, t_leave = _keyframes(room, op, plan)
            ts = np.maximum.accumulate(ts + np.arange(len(ts)) * 1e-9)
            pos[b, :, i, 0] = np.interp(t, ts, ps[:, 0])
            pos[b, :, i, 1] = np.interp(t, ts, ps[:, 1])
            phase[b, :, i] = (t >= t_thr).astype(int) + (t >= t_pod + plan.hold) + (t >= t_leave)
            tg[b, :, i] = (plan.gaze1, plan.gaze2, plan.gaze3)
    look = np.array([room.door_c, 0.6])
    door_ang = np.arctan2(look[1] - pos[..., 1], look[0] - pos[..., 0])  # (P,T,n)
    gaze = np.zeros((P, NT, n))
    g = door_ang[:, 0].copy()
    step = cfg.turn_rate * DT
    bi, ni = np.arange(P)[:, None], np.arange(n)[None, :]
    for k in range(NT):
        ph = phase[:, k]
        tgt = np.where(ph == 0, door_ang[:, k], tg[bi, np.clip(ph - 1, 0, 2), ni])
        diff = (tgt - g + math.pi) % (2 * math.pi) - math.pi
        g = g + np.clip(diff, -step, step)
        gaze[:, k] = g
    return pos, gaze, phase


def _physical_batch(room: Room, team, pos, gaze, phase):
    """Torch version of entry.physical_metrics for (P,T,n) tensors -> three (P,) arrays."""
    dev = pos.device
    r = torch.tensor([o.radius_m for o in team], dtype=torch.float32, device=dev)
    x, y = pos[..., 0], pos[..., 1]
    t = room.wall_t
    straddle = (y > -t - r) & (y < r)
    lat = torch.maximum(room.door_x0 - (x - r), (x + r) - room.door_x1).clamp(min=0)
    depth = torch.minimum(r - y, y + t + r).clamp(min=0)
    wall = torch.where(straddle, torch.minimum(lat, depth), torch.zeros_like(x))
    inside = y > 0
    wall = wall + torch.where(inside, (r - x).clamp(min=0) + (x + r - room.w).clamp(min=0), 0.0)
    wall = wall + torch.where(inside, (y + r - room.d).clamp(min=0), 0.0)
    for x0, y0, x1, y1 in room.obstacles:
        d = torch.minimum(
            torch.minimum(x + r - x0, x1 - (x - r)), torch.minimum(y + r - y0, y1 - (y - r))
        )
        wall = wall + d.clamp(min=0)
    n = len(team)
    col = torch.zeros(pos.shape[0], device=dev)
    fr = torch.zeros(pos.shape[0], device=dev)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = pos[:, :, j] - pos[:, :, i]
            if j > i:
                col = col + (r[i] + r[j] - torch.hypot(d[..., 0], d[..., 1])).clamp(min=0).sum(1)
            aim = _wrap(torch.atan2(d[..., 1], d[..., 0]) - gaze[:, :, i]).abs() < MUZZLE
            a, b = pos[:, :, i], pos[:, :, j]
            vis = _through_door(room, a[..., 0], a[..., 1], b[..., 0], b[..., 1])
            fr = fr + (aim & (phase[:, :, i] >= 1) & vis).sum(1)
    return (col * DT).cpu().numpy(), (wall.sum((1, 2)) * DT).cpu().numpy(), (fr * DT).cpu().numpy()


def evaluate_batch(
    room: Room, pbs: list[Playbook], team: list[Operator], cfg: ModelCfg = DEFAULT_CFG
) -> list[Result]:
    dev = device()
    pos_np, gaze_np, phase_np = batch_trajectories(room, team, pbs, cfg)
    pos = torch.tensor(pos_np, dtype=torch.float32, device=dev)  # (P,T,n,2)
    gaze = torch.tensor(gaze_np, dtype=torch.float32, device=dev)
    qn = room.points()
    q = torch.tensor(qn, dtype=torch.float32, device=dev)
    nt, m = pos.shape[1], len(qn)
    px, py = pos[..., 0, None], pos[..., 1, None]  # (P,T,n,1)
    qx, qy = q[:, 0], q[:, 1]
    vis = torch.where(
        py < 0, _through_door(room, px, py, qx, qy), torch.ones_like(py, dtype=torch.bool)
    )
    for box in room.obstacles:
        vis &= ~_seg_hits_box(px, py, qx, qy, box)
    ang = torch.atan2(qy - py, qx - px)
    looked = vis & (_wrap(ang - gaze[..., None]).abs() <= cfg.half_fov)

    k_dwell = max(1, round(cfg.dwell / DT))
    seen = torch.cumsum(looked.any(2).int(), 1) >= k_dwell  # (P,T,M)
    first = torch.where(
        seen.any(1), seen.int().argmax(1), torch.full_like(seen[:, 0], nt, dtype=torch.long)
    )
    tt = torch.arange(nt, device=dev)[None, :, None]
    alive = tt < first[:, None, :]  # (P,T,M)
    exposure = (vis & alive[:, :, None, :]).sum((1, 2, 3)).float() / m * DT

    sees = vis.any(2)
    ready = torch.cumsum(sees.int(), 1) >= max(1, round(cfg.threat_react / DT))
    h = torch.where(ready & sees, 1 - math.exp(-cfg.threat_rate * DT), 0.0)
    engaged = looked.sum(2).float() * (~alive)
    qe = 1 - torch.exp(-cfg.engage_rate * DT * engaged)
    surv = torch.cumprod((1 - h) * (1 - qe), 1)
    before = torch.cat([torch.ones_like(surv[:, :1]), surv[:, :-1]], 1)
    risk = (before * h).sum(1).mean(1)
    hit_free = torch.cumprod(1 - h, 1)[:, -1]
    threat_alive = (torch.prod(1 - qe, 1) * hit_free).mean(1)

    idx = torch.tensor(threat_sets(room, m, cfg), device=dev)  # (S,K)
    k_n = idx.shape[1]
    lk = looked[..., idx] & (~alive)[:, :, idx][:, :, None]  # (P,T,n,S,K)
    hh = h[:, :, idx]  # (P,T,S,K)
    a = torch.ones(hh.shape[0], *idx.shape, device=dev)
    u = torch.ones(hh.shape[0], idx.shape[0], device=dev)
    steps = torch.nonzero(lk.any(4).any(3).any(2).any(0) | (hh > 0).any(3).any(2).any(0))[:, 0]
    for t in steps.tolist():
        score = torch.where(lk[:, t], a[:, None], torch.tensor(-1.0, device=dev))
        best = score.argmax(-1)
        has = score.amax(-1) > 0
        eng = (torch.nn.functional.one_hot(best, k_n).bool() & has[..., None]).sum(1)
        u = u * torch.prod(1 - a * hh[:, t], -1)
        a = a * torch.exp(-cfg.engage_rate * DT * eng)
    risk_multi = 1 - u.mean(1)

    unc = alive.float().mean(2)  # (P,T)
    done = unc <= CLEAR_FRAC
    t_first = torch.where(done.any(1), done.int().argmax(1).float() * DT, HORIZON + 10 * unc[:, -1])

    col, wall, fr = _physical_batch(
        room,
        team,
        torch.tensor(pos_np, dtype=torch.float64, device=dev),
        torch.tensor(gaze_np, dtype=torch.float64, device=dev),
        torch.tensor(phase_np, device=dev),
    )
    vals = [
        x.cpu().numpy() for x in (risk, risk_multi, threat_alive, exposure, t_first, unc[:, -1])
    ]
    return [
        Result(*(float(v[k]) for v in vals), float(col[k]), float(wall[k]), float(fr[k]))
        for k in range(len(pbs))
    ]
