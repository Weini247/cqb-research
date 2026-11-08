"""House generator (v0.3-d): invariants, visibility on the GPU, time and memory budget."""

import time

import numpy as np
import pytest

from killhouse.apartment import generate_apartment
from killhouse.geom import Grid, visibility, visibility_fast
from killhouse.house import all_rooms_reachable, generate_house
from killhouse.sim2.core import SearchParams, run_search, scenario
from killhouse.team import default_team

SEEDS = range(16)
HALLS = ("Flur", "Diele")


@pytest.fixture(scope="module")
def houses():
    return [generate_house(s) for s in SEEDS]


def overlap(a, b, eps=1e-6):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def inside(a, b, eps=1e-6):
    return a[0] >= b[0] - eps and a[1] >= b[1] - eps and a[2] <= b[2] + eps and a[3] <= b[3] + eps


def test_houses_are_deterministic_and_of_both_kinds(houses):
    assert generate_house(3).to_dict() == houses[3].to_dict()
    assert {h.fp.regions[0][0] for h in houses} == {"Flur", "Diele"}  # spine and tee layouts


def test_room_count_and_every_room_reachable(houses):
    for h in houses:
        n = sum(name not in HALLS for name, _ in h.fp.regions)
        assert 8 <= n <= 15, (h.name, n)
        assert all_rooms_reachable(h), h.name


def test_rooms_do_not_overlap_and_furniture_stays_inside_rooms(houses):
    for h in houses:
        rooms = [r for _, r in h.fp.regions]
        assert not any(overlap(a, b) for i, a in enumerate(rooms) for b in rooms[i + 1 :]), h.name
        for f in h.fp.furniture:
            assert any(inside(f, r) for r in rooms), (h.name, f)
            assert not any(overlap(f, lf) for lf in h.fp.doors), (h.name, f)


def test_doors_sit_in_walls_between_their_two_rooms(houses):
    for h in houses:
        rooms = [r for _, r in h.fp.regions]
        for d in h.doors:
            gx0, gy0, gx1, gy1 = d.gap
            assert not any(overlap(d.gap, w) for w in h.fp.walls), (h.name, d.name)
            into = rooms[d.into]
            # the gap touches the entered room on the side named by the door
            edge = {"bottom": into[1], "top": into[3], "left": into[0], "right": into[2]}[d.side]
            span = (gy0, gy1) if d.side in ("bottom", "top") else (gx0, gx1)
            assert span[0] - 1e-6 <= edge <= span[1] + 1e-6, (h.name, d.name)


def test_gpu_visibility_equals_the_reference():
    for ap in (generate_apartment(2), generate_house(1)):
        g = Grid(ap.fp)
        q = ap.fp.points()
        assert np.array_equal(visibility_fast(ap.fp, g, q), visibility(ap.fp, g, q))


def test_a_house_fits_the_time_and_memory_budget_and_gets_cleared():
    t0 = time.perf_counter()
    sc = scenario(6, "house")
    run = run_search(sc, default_team(), SearchParams(delay=1.0, max_time=240))
    elapsed = time.perf_counter() - t0
    assert sc.vis.nbytes < 50e6  # dense visibility stays small enough for houses of this size
    assert elapsed < 120  # also on the numpy fallback
    assert run["metrics"]["feasible"]
