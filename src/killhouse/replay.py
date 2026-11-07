"""Replay format `killhouse.replay/2`: the contract between simulation and viewer.

The viewer only interprets what is in here; it never invents state. Conventions are written into
every document (see docs/CONVENTIONS.md). Version 1 was used by the removed spike-1 prototype.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = "killhouse.replay/2"
CONVENTIONS = {
    "length": "m",
    "angle": "rad, 0 = +x, counter-clockwise",
    "time": "s from episode start",
    "axes": "x right, y forward (into the building); viewer: three.js y up, z = -y",
    "precision": "positions 0.01 m and angles 0.01 rad in v0.2 sources",
}


def _events(rp: dict) -> list[dict]:
    ev = []
    if rp["metrics"].get("t_clear") is not None:
        ev.append({"t": rp["metrics"]["t_clear"], "type": "cleared"})
    for i, to in enumerate(rp.get("door_open", [])):
        if to >= 0:
            ev.append({"t": to, "type": "door_open", "door": i})
    return sorted(ev, key=lambda e: e["t"])


def _run(rp: dict) -> dict:
    pos, gaze = np.asarray(rp["pos"], float), np.asarray(rp["gaze"], float)
    return {
        "name": rp["name"],
        "metrics": rp["metrics"],
        "steps": len(pos),
        "agents": [
            {
                "x": pos[:, i, 0].tolist(),
                "y": pos[:, i, 1].tolist(),
                "heading": gaze[:, i].tolist(),
                "attention": gaze[:, i].tolist(),
            }
            for i in range(pos.shape[1])
        ],
        "first_seen": rp["first_seen"],
        "markers": rp.get("markers", []),
        "events": _events(rp),
    }


def from_results(results: dict, source: str) -> dict:
    """Replay document from the results of `killhouse-bench` or `killhouse-apartment`."""
    cfg = results["config"]
    return {
        "schema": SCHEMA,
        "conventions": CONVENTIONS,
        "dt": cfg["dt"],
        "model": {
            "half_fov_deg": cfg["half_fov_deg"],
            "objective": cfg.get("objective", "risk"),
            # model v0.2 has one angle per agent: body, view and attention coincide
            "attention_equals_heading": True,
        },
        "provenance": {
            "source": source,
            "results_schema": results.get("schema"),
            "commit": cfg.get("commit"),
        },
        "agents": results["team"],
        "scenes": [
            {
                "environment": r["room"],
                "points": r["points"],
                "runs": [_run(rp) for rp in r["replays"]],
            }
            for r in results["rooms"]
        ],
    }


def validate(doc: dict) -> list[str]:
    """Problems in a replay document; empty if it is valid."""
    err = []
    if doc.get("schema") != SCHEMA:
        err.append(f"schema is {doc.get('schema')!r}, expected {SCHEMA!r}")
    if not doc.get("dt", 0) > 0:
        err.append("dt must be positive")
    n = len(doc.get("agents", []))
    for s, scene in enumerate(doc.get("scenes", [])):
        m = len(scene["points"])
        for run in scene["runs"]:
            where = f"scene {s} run {run['name']!r}"
            if len(run["agents"]) != n:
                err.append(f"{where}: {len(run['agents'])} agent tracks for {n} agents")
            for a in run["agents"]:
                lens = {len(a[k]) for k in ("x", "y", "heading", "attention")}
                if lens != {run["steps"]}:
                    err.append(f"{where}: track lengths {sorted(lens)} != steps {run['steps']}")
                if not all(
                    math.isfinite(v) for k in ("x", "y", "heading", "attention") for v in a[k]
                ):
                    err.append(f"{where}: non-finite values")
            if len(run["first_seen"]) != m:
                err.append(
                    f"{where}: first_seen has {len(run['first_seen'])} entries for {m} points"
                )
            end = (run["steps"] - 1) * doc["dt"]
            for e in run["events"]:
                if not 0 <= e["t"] <= end + 1e-9:
                    err.append(f"{where}: event {e['type']} at {e['t']} s outside 0..{end:.1f} s")
    return err


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-replay")
    ap.add_argument("results", type=Path, help="results.json of killhouse-bench or -apartment")
    ap.add_argument("--out", type=Path, help="default: replay.json next to the input")
    a = ap.parse_args(argv)
    doc = from_results(json.loads(a.results.read_text(encoding="utf-8")), a.results.name)
    problems = validate(doc)
    if problems:
        raise SystemExit("invalid replay:\n" + "\n".join(problems))
    out = a.out or a.results.with_name("replay.json")
    out.write_text(json.dumps(doc), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
