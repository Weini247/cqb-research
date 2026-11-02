"""`killhouse` command: building + episode + replay JSON + HTML viewer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .building import BuildingParams, generate
from .replay import to_html, to_replay
from .sim import Sim
from .team import default_team


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--width", type=float, default=30.0, help="building width in m")
    ap.add_argument("--height", type=float, default=40.0, help="building depth in m")
    ap.add_argument("--entrances", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path("out"))
    a = ap.parse_args(argv)

    b = generate(
        BuildingParams(width_m=a.width, height_m=a.height, n_entrances=a.entrances, seed=a.seed)
    )
    sim = Sim(b, default_team())
    sim.run()
    rep = to_replay(b, sim)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "replay.json").write_text(json.dumps(rep), encoding="utf-8")
    (a.out / "replay.html").write_text(to_html(rep), encoding="utf-8")
    n_corr = sum(r.kind == "corridor" for r in b.rooms)
    print(
        f"building {a.width:g}x{a.height:g} m: {len(b.rooms) - n_corr} rooms, {n_corr} corridors, "
        f"{len(b.doors) - len(b.entrances)} doors, {len(b.entrances)} entrances"
    )
    print(f"episode {rep['meta']['duration_s']:.1f} s, {len(sim.frames)} frames -> {a.out}")


if __name__ == "__main__":
    main()
