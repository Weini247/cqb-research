"""M2b: does the optimizer's answer depend on its seed and budget? (gap per doctrine)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .bench import bench_room
from .room import standard_rooms
from .team import default_team

BUDGETS = ((20, 32), (30, 64), (60, 64), (60, 128))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-saturation")
    ap.add_argument("--rooms", nargs="+", default=["M-center", "M-corner", "L-center"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path("out/saturation.json"))
    a = ap.parse_args(argv)
    team, rows = default_team(), []
    rooms = [r for r in standard_rooms() if r.name in a.rooms]
    for room in rooms:
        for iters, pop in BUDGETS:
            for seed in range(a.seeds):
                t0 = time.perf_counter()
                res = bench_room(room, team, iters, pop, seed, log=lambda s: None)
                for d in res["doctrines"]:
                    if d["feasible"]:
                        rows.append(
                            {
                                "room": room.name,
                                "iters": iters,
                                "pop": pop,
                                "seed": seed,
                                "doctrine": d["name"],
                                "gap": d["gap_selected"],
                                "selected_risk": d["selected_risk"],
                                "risk": d["risk_multi"],
                            }
                        )
                print(
                    f"{room.name} {iters}x{pop} seed {seed}: "
                    + " ".join(
                        f"{d['gap_selected']:+.2f}" for d in res["doctrines"] if d["feasible"]
                    )
                    + f"  ({time.perf_counter() - t0:.0f}s)",
                    flush=True,
                )
                a.out.parent.mkdir(parents=True, exist_ok=True)
                a.out.write_text(json.dumps(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
