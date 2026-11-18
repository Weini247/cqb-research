"""Training-house generator (v0.4)."""

import pytest

from killhouse.apartment import generate_apartment
from killhouse.geom import SIGHT_H
from killhouse.house import all_rooms_reachable
from killhouse.sim2.core import SearchParams, run_search, scenario
from killhouse.team import default_team
from killhouse.trainhouse import CORRIDOR, generate_trainhouse

SEEDS = range(12)


@pytest.fixture(scope="module")
def houses():
    return [generate_trainhouse(s) for s in SEEDS]


def inside(b, r, eps=1e-6):
    return r[0] - eps <= b[0] and b[2] <= r[2] + eps and r[1] - eps <= b[1] and b[3] <= r[3] + eps


def test_deterministic_reachable_and_marked_as_training_house(houses):
    assert generate_trainhouse(5).to_dict() == houses[5].to_dict()
    for h in houses:
        assert all_rooms_reachable(h), h.name
        assert h.to_dict()["style"] == "trainhouse"
    assert "style" not in generate_apartment(1).to_dict()  # older result files stay identical


def test_rooms_sit_on_a_module_grid_with_corridors(houses):
    for h in houses:
        names = [n for n, _ in h.fp.regions]
        assert (
            any(n.startswith("Gang") for n in names)
            and sum(n.startswith("Raum") for n in names) >= 6
        )
        for n, (x0, y0, x1, y1) in h.fp.regions:
            if n.startswith("Gang"):
                assert min(x1 - x0, y1 - y0) == pytest.approx(CORRIDOR - 0.2, abs=1e-6), (h.name, n)
            else:  # one module or two side by side, walls of 0.2 m taken off
                w, d = x1 - x0 + 0.2, y1 - y0 + 0.2
                m = d
                assert 2.8 - 1e-6 <= m <= 3.2 + 1e-6, (h.name, n, m)
                assert w == pytest.approx(m) or w == pytest.approx(2 * m), (h.name, n, w, m)


def test_doorways_and_doors_and_no_door_leaf_in_a_corridor(houses):
    some_open = some_doors = False
    for h in houses:
        corridors = [r for n, r in h.fp.regions if n.startswith("Gang")]
        interior = [d for d in h.doors if d.frm >= 0]
        some_doors |= bool(interior)
        # more links than doors means open doorways exist
        some_open |= len(h.fp.walls) > 0 and len(interior) < len(h.fp.regions) - 1
        for d in interior:
            assert not any(inside(d.leaf, c) for c in corridors), (h.name, d.name)
    assert some_open and some_doors


def test_sparse_furniture_split_by_height(houses):
    for h in houses:
        kinds = {k for k, _, _ in h.fp.items}
        assert kinds <= {"barrier", "partition"}
        assert {b for _, b, ht in h.fp.items if ht < SIGHT_H} == set(h.fp.low)
        assert len(h.fp.items) <= sum(n.startswith("Raum") for n, _ in h.fp.regions)


def test_four_agents_search_a_training_house():
    sc = scenario(7, "trainhouse", closed_frac=0.5)
    r = run_search(sc, default_team(), SearchParams(delay=1.0, max_time=240))
    assert r["metrics"]["feasible"]
