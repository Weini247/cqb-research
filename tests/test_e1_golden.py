"""Golden test: main must still reproduce the archived E1 numbers (study frozen at e1-prereg).

It re-evaluates the techniques and the selected plans of a few E1 rooms on the held-out scenarios
and compares them with data/e1. A failure means a change altered the E1 model or its scenarios.
"""

import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from killhouse.doctrine import doctrines
from killhouse.entry import E1_CFG, evaluate
from killhouse.optimize import OBJECTIVE, decode
from killhouse.room import generated_rooms
from killhouse.team import default_team

DATA = Path(__file__).resolve().parents[1] / "data" / "e1" / "results.json.gz"
ROOMS = ("G2026-00", "G2026-17", "G2026-31")


@pytest.fixture(scope="module")
def e1():
    return {r["room"]["name"]: r for r in json.loads(gzip.open(DATA).read())["rooms"]}


@pytest.mark.parametrize("name", ROOMS)
def test_e1_room_reproduces(e1, name):
    team = default_team()
    room = next(r for r in generated_rooms(2026, 40) if r.name == name)
    assert room.to_dict() == {**e1[name]["room"], "obstacles": [list(b) for b in room.obstacles]}
    pbs = {pb.name: pb for pb in doctrines(room, team)}
    checked = 0
    for d in e1[name]["doctrines"]:
        res = evaluate(room, pbs[d["name"]], team, cfg=E1_CFG)
        assert res.feasible == d["feasible"], d["name"]
        if not d["feasible"]:
            continue
        assert res.objective(OBJECTIVE) == pytest.approx(d["risk_exact"], abs=1e-9)
        sel = evaluate(room, decode(np.array(d["x_selected"]), room, team), team, cfg=E1_CFG)
        assert sel.objective(OBJECTIVE) == pytest.approx(d["selected_risk"], abs=1e-9)
        checked += 1
    assert checked >= 1
