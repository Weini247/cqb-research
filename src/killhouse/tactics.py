"""Tactic catalog: every encoded technique with source, applicability and review status.

The builders reuse the geometry helpers of `doctrine.py` (points of domination adapted to
centre/corner-fed doors and small rooms). `docs/TACTICS.md` describes the entries in words;
`killhouse-tactics` evaluates the whole catalog, nominally and under execution noise.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import doctrine
from .doctrine import _plan
from .entry import Playbook, evaluate
from .room import Room, standard_rooms
from .team import Operator, default_team

FM_3_06_11 = (
    "FM 3-06.11 Combined Arms Operations in Urban Terrain (US Army, 2002), ch. 3, "
    "para. 3-22 'Techniques for Entering Buildings and Clearing Rooms'"
)
CALL_97_20 = "CALL Newsletter 97-20, battle drill 'Enter building / clear room' (US Army, 1997)"
PRACTITIONER = "public practitioner material (police/military training articles and courses)"

SPLIT = [(-1, 0), (1, 0), (-1, 1), (1, 1)]
LEFT = [(-1, 0), (-1, 1), (-1, 2), (-1, 3)]


@dataclass(frozen=True)
class Tactic:
    id: str
    name: str
    family: str  # entry / pie / limited / deliberate
    stack: str  # split / single-side
    min_team: int
    build: Callable[[Room, list[Operator]], Playbook]
    sources: tuple[str, ...]
    status: str  # "coded from source" / "adapted" / "SME confirmed"
    note: str = ""


def _full(team: list[Operator]) -> list[Operator]:
    """Builders lay out four roles; smaller teams use the first n of them."""
    return team + default_team()[len(team) :]


def _assign(room, team, sides, targets, spacing=0.6, t0=0.0, pie0=0.0, speed=1.0, hold=0.5):
    ops, full = [], _full(team)
    for i, ((s, k), (tg, tx)) in enumerate(zip(sides, targets, strict=True)):
        p = _plan(room, full[i], s, k, tg, tx, t0 + spacing * i, pie0 if i == 0 else 0.0)
        # small rooms: the first two in the order of march enter, whatever their stack slot
        enter = i < 2 or room.w >= doctrine.SMALL_ROOM_W
        ops.append(dataclasses.replace(p, speed=speed, hold=hold, enter=enter))
    return ops[: len(team)]


def crisscross(room, team):
    return Playbook("crisscross", doctrine.crisscross(room, _full(team)).ops[: len(team)])


def buttonhook(room, team):
    return Playbook("buttonhook", doctrine.buttonhook(room, _full(team)).ops[: len(team)])


def combination_cross_first(room, team):
    # single-side stack on the left: #1 crosses to the far side, #2 hooks back to the near side
    tg = [("deep_r", 0.85), ("deep_l", 0.15), ("shallow_r", 0.7), ("shallow_l", 0.3)]
    return Playbook("combination (cross first)", _assign(room, team, LEFT, tg))


def combination_hook_first(room, team):
    tg = [("deep_l", 0.1), ("deep_r", 0.85), ("shallow_l", 0.3), ("shallow_r", 0.7)]
    return Playbook("combination (hook first)", _assign(room, team, LEFT, tg))


def two_man_crisscross(room, team):
    pb = doctrine.crisscross(room, _full(team))
    ops = [o if i < 2 else dataclasses.replace(o, enter=False) for i, o in enumerate(pb.ops)]
    return Playbook("two-man crisscross", ops[: len(team)])


def limited_penetration(room, team):
    ops = doctrine.limited_penetration(room, _full(team)).ops[: len(team)]
    return Playbook("limited penetration", ops)


def pie_crisscross(room, team):
    ops = doctrine.crisscross(room, _full(team), t0=3.0, pie=1.0).ops[: len(team)]
    return Playbook("pie + crisscross", ops)


def deliberate(room, team):
    # slow, methodical: #1 slices the pie from outside, then the team enters at reduced speed,
    # wider spacing and longer corner holds (crisscross geometry)
    tg = [("deep_r", 0.85), ("deep_l", 0.15), ("shallow_r", 0.7), ("shallow_l", 0.3)]
    ops = _assign(room, team, SPLIT, tg, spacing=1.2, t0=3.0, pie0=1.0, speed=0.6, hold=1.0)
    return Playbook("deliberate", ops)


CATALOG: list[Tactic] = [
    Tactic(
        "crisscross",
        "Crisscross",
        "entry",
        "split",
        2,
        crisscross,
        (FM_3_06_11, CALL_97_20),
        "coded from source",
        "#1/#2 cross through the doorway to the opposite near corners",
    ),
    Tactic(
        "buttonhook",
        "Buttonhook",
        "entry",
        "split",
        2,
        buttonhook,
        (FM_3_06_11, CALL_97_20),
        "coded from source",
        "#1/#2 hook around the frame and stay on their own side",
    ),
    Tactic(
        "combination-cross",
        "Combination (cross first)",
        "entry",
        "single-side",
        2,
        combination_cross_first,
        (FM_3_06_11, PRACTITIONER),
        "adapted",
        "single-side stack; #1 crosses, #2 hooks; #3/#4 alternate",
    ),
    Tactic(
        "combination-hook",
        "Combination (hook first)",
        "entry",
        "single-side",
        2,
        combination_hook_first,
        (FM_3_06_11, PRACTITIONER),
        "adapted",
        "single-side stack; #1 hooks, #2 crosses",
    ),
    Tactic(
        "two-man",
        "Two-man crisscross",
        "entry",
        "split",
        2,
        two_man_crisscross,
        (FM_3_06_11,),
        "adapted",
        "only #1/#2 enter, #3/#4 hold outside / rear security",
    ),
    Tactic(
        "limited",
        "Limited penetration",
        "limited",
        "split",
        2,
        limited_penetration,
        (PRACTITIONER,),
        "adapted",
        "one step in beside the frame, clear from the threshold",
    ),
    Tactic(
        "pie-crisscross",
        "Pie + crisscross",
        "pie",
        "split",
        2,
        pie_crisscross,
        (PRACTITIONER,),
        "adapted",
        "#1 slices the pie from outside, then dynamic crisscross",
    ),
    Tactic(
        "deliberate",
        "Deliberate entry",
        "deliberate",
        "split",
        2,
        deliberate,
        (FM_3_06_11, PRACTITIONER),
        "adapted",
        "pie, then slow entry (0.6x), 1.2 s spacing, 1.0 s corner hold",
    ),
]
BY_ID = {t.id: t for t in CATALOG}


def build(
    tactic_id: str, room: Room, team: list[Operator], dead_space: bool = True, strict: bool = False
) -> Playbook:
    pb = BY_ID[tactic_id].build(room, team)
    if dead_space and room.obstacles:
        pb = doctrine.with_dead_space_step(room, team, pb, strict=strict)
    return pb


# ---------- execution noise ----------
@dataclass(frozen=True)
class Noise:
    timing: float = 0.25  # s, std of each operator's start time
    position: float = 0.25  # m, std of points of domination (per axis)
    gaze: float = 0.15  # rad, std of gaze targets
    speed: float = 0.10  # relative std of entry speed


def perturb(pb: Playbook, room: Room, rng: np.random.Generator, nz: Noise) -> Playbook:
    ops = []
    for o in pb.ops:

        def pt(p):
            if p is None:
                return None
            x, y = np.array(p) + rng.normal(0, nz.position, 2)
            return (float(np.clip(x, 0.3, room.w - 0.3)), float(np.clip(y, 0.3, room.d - 0.3)))

        ops.append(
            dataclasses.replace(
                o,
                delay=max(0.0, o.delay + rng.normal(0, nz.timing)),
                pod=pt(o.pod),
                pod2=pt(o.pod2),
                gaze1=o.gaze1 + rng.normal(0, nz.gaze),
                gaze2=o.gaze2 + rng.normal(0, nz.gaze),
                gaze3=o.gaze3 + rng.normal(0, nz.gaze),
                speed=max(0.3, o.speed * (1 + rng.normal(0, nz.speed))),
            )
        )
    return Playbook(pb.name, ops)


def robust_eval(room, pb, team, k=16, nz: Noise | None = None, seed=0, key="risk_multi") -> dict:
    """Risk under execution noise: mean and 90th percentile over k perturbed executions."""
    nz = nz or Noise()
    rng = np.random.default_rng(seed)
    vals, valid, unseen = [], 0, 0
    for _ in range(k):
        res = evaluate(room, perturb(pb, room, rng, nz), team)
        vals.append(res.objective(key))
        valid += res.feasible
        unseen += res.uncleared_end > 0.005
    v = np.array(vals)
    return {
        "mean": round(float(v.mean()), 4),
        "p90": round(float(np.quantile(v, 0.9)), 4),
        "valid_frac": round(valid / k, 3),
        "unseen_frac": round(unseen / k, 3),  # executions that left threat positions unseen
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-tactics")
    ap.add_argument("--noise-samples", type=int, default=16)
    ap.add_argument("--out", type=Path, default=Path("out/tactics.json"))
    a = ap.parse_args(argv)
    team = default_team()
    rows = []
    print(
        f"{'room':13s} {'tactic':26s} {'R2':>6s} {'T':>5s} {'noisy':>6s} {'p90':>6s} {'valid':>5s}"
    )
    for room in standard_rooms():
        for t in CATALOG:
            pb = build(t.id, room, team)
            res = evaluate(room, pb, team)
            rob = robust_eval(room, pb, team, k=a.noise_samples)
            rows.append(
                {"room": room.name, "tactic": t.id, "team": 4, **res.metrics(), "noise": rob}
            )
            print(
                f"{room.name:13s} {t.name:26s} {res.risk_multi:6.3f} {res.t_clear:5.1f} "
                f"{rob['mean']:6.3f} {rob['p90']:6.3f} {rob['valid_frac']:5.2f}"
                + ("" if res.feasible else "  (nominal invalid)")
            )
    sizes = []
    for room in [r for r in standard_rooms() if r.name in ("M-center", "L-corner")]:
        for tid in ("crisscross", "buttonhook"):
            for n in (2, 3, 4):
                sub = team[:n]
                res = evaluate(room, build(tid, room, sub), sub)
                sizes.append({"room": room.name, "tactic": tid, "team": n, **res.metrics()})
                print(
                    f"team size {n}: {room.name:9s} {tid:11s} "
                    f"R2={res.risk_multi:.3f} T={res.t_clear:.1f}"
                )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(
            {
                "catalog": [
                    {k: v for k, v in dataclasses.asdict(t).items() if k != "build"}
                    for t in CATALOG
                ],
                "rows": rows,
                "team_size": sizes,
            }
        ),
        encoding="utf-8",
    )
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
