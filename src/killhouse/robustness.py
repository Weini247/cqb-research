"""Robustness study: risk and physical validity of each technique under growing execution noise."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from .room import standard_rooms
from .tactics import CATALOG, Noise, build, robust_eval
from .team import default_team

LEVELS = (0.0, 0.5, 1.0, 2.0)  # multiples of the base noise (0.25 s, 0.25 m, 0.15 rad, 10 %)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-robustness")
    ap.add_argument("--k", type=int, default=24, help="noisy executions per cell")
    ap.add_argument("--out", type=Path, default=Path("out/robustness.json"))
    a = ap.parse_args(argv)
    team, base = default_team(), Noise()
    rows = []
    for room in standard_rooms():
        for t in CATALOG:
            pb = build(t.id, room, team)
            for lv in LEVELS:
                nz = Noise(*(v * lv for v in dataclasses.astuple(base)))
                r = robust_eval(room, pb, team, k=1 if lv == 0 else a.k, nz=nz, seed=11)
                rows.append({"room": room.name, "tactic": t.id, "level": lv, **r})
            line = [f"{x['mean']:.2f}/{x['valid_frac']:.2f}" for x in rows[-len(LEVELS) :]]
            print(f"{room.name:13s} {t.id:18s} " + "  ".join(line), flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rows), encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
