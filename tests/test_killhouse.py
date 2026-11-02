import json
import math

import pytest

from killhouse.building import BuildingParams, generate, is_connected
from killhouse.cli import main
from killhouse.replay import to_html, to_replay
from killhouse.sim import Sim
from killhouse.team import default_team


@pytest.mark.parametrize("seed", [0, 1, 7, 42])
def test_building_large_and_connected(seed):
    b = generate(BuildingParams(seed=seed))
    assert (b.w, b.h) == (60, 80)  # 30 x 40 m
    assert len(b.rooms) >= 20
    assert any(r.kind == "corridor" for r in b.rooms)
    assert len(b.entrances) >= 3
    assert is_connected(b)


def test_building_deterministic():
    a, b = generate(BuildingParams(seed=3)), generate(BuildingParams(seed=3))
    assert a.grid == b.grid


def test_team_has_distinct_bodies():
    team = default_team()
    assert len(team) == 4
    assert len({o.radius_m for o in team}) == 4
    assert len({o.height_m for o in team}) == 4


@pytest.mark.parametrize("seed", [1, 7])
def test_episode_clears_every_room(seed):
    b = generate(BuildingParams(seed=seed))
    sim = Sim(b, default_team())
    sim.run()
    assert sim.cleared == {r.id for r in b.rooms}
    kinds = [e["kind"] for e in sim.events]
    assert kinds.count("stack") == len(b.rooms)
    assert kinds[-1] == "done"
    # operators never stand inside a wall
    for f in sim.frames:
        for x, y, *_ in f["ops"]:
            cx, cy = math.floor(x / 0.5), math.floor(y / 0.5)
            if 0 <= cx < b.w and 0 <= cy < b.h:
                assert b.grid[cy][cx] == 0


def test_replay_and_html(tmp_path):
    main(["--seed", "7", "--out", str(tmp_path)])
    rep = json.loads((tmp_path / "replay.json").read_text(encoding="utf-8"))
    assert rep["schema"] == "killhouse.replay/1"
    assert len(rep["operators"]) == 4 and len(rep["frames"]) > 100
    html = (tmp_path / "replay.html").read_text(encoding="utf-8")
    assert "/*__REPLAY__*/null" not in html and '"killhouse.replay/1"' in html
    assert to_html(to_replay(generate(BuildingParams(seed=1)), _ran(1))).startswith("<!doctype")


def _ran(seed):
    s = Sim(generate(BuildingParams(seed=seed)), default_team())
    s.run()
    return s
