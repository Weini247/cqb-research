import json

import numpy as np
import pytest

from killhouse.apartment import generate_apartment
from killhouse.clearing import Frame, evaluate_episode, main, objectives, run_clearing
from killhouse.geom import Grid, los_boxes, visibility
from killhouse.team import default_team


@pytest.mark.parametrize("seed", range(6))
def test_apartment_connected_and_sane(seed):
    ap = generate_apartment(seed)
    names = [n for n, _ in ap.fp.regions]
    assert names[0] == "Flur" and len(names) >= 5
    assert {k for k, _ in objectives(ap)} == set(range(len(names)))  # every room reachable
    assert ap.entrance.frm == -1 and len(ap.fp.points()) > 300
    assert generate_apartment(seed).fp.walls == ap.fp.walls


def test_frame_roundtrip_and_door_interval():
    ap = generate_apartment(1)
    p = np.array([[0.3, 0.4], [1.7, 2.2]])
    for d in ap.doors:
        fr = Frame(ap, d)
        assert np.allclose(fr.to_local(fr.to_world(p)), p)
        assert 0 <= fr.dx[0] < fr.dx[1] <= fr.w + 1e-9
        assert fr.local_room(ap, d.name).obstacles  # at least the open door leaf


def test_walls_block_sight_between_rooms():
    ap = generate_apartment(1)
    landing = np.array([[(ap.entrance.a + ap.entrance.b) / 2 - 1.5, -1.5]])
    reg = ap.fp.region_of(q := ap.fp.points())
    vis = los_boxes(landing, q, ap.fp.blockers)[0]
    side_rooms = [k for k, (n, _) in enumerate(ap.fp.regions) if n not in ("Flur", "Wohnzimmer")]
    assert not vis[np.isin(reg, side_rooms)].any()


def test_full_clearing_episode():
    ap, team = generate_apartment(5), default_team()
    grid = Grid(ap.fp)
    q = ap.fp.points()
    ep = run_clearing(ap, team, "crisscross", grid)
    met = evaluate_episode(ap, ep, grid, visibility(ap.fp, grid, q), q)
    assert met["feasible"] and all(v is not None for v in met["room_clear_s"].values())
    assert 0 < met["risk"] <= met["risk_multi"] < 1
    assert [s["room"] for s in ep.steps][0] == "Flur"
    # the team never stands inside a wall (body centres stay on walkable cells)
    assert grid.walk_free[grid.index(ep.pos[::5])].mean() > 0.97


def test_cli_exports_viewer(tmp_path):
    main(["--seeds", "5", "--techniques", "crisscross", "--out", str(tmp_path)])
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert data["rooms"][0]["room"]["kind"] == "apartment"
    html = (tmp_path / "viewer3d.html").read_text(encoding="utf-8")
    assert "/*__DATA__*/null" not in html and '"boxes"' in html


def test_closed_doors_block_sight_until_opened():
    from killhouse.clearing import closed_door_masks, run

    ap = generate_apartment(5, closed_frac=1.0)
    assert all(d.closed for d in ap.doors)
    grid = Grid(ap.fp)
    q = ap.fp.points()
    masks = closed_door_masks(ap, grid, q)
    vmat = visibility(ap.fp, grid, q)
    ep = run_clearing(ap, default_team(), "crisscross", grid)
    closed = evaluate_episode(ap, ep, grid, vmat, q, closed_masks=masks)
    opened = evaluate_episode(ap, ep, grid, vmat, q)
    assert closed["exposure"] < opened["exposure"]
    assert set(ep.door_open) == set(range(len(ap.doors)))  # every door gets opened
    sc = run(5, ["crisscross"], closed_frac=1.0)
    assert sc["replays"][0]["markers"] and sc["room"]["doors"][0]["closed"]


def test_pass_through_window_blocks_walking_not_sight():
    ap = next(a for a in (generate_apartment(s) for s in range(12)) if a.fp.windows)
    grid = Grid(ap.fp)
    x0, y0, x1, y1 = ap.fp.windows[0]
    c = grid.index(np.array([(x0 + x1) / 2, (y0 + y1) / 2]))
    assert not grid.walk_free[c] and grid.see_free[c]
