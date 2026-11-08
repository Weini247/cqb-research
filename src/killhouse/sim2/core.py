"""Closed-loop loop of model v0.3: perceive, exchange delayed messages, decide, move.

`killhouse-search` runs it on generated apartments or houses, with doors that start closed and
have to be opened, and writes results.json plus a viewer with each agent's knowledge. Afterwards
each run is scored with the abstract threat model of the apartment study (`clearing`): hidden
threats that react and hit at a rate. The agents themselves do not react to threats; the risk
only measures how exposed the search was.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..apartment import Apartment, generate_apartment
from ..clearing import OPEN_TIME, Episode, closed_door_masks, door_xy, evaluate_episode
from ..entry import CLEAR_FRAC, DT, HALF_FOV
from ..geom import Grid, reachable, visibility, visibility_fast
from ..house import generate_house
from ..team import Operator, default_team
from .agents import HOLD, MOVE, OPEN, WAIT, AgentState, Limits, turn_towards, wrap
from .perception import DWELL_STEPS, in_view
from .policy import attention_goal, choose_target

REPLAN = 1.0  # s between scheduled replans
MAX_WAIT = 1.0  # s waiting for a teammate before one of the two gives way
YIELD_TIME = 3.0  # s an agent that gives way stays out of the other's path
CONTACT = 0.85  # bodies may come this close (share of the summed radii): shoulders can brush
STUCK_STEPS = 50  # steps (5 s) after which an agent that barely moved drops its target
SIDESTEPS = (
    0.0,
    0.6,
    -0.6,
    1.2,
    -1.2,
)  # rad: step directions tried when the straight one is blocked


@dataclass(frozen=True)
class SearchParams:
    delay: float | None = 1.0  # s until a message arrives; None = no communication
    max_time: float = 120.0
    limits: Limits = field(default_factory=Limits)

    @property
    def label(self) -> str:
        return "no communication" if self.delay is None else f"messages after {self.delay:g} s"


@dataclass
class Scenario:
    ap: Apartment
    grid: Grid
    q: np.ndarray
    vis: np.ndarray
    closed: dict[int, np.ndarray] = field(default_factory=dict)  # door -> sight lines it blocks


def scenario(seed: int, building: str = "apartment", closed_frac: float = 0.0) -> Scenario:
    """A generated apartment or house with its visibility matrix and closed-door masks."""
    if building == "house":
        ap = generate_house(seed, closed_frac=closed_frac)
        grid = Grid(ap.fp)
        q = ap.fp.points()
        vis = visibility_fast(ap.fp, grid, q)
    else:
        ap = generate_apartment(seed, closed_frac=closed_frac)
        grid = Grid(ap.fp)
        q = ap.fp.points()
        vis = visibility(ap.fp, grid, q)
    return Scenario(ap, grid, q, vis, closed_door_masks(ap, grid, q))


def start_positions(sc: Scenario, n: int) -> np.ndarray:
    """n free cells on the landing next to the entrance, at least 0.8 m apart."""
    door = door_xy(sc.ap.entrance)
    g = sc.grid
    d = np.linalg.norm(g.centers - door, axis=1)
    cand = np.nonzero(g.walk_free & (g.region < 0) & (d > 0.6))[0]
    out: list[np.ndarray] = []
    for c in cand[np.argsort(d[cand])]:
        p = g.centers[c]
        if all(np.linalg.norm(p - o) >= 0.8 for o in out):
            out.append(p)
        if len(out) == n:
            return np.array(out)
    raise RuntimeError("not enough room at the entrance")


def run_search(sc: Scenario, team: list[Operator], params: SearchParams) -> dict:
    g, q, vis, lim = sc.grid, sc.q, sc.vis, params.limits
    n, m = len(team), len(q)
    steps = int(round(params.max_time / DT))
    lag = None if params.delay is None else max(1, int(round(params.delay / DT)))
    door = door_xy(sc.ap.entrance)
    starts = start_positions(sc, n)
    allowed = reachable(g, starts[0])  # pockets behind furniture or door leaves are no targets
    cand = np.nonzero(allowed)[0]
    boxes = np.array(sc.ap.fp.blockers, float)
    # doors: closed ones block sight until an agent has spent OPEN_TIME at them; everybody
    # knows the floorplan and which doors are still closed
    closed = dict(sc.closed)
    gaps = {di: np.array(sc.ap.doors[di].gap) for di in closed}
    door_open: dict[int, float] = {}
    open_steps = int(round(OPEN_TIME / DT))
    state = {}

    def doors_changed():
        block = np.zeros_like(vis)
        for mk in closed.values():
            block |= mk
        state["block"] = block
        state["visf"] = (vis[cand] & ~block[cand]).astype(np.float32)

    doors_changed()

    def gap_dist(p: np.ndarray, b: np.ndarray) -> float:
        return float(np.hypot(max(b[0] - p[0], 0, p[0] - b[2]), max(b[1] - p[1], 0, p[1] - b[3])))

    def clearance(p: np.ndarray) -> float:
        """Distance from a body centre to the nearest wall, door leaf or furniture."""
        dx = np.maximum(np.maximum(boxes[:, 0] - p[0], 0), p[0] - boxes[:, 2])
        dy = np.maximum(np.maximum(boxes[:, 1] - p[1], 0), p[1] - boxes[:, 3])
        return float(np.hypot(dx, dy).min())

    agents = []
    for p in starts:
        h = math.atan2(door[1] - p[1], door[0] - p[0])
        agents.append(AgentState(p.copy(), h, h, known=np.zeros(m, bool), dwell=np.zeros(m, int)))
    own = np.full((n, m), steps + 1)  # step of own first sight
    first_known = np.full((n, m), steps + 1)
    claims: list[dict[int, np.ndarray]] = [{} for _ in range(n)]
    avoid: list[list[np.ndarray]] = [[] for _ in range(n)]  # own targets that got it stuck
    anchor = [a.pos.copy() for a in agents]
    inbox: list[tuple[int, int, np.ndarray, np.ndarray | None]] = []
    pos, head, att, mode = [], [], [], []

    def record():
        pos.append([a.pos.tolist() for a in agents])
        head.append([a.heading for a in agents])
        att.append([a.attention for a in agents])
        mode.append([a.mode for a in agents])

    def route(start: np.ndarray, goal: np.ndarray, mask: np.ndarray) -> list:
        """Waypoints after `start`; a sidestep can end on a cell next to a wall, so the path
        then starts with the nearest walkable cell."""
        try:
            return g.astar(start, goal, mask)[1:]
        except RuntimeError:
            free = np.nonzero(g.walk_free & mask)[0]
            near = g.centers[free[np.argmin(np.linalg.norm(g.centers[free] - start, axis=1))]]
            return [near] + g.astar(near, goal, mask)[1:]

    def give_way(lo: int, hi: int, k: int) -> None:
        """Agent `lo` walks to the nearest free spot clear of the remaining path of agent `hi`
        and stays out of the way for YIELD_TIME. Bodies cannot pass in narrow hallways."""
        a, w = agents[lo], agents[hi]
        if k < a.yield_until:
            return
        ahead = [w.pos] + list(w.path[:6])  # where `hi` is going next
        dense = np.concatenate(
            [
                np.linspace(p, r, max(2, int(np.linalg.norm(r - p) / 0.25) + 1))
                for p, r in zip(ahead[:-1], ahead[1:], strict=False)
            ]
            or [w.pos[None]]
        )
        clear = team[lo].radius_m + team[hi].radius_m + 0.15
        d_route = np.min(np.linalg.norm(g.centers[:, None, :] - dense[None], axis=2), axis=1)
        mask = allowed & (np.linalg.norm(g.centers - w.pos, axis=1) > clear)  # only `hi` blocks
        taken = np.zeros(len(g.centers), bool)
        for j, b in enumerate(agents):
            if j != lo:
                taken |= np.linalg.norm(g.centers - b.pos, axis=1) < clear
        spots = np.nonzero(g.walk_free & mask & ~taken & (d_route > clear))[0]
        hold = k + int(round(YIELD_TIME / DT))
        for c in spots[np.argsort(np.linalg.norm(g.centers[spots] - a.pos, axis=1))][:6]:
            try:
                a.path = route(a.pos, g.centers[c], mask)
            except (RuntimeError, ValueError):
                continue
            a.yield_until = a.next_plan = hold
            a.mode, a.waited = MOVE, 0
            return
        away = a.pos - w.pos  # no spot reachable: one step back, away from `hi`
        spot = a.pos + 0.5 * away / max(1e-9, float(np.linalg.norm(away)))
        if g.walk_free[g.index(spot)] and clearance(spot) >= CONTACT * team[lo].radius_m:
            a.path, a.yield_until, a.next_plan, a.mode = [spot], hold, hold, MOVE

    record()
    for k in range(1, steps + 1):
        # 1. messages sent `lag` steps ago arrive at everybody else
        for _arrive, sender, pts, tgt in [x for x in inbox if x[0] <= k]:
            for j, b in enumerate(agents):
                if j == sender:
                    continue
                fresh = pts[~b.known[pts]]
                b.known[fresh] = True
                first_known[j, fresh] = k
                if tgt is not None:
                    claims[j][sender] = tgt
        inbox = [x for x in inbox if x[0] > k]
        for i, a in enumerate(agents):
            op = team[i]
            # 2. perceive with the attention direction of the previous step
            c = g.see_index(a.pos)
            los = vis[c] & ~state["block"][c]
            a.dwell += in_view(g, vis, q, a.pos, a.attention, los=los)
            new = np.nonzero((a.dwell >= DWELL_STEPS) & (own[i] > steps))[0]
            own[i, new] = k
            fresh = new[~a.known[new]]
            a.known[fresh] = True
            first_known[i, fresh] = k
            # 3. decide from own knowledge
            old_target = a.target
            if k % STUCK_STEPS == 0:  # barely moved while trying to: avoid this target for now
                if a.mode != HOLD and a.target >= 0 and np.linalg.norm(a.pos - anchor[i]) < 0.3:
                    avoid[i].append(g.centers[a.target].copy())
                    a.next_plan = k
                anchor[i] = a.pos.copy()
            if a.mode == OPEN and k >= a.open_until:
                if a.opening in closed:  # the door is open from now on, for everybody
                    del closed[a.opening]
                    door_open[a.opening] = round(k * DT, 1)
                    doors_changed()
                a.mode, a.opening = MOVE, -1
            if a.mode == OPEN:
                pass  # still opening the door
            elif k < a.yield_until:
                pass  # giving way: keep the yield path, decide again afterwards
            elif a.known.mean() >= 1 - CLEAR_FRAC:
                a.mode, a.path, a.target = HOLD, [], -1
            elif k >= a.next_plan or not a.path:
                j = choose_target(
                    a, cand, g.centers, state["visf"], list(claims[i].values()) + avoid[i][-3:]
                )
                if j < 0:
                    a.mode, a.path, a.target = HOLD, [], -1
                else:
                    a.target = int(cand[j])
                    a.path = route(a.pos, g.centers[a.target], allowed)
                    a.mode = MOVE
                a.next_plan = k + int(round(REPLAN / DT))
            if lag is not None and (len(fresh) or a.target != old_target):
                tgt = g.centers[a.target].copy() if a.target >= 0 else None
                inbox.append((k + lag, i, fresh, tgt))
            # 4. move within the speed, acceleration and turn limits
            goal_att = attention_goal(a, los, q, lim)
            if a.mode == OPEN:
                a.speed = 0.0
            elif a.mode != HOLD and a.path:
                wp = a.path[0]
                want = math.atan2(wp[1] - a.pos[1], wp[0] - a.pos[0])
                a.heading = turn_towards(a.heading, want, lim.body_turn * DT)
                aligned = abs(wrap(want - a.heading)) < 0.6
                v = min(op.speed_mps, a.speed + lim.accel * DT) if aligned else 0.0
                step = min(v * DT, float(np.linalg.norm(wp - a.pos)))

                def blocking(nxt, i=i, op=op, a=a):
                    return [
                        j
                        for j, b in enumerate(agents)
                        if j != i
                        and np.linalg.norm(nxt - b.pos) < CONTACT * (op.radius_m + team[j].radius_m)
                        and np.linalg.norm(nxt - b.pos) < np.linalg.norm(a.pos - b.pos)
                    ]

                # straight towards the waypoint, else a step turned to either side; a step must
                # keep the body clear of walls or at least not push it further in
                here = clearance(a.pos)
                for turn in SIDESTEPS:
                    nxt = a.pos + step * np.array([math.cos(want + turn), math.sin(want + turn)])
                    blockers = blocking(nxt)
                    c = clearance(nxt)
                    walled = c < CONTACT * op.radius_m and c < here - 1e-9
                    if not blockers and not walled:
                        break
                at_door = next(
                    (
                        di
                        for di, b in gaps.items()
                        if di in closed and gap_dist(nxt, b) < 0.5 * op.radius_m
                    ),
                    None,
                )
                if at_door is not None and not blockers:  # a closed door ahead: open it first
                    a.mode, a.speed, a.opening = OPEN, 0.0, at_door
                    a.open_until = k + open_steps
                elif walled and not blockers:
                    a.mode, a.speed, a.waited = WAIT, 0.0, a.waited + 1
                    if a.waited * DT >= MAX_WAIT:
                        a.next_plan, a.waited = k + 1, 0
                elif blockers:
                    a.mode, a.speed, a.waited = WAIT, 0.0, a.waited + 1
                    if a.waited * DT >= MAX_WAIT:
                        # the lower-priority agent of the pair gives way; finished agents
                        # (holding) always count as lower priority
                        j = blockers[0]
                        lo = j if agents[j].mode == HOLD or j > i else i
                        give_way(lo, i if lo == j else j, k)
                        a.waited = 0
                else:
                    a.mode, a.waited = MOVE, 0
                    a.speed = step / DT
                    a.pos = nxt
                    if np.linalg.norm(wp - a.pos) < 1e-6:
                        a.path.pop(0)
            else:
                a.speed = 0.0
                if abs(wrap(goal_att - a.heading)) > lim.head_range - 1e-6:
                    a.heading = turn_towards(a.heading, goal_att, lim.body_turn * DT)
            a.attention = turn_towards(a.attention, goal_att, lim.head_turn * DT)
            a.clamp_attention(lim)
        record()
        if all(a.mode == HOLD for a in agents) and not inbox:
            break

    t_end = len(pos) - 1
    first_seen = np.minimum(own.min(0), t_end + 1)
    cover = np.sort(first_seen)
    need = int(math.ceil((1 - CLEAR_FRAC) * m))
    t_clear = cover[need - 1] * DT if cover[need - 1] <= t_end else None
    know_all = [np.sort(first_known[i])[need - 1] for i in range(n)]
    # threat model of the apartment study, on the attention directions (where agents look)
    ep = Episode(params.label, np.array(pos), np.array(att), door_open=dict(door_open))
    threat = evaluate_episode(sc.ap, ep, g, vis, q, closed_masks=sc.closed)
    return {
        "name": params.label,
        "metrics": {
            "coverage": round(float((first_seen <= t_end).mean()), 4),
            "t_clear": None if t_clear is None else round(float(t_clear), 1),
            "t_all_know": round(float(max(know_all)) * DT, 1) if max(know_all) <= t_end else None,
            "duration": round(t_end * DT, 1),
            "feasible": t_clear is not None,
            "risk": threat["risk"],
            "risk_multi": threat["risk_multi"],
            "exposure": threat["exposure"],
            "doors_opened": len(door_open),
        },
        "pos": np.round(np.array(pos), 4).tolist(),
        "gaze": np.round(np.array(head), 4).tolist(),
        "attention": np.round(np.array(att), 4).tolist(),
        "mode": np.array(mode).T.tolist(),
        "first_seen": first_seen.tolist(),
        "first_known": np.minimum(first_known, t_end + 1).tolist(),
        "own_seen": np.minimum(own, t_end + 1).tolist(),
        "door_open": [door_open.get(di, -1.0) for di in range(len(sc.ap.doors))],
        "markers": threat["_markers"],
    }


def results(
    seeds: list[int],
    delays: list[float | None],
    team=None,
    building: str = "apartment",
    closed_frac: float = 0.0,
) -> dict:
    team = team or default_team()
    rooms = []
    for seed in seeds:
        sc = scenario(seed, building, closed_frac)
        horizon = 240.0 if building == "house" else 120.0  # houses take longer
        runs = [run_search(sc, team, SearchParams(delay=d, max_time=horizon)) for d in delays]
        rooms.append(
            {
                "room": {**sc.ap.to_dict(), "kind": "apartment"},
                "points": sc.q.round(3).tolist(),
                "replays": runs,
            }
        )
    return {
        "schema": "killhouse.sim2/0",
        "config": {
            "dt": DT,
            "half_fov_deg": round(math.degrees(HALF_FOV), 1),
            "objective": "coverage",
            "attention_equals_heading": False,
            "model": "sim2 (v0.3, exploratory)",
        },
        "team": [o.to_dict() for o in team],
        "rooms": rooms,
    }


def main(argv: list[str] | None = None) -> None:
    from ..viewer3d import to_html

    ap = argparse.ArgumentParser(prog="killhouse-search")
    ap.add_argument("--seeds", type=int, nargs="+", default=[2])
    ap.add_argument(
        "--delays",
        nargs="+",
        default=["0", "1", "none"],
        help="message delays in seconds, 'none' = no communication",
    )
    ap.add_argument("--building", choices=("apartment", "house"), default="apartment")
    ap.add_argument("--closed", type=float, default=0.6, help="share of doors closed at the start")
    ap.add_argument("--out", type=Path, default=Path("out/search"))
    a = ap.parse_args(argv)
    delays = [None if d == "none" else float(d) for d in a.delays]
    data = results(a.seeds, delays, building=a.building, closed_frac=a.closed)
    for r in data["rooms"]:
        for rp in r["replays"]:
            print(f"{r['room']['name']} {rp['name']:24s} {rp['metrics']}")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "results.json").write_text(json.dumps(data), encoding="utf-8")
    (a.out / "viewer3d.html").write_text(to_html(data, "results.json"), encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
