import numpy as np
import pytest

from killhouse.entry import evaluate
from killhouse.room import standard_rooms
from killhouse.tactics import BY_ID, CATALOG, Noise, build, perturb, robust_eval
from killhouse.team import default_team

TEAM = default_team()
ROOMS = {r.name: r for r in standard_rooms()}


def test_catalog_entries_are_documented():
    assert len({t.id for t in CATALOG}) == len(CATALOG) >= 8
    for t in CATALOG:
        assert t.sources and t.status in ("coded from source", "adapted", "SME confirmed")


@pytest.mark.parametrize("tid", [t.id for t in CATALOG])
def test_every_tactic_is_physically_valid_in_open_rooms(tid):
    for name in ("M-center", "L-corner"):
        room = ROOMS[name]
        res = evaluate(room, build(tid, room, TEAM), TEAM)
        assert res.collision < 0.02 and res.wall < 0.02, (tid, name)


def test_single_side_stack_and_two_man_roles():
    room = ROOMS["M-center"]
    combo = build("combination-cross", room, TEAM)
    assert {o.side for o in combo.ops} == {-1} and [o.slot for o in combo.ops] == [0, 1, 2, 3]
    assert [o.enter for o in build("two-man", room, TEAM).ops] == [True, True, False, False]
    small = ROOMS["S-center"]
    assert [o.enter for o in build("combination-cross", small, TEAM).ops] == [
        True,
        True,
        False,
        False,
    ]


def test_deliberate_is_slower_than_dynamic():
    room = ROOMS["M-center"]
    slow = evaluate(room, build("deliberate", room, TEAM), TEAM)
    fast = evaluate(room, build("crisscross", room, TEAM), TEAM)
    assert slow.t_clear > fast.t_clear + 1.0


def test_team_sizes():
    room = ROOMS["M-center"]
    r = [
        evaluate(room, build("crisscross", room, TEAM[:n]), TEAM[:n]).risk_multi for n in (2, 3, 4)
    ]
    assert r[2] <= r[0]  # four operators are never worse than two


def test_noise_is_reproducible_and_zero_noise_is_identity():
    room = ROOMS["M-center"]
    pb = build("crisscross", room, TEAM)
    a = robust_eval(room, pb, TEAM, k=3, seed=1)
    assert a == robust_eval(room, pb, TEAM, k=3, seed=1)
    same = perturb(pb, room, np.random.default_rng(0), Noise(0, 0, 0, 0))
    assert evaluate(room, same, TEAM).risk_multi == pytest.approx(
        evaluate(room, pb, TEAM).risk_multi
    )
    assert BY_ID["crisscross"].stack == "split"
