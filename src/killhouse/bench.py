"""E0 benchmark: doctrines vs best-found strategies per room -> results.json + report.html.

Runs single-process (other experiments may share the CPU).
"""

from __future__ import annotations

import argparse
import json
import time
from importlib import resources
from pathlib import Path

import numpy as np

from . import entry
from .doctrine import doctrines
from .entry import Playbook, Result, evaluate
from .optimize import Archive, cem, decode, encode
from .room import Room, standard_rooms
from .team import default_team

WEIGHTS = (0.01, 0.03, 0.1, 0.3)


def _replay(room: Room, name: str, pb: Playbook, res: Result) -> dict:
    return {
        "name": name,
        "metrics": res.metrics(),
        "pos": np.round(res.pos, 2).tolist(),
        "gaze": np.round(res.gaze, 2).tolist(),
        "first_seen": res.first_seen.tolist(),
        "plan": [
            {"enter": o.enter, "delay": round(o.delay, 2), "pod": [round(v, 2) for v in o.pod]}
            for o in pb.ops
        ],
    }


def bench_room(room: Room, team, iters: int, pop: int, seed: int, log=print) -> dict:
    docs = doctrines(room, team)
    archive = Archive()
    doc_out, replays = [], []
    for pb in docs:
        res = evaluate(room, pb, team, keep=True)
        archive.add(res, encode(pb, room, team))
        doc_out.append({"name": pb.name, **res.metrics()})
        replays.append(_replay(room, pb.name, pb, res))
    init = [encode(pb, room, team) for pb in docs]
    for k, w in enumerate(WEIGHTS):
        t0 = time.perf_counter()
        cem(room, team, w, init, archive, iters=iters, pop=pop, seed=seed * 100 + k)
        dt = time.perf_counter() - t0
        log(f"  {room.name} w={w}: {len(archive.rows)} valid evals ({dt:.0f}s)")
    for d in doc_out:
        if d["feasible"]:
            d.update(archive.gap(d["risk"], d["t_clear"], d["fratricide"]))
    # "best found" replay: knee of the front at fratricide <= the safest valid doctrine
    valid = [d for d in doc_out if d["feasible"]]
    fr_cap = min((d["fratricide"] for d in valid), default=float("inf"))
    knee_front = archive.front(fr_cap) or archive.front()
    if knee_front:
        e0 = min(archive.rows[i][0] for i in knee_front)
        t0 = min(archive.rows[i][1] for i in knee_front)
        i = min(knee_front, key=lambda i: archive.rows[i][0] / e0 + archive.rows[i][1] / t0)
        pb = decode(archive.xs[i], room, team)
        res = evaluate(room, pb, team, keep=True)
        replays.append(_replay(room, "best found (knee)", pb, res))
    front_idx = archive.front()
    front = [list(archive.rows[i]) for i in front_idx]
    front_plans = [
        {
            "metrics": [round(v, 4) for v in archive.rows[i]],
            "x": np.round(archive.xs[i], 4).tolist(),
        }
        for i in front_idx
    ]
    rng = np.random.default_rng(0)
    pick = rng.choice(len(archive.rows), size=min(400, len(archive.rows)), replace=False)
    cloud = [[round(v, 3) for v in archive.rows[i]] for i in pick]
    return {
        "room": room.to_dict(),
        "points": room.points().round(3).tolist(),
        "doctrines": doc_out,
        "front": [[round(v, 4) for v in r] for r in front],
        "front_plans": front_plans,
        "cloud": cloud,
        "n_valid": len(archive.rows),
        "replays": replays,
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-bench")
    ap.add_argument("--quick", action="store_true", help="tiny budget for smoke tests")
    ap.add_argument("--rooms", nargs="*", help="room names (default: all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("out/bench"))
    a = ap.parse_args(argv)
    iters, pop = (4, 12) if a.quick else (30, 32)
    team = default_team()
    rooms = [r for r in standard_rooms() if not a.rooms or r.name in a.rooms]
    t0 = time.perf_counter()
    results = []
    for room in rooms:
        print(f"{room.name} ...", flush=True)
        results.append(
            bench_room(room, team, iters, pop, a.seed, log=lambda s: print(s, flush=True))
        )
    data = {
        "schema": "killhouse.bench/0",
        "config": {
            "iters": iters,
            "pop": pop,
            "weights": WEIGHTS,
            "seed": a.seed,
            "dt": entry.DT,
            "horizon": entry.HORIZON,
            "half_fov_deg": round(np.degrees(entry.HALF_FOV), 1),
            "dwell": entry.DWELL,
            "turn_rate": entry.TURN_RATE,
            "threat_react": entry.DEFAULT_CFG.threat_react,
            "threat_rate": entry.DEFAULT_CFG.threat_rate,
            "engage_rate": entry.DEFAULT_CFG.engage_rate,
            "clear_frac": entry.CLEAR_FRAC,
            "runtime_s": round(time.perf_counter() - t0, 1),
        },
        "team": [o.to_dict() for o in team],
        "rooms": results,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "results.json").write_text(json.dumps(data), encoding="utf-8")
    tpl = resources.files("killhouse").joinpath("report.html").read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    (a.out / "report.html").write_text(tpl.replace("/*__DATA__*/null", payload), encoding="utf-8")
    print(f"\n{'room':14s} {'doctrine':20s} {'R':>6s} {'T':>5s} {'fr':>4s} {'R*':>6s} {'gapR':>5s}")
    for r in results:
        for d in r["doctrines"]:
            if d["feasible"]:
                print(
                    f"{r['room']['name']:14s} {d['name']:20s} {d['risk']:6.3f} "
                    f"{d['t_clear']:5.1f} {d['fratricide']:4.1f} {d['risk_best']:6.3f} "
                    f"{d['gap_risk'] * 100:4.0f}%"
                )
            else:
                print(f"{r['room']['name']:14s} {d['name']:20s} invalid (not cleared / collision)")
    print(f"-> {a.out} ({data['config']['runtime_s']} s)")


if __name__ == "__main__":
    main()
