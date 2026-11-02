"""Replay JSON export and standalone HTML viewer."""

from __future__ import annotations

import json
from importlib import resources

from .building import CELL, Building
from .sim import Sim

SCHEMA = "killhouse.replay/1"


def to_replay(b: Building, sim: Sim) -> dict:
    return {
        "schema": SCHEMA,
        "meta": {"seed": b.params.seed, "duration_s": sim.frames[-1]["t"]},
        "building": {
            "cell_m": CELL,
            "width_cells": b.w,
            "height_cells": b.h,
            "grid": ["".join("#" if c else "." for c in row) for row in b.grid],
            "rooms": [
                {"id": r.id, "kind": r.kind, "x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1}
                for r in b.rooms
            ],
            "doors": [{"a": d.a, "b": d.b, "cells": d.cells} for d in b.doors],
        },
        "operators": [o.op.to_dict() for o in sim.ops],
        "events": sim.events,
        "frames": sim.frames,
    }


def to_html(replay: dict) -> str:
    template = resources.files("killhouse").joinpath("viewer.html").read_text(encoding="utf-8")
    data = json.dumps(replay, separators=(",", ":")).replace("</", "<\\/")
    return template.replace("/*__REPLAY__*/null", data)
