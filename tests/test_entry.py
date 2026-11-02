import dataclasses
import json

import numpy as np

from killhouse.bench import main as bench_main
from killhouse.doctrine import doctrines
from killhouse.entry import ModelCfg, OpPlan, Playbook, evaluate
from killhouse.optimize import Archive, cem, decode, encode, score
from killhouse.room import Room, los, standard_rooms
from killhouse.team import default_team

TEAM = default_team()
ROOM = Room("t", 5.0, 5.0, 2.05, 2.95)


def test_los_through_door_only():
    q = np.array([[2.5, 2.0], [0.5, 0.5], [4.5, 0.5]])
    v = los(ROOM, np.array([[2.5, -1.0]]), q)[0]
    assert v.tolist() == [True, False, False]  # straight through yes, hidden corners no
    assert los(ROOM, np.array([[2.5, 1.0]]), q).all()  # convex room: inside sees all


def test_wall_thickness_blocks_oblique_view():
    beside = np.array([[ROOM.door_x0 - 0.35, -0.5]])  # stacked next to the door frame
    thin = Room("thin", 5.0, 5.0, 2.05, 2.95, wall_t=0.001)
    thick_frac = los(ROOM, beside, ROOM.points()).mean()
    assert thick_frac < 0.15
    assert thick_frac < 0.8 * los(thin, beside, thin.points()).mean()


def test_obstacle_blocks_los():
    room = Room("box", 5.0, 5.0, 2.05, 2.95, ((2.0, 2.0, 3.0, 2.5),))
    v = los(room, np.array([[2.5, 1.0]]), np.array([[2.5, 4.0], [0.5, 4.0]]))[0]
    assert v.tolist() == [False, True]


def test_doctrines_valid_on_empty_rooms():
    for room in standard_rooms():
        if room.obstacles:
            continue
        for pb in doctrines(room, TEAM):
            res = evaluate(room, pb, TEAM)
            assert res.collision < 0.02 and res.wall < 0.02, (room.name, pb.name)
        assert any(evaluate(room, pb, TEAM).feasible for pb in doctrines(room, TEAM)), room.name


def test_staying_outside_never_clears():
    pb = Playbook(
        "outside", [OpPlan(s, k, enter=False) for s, k in [(-1, 0), (1, 0), (-1, 1), (1, 1)]]
    )
    res = evaluate(ROOM, pb, TEAM)
    assert not res.feasible and res.uncleared_end > 0.1


def test_encode_decode_roundtrip():
    pb = doctrines(ROOM, TEAM)[0]
    pb2 = decode(encode(pb, ROOM, TEAM), ROOM, TEAM)
    for a, b in zip(pb.ops, pb2.ops, strict=True):
        assert np.allclose(a.pod, b.pod, atol=1e-6) and a.enter == b.enter


def test_optimizer_not_worse_than_seed():
    init = [encode(pb, ROOM, TEAM) for pb in doctrines(ROOM, TEAM)]
    arch = Archive()
    _, best = cem(ROOM, TEAM, 0.2, init, arch, iters=3, pop=8)
    seed_scores = []
    for x in init:
        r = evaluate(ROOM, decode(x, ROOM, TEAM), TEAM)
        seed_scores.append(score(r, 0.2))
    assert best <= min(seed_scores) + 1e-9
    assert arch.front()


def test_bench_quick(tmp_path):
    bench_main(["--quick", "--rooms", "S-center", "--out", str(tmp_path)])
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    room = data["rooms"][0]
    assert len(room["doctrines"]) == 4 and room["front"]
    assert "/*__DATA__*/null" not in (tmp_path / "report.html").read_text(encoding="utf-8")
    html3d = (tmp_path / "viewer3d.html").read_text(encoding="utf-8")
    assert "/*__DATA__*/null" not in html3d and "three@0.160.0" in html3d
    assert '"cloud"' not in html3d  # viewer payload is stripped to what it renders


def test_threat_model_rewards_more_guns_and_faster_engagement():
    pb = doctrines(ROOM, TEAM)[0]
    two = Playbook("2", [dataclasses.replace(o, enter=i < 2) for i, o in enumerate(pb.ops)])
    four, pair = evaluate(ROOM, pb, TEAM), evaluate(ROOM, two, TEAM)
    assert 0.0 < four.risk < 1.0
    assert four.risk <= pair.risk  # extra entrants help neutralize, they are not pure exposure
    fast = evaluate(ROOM, pb, TEAM, cfg=ModelCfg(engage_rate=8.0))
    slow = evaluate(ROOM, pb, TEAM, cfg=ModelCfg(engage_rate=2.0))
    assert fast.risk < four.risk < slow.risk


def test_kendall_and_variants():
    from killhouse.sensitivity import _variant, kendall

    assert kendall({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2, "c": 3}) == 1.0
    assert kendall({"a": 1, "b": 2}, {"a": 2, "b": 1}) == -1.0
    _, rooms, _ = _variant("door_w", 1.2)
    assert all(abs((r.door_x1 - r.door_x0) - 1.2) < 1e-9 for r in rooms)


def test_multi_threat_values_full_team():
    """Regression test: protects the implemented multi-threat engagement rule. It is NOT
    evidence for prereg H4 (review R3: a test that fixes an outcome cannot confirm it)."""
    room = standard_rooms()[2]  # M-center
    pb = doctrines(room, TEAM)[0]
    two = Playbook("2", [dataclasses.replace(o, enter=i < 2) for i, o in enumerate(pb.ops)])
    four, pair = evaluate(room, pb, TEAM), evaluate(room, two, TEAM)
    assert four.risk_multi < pair.risk_multi - 0.02  # a second threat needs a second gun
    assert four.risk <= four.risk_multi


def test_dead_space_step_clears_furniture_room():
    room = next(r for r in standard_rooms() if r.name == "M-center-box")
    pbs = doctrines(room, TEAM)
    assert all(evaluate(room, pb, TEAM).feasible for pb in pbs)
    assert all(any(o.pod2 for o in pb.ops) for pb in pbs)


def test_generated_rooms_deterministic_and_sane():
    from killhouse.room import generated_rooms

    a, b = generated_rooms(3, 6), generated_rooms(3, 6)
    assert a == b and len({r.name for r in a}) == 6
    for r in a:
        assert 0 < r.door_x0 < r.door_x1 <= r.w and len(r.points()) > 50


def test_information_model_plans_never_see_sampled_threats(monkeypatch):
    """Playbooks (incl. the dead-space step) may use the floorplan, never threat placements."""
    import killhouse.entry as entry_mod

    room = next(r for r in standard_rooms() if r.name == "M-center-box")
    base = [pb.ops for pb in doctrines(room, TEAM)]
    rng = np.random.default_rng(99)
    monkeypatch.setattr(
        entry_mod,
        "threat_sets",
        lambda room, m, cfg: rng.integers(0, m, size=(cfg.n_scenarios, cfg.n_threats)),
    )
    assert [pb.ops for pb in doctrines(room, TEAM)] == base


def test_planning_and_evaluation_scenarios_differ():
    from killhouse.entry import DEFAULT_CFG, EVAL_CFG, threat_sets

    a, b = threat_sets(ROOM, 200, DEFAULT_CFG), threat_sets(ROOM, 200, EVAL_CFG)
    assert a.shape == b.shape and not np.array_equal(a, b)
    pb = doctrines(ROOM, TEAM)[0]
    r0, r1 = evaluate(ROOM, pb, TEAM), evaluate(ROOM, pb, TEAM, cfg=EVAL_CFG)
    assert r0.risk == r1.risk  # the single-threat risk is an exact expectation, no sampling
