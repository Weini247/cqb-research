"""Residence generator (v0.4) and furniture heights."""

import numpy as np
import pytest

from killhouse.geom import SIGHT_H, Floorplan, Grid, visibility
from killhouse.house import all_rooms_reachable
from killhouse.residence import generate_residence
from killhouse.sim2.core import SearchParams, run_search, scenario
from killhouse.team import default_team

SEEDS = range(12)
REQUIRED = {
    "Diele",
    "Flur",
    "Gang",
    "Schlafzimmer",
    "Bad en suite",
    "Ankleide",
    "Wohnzimmer",
    "Esszimmer",
    "Küche",
    "Hauswirtschaft",
    "WC",
    "Bad",
}


@pytest.fixture(scope="module")
def homes():
    return [generate_residence(s) for s in SEEDS]


def overlap(a, b, eps=1e-6):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def test_low_furniture_blocks_bodies_but_not_sight_tall_furniture_blocks_both():
    sofa, wardrobe = (2.0, 2.0, 3.0, 2.6), (5.0, 2.0, 6.0, 2.6)
    fp = Floorplan(
        bounds=(0.0, 0.0, 8.0, 5.0),
        walls=[],
        furniture=[wardrobe],
        low=[sofa],
        regions=[("R", (0.0, 0.0, 8.0, 5.0))],
        walkable=[(0.0, 0.0, 8.0, 5.0)],
    )
    g = Grid(fp)
    q = np.array([[2.5, 3.6], [5.5, 3.6]])  # right behind the sofa / behind the wardrobe
    seen_from_sofa_side = visibility(fp, g, q)[g.index(np.array([2.5, 0.8]))]
    seen_from_wardrobe_side = visibility(fp, g, q)[g.index(np.array([5.5, 0.8]))]
    assert seen_from_sofa_side[0] and not seen_from_wardrobe_side[1]
    # bodies cannot stand in either piece
    assert (
        not g.walk_free[g.index(np.array([2.5, 2.3]))]
        and not g.walk_free[g.index(np.array([5.5, 2.3]))]
    )


def test_residences_are_deterministic_have_the_full_programme_and_are_reachable(homes):
    assert generate_residence(4).to_dict() == homes[4].to_dict()
    for h in homes:
        names = {n for n, _ in h.fp.regions}
        assert REQUIRED <= names, (h.name, REQUIRED - names)
        assert all_rooms_reachable(h), h.name


def test_both_orientations_and_garages_occur(homes):
    garage_right = [
        dict(h.fp.regions)["Garage"][0] > dict(h.fp.regions)["Diele"][0]
        for h in homes
        if "Garage" in dict(h.fp.regions)
    ]
    assert True in garage_right and False in garage_right


def test_furniture_is_typed_split_by_height_and_stays_in_rooms(homes):
    for h in homes:
        rooms = [r for _, r in h.fp.regions]
        assert {b for _, b, ht in h.fp.items if ht >= SIGHT_H} == set(h.fp.furniture)
        assert {b for _, b, ht in h.fp.items if ht < SIGHT_H} == set(h.fp.low)
        for kind, b, _ in h.fp.items:
            assert any(
                r[0] - 1e-6 <= b[0]
                and b[2] <= r[2] + 1e-6
                and r[1] - 1e-6 <= b[1]
                and b[3] <= r[3] + 1e-6
                for r in rooms
            ), (h.name, kind)
            assert not any(overlap(b, lf) for lf in h.fp.doors), (h.name, kind)
        if "Garage" in dict(h.fp.regions):
            assert any(k == "car" for k, _, _ in h.fp.items), h.name


def test_windows_sit_in_exterior_walls(homes):
    # a room on exactly one side of the window, nothing on the other (L-shaped footprints too)
    for h in homes:
        for w in h.fp.windows:
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
            horizontal = w[2] - w[0] > w[3] - w[1]
            probe = np.array(
                [[cx, cy - 0.4], [cx, cy + 0.4]] if horizontal else [[cx - 0.4, cy], [cx + 0.4, cy]]
            )
            inside = h.fp.region_of(probe) >= 0
            assert inside.sum() == 1, (h.name, w)


def test_four_agents_search_a_residence_with_closed_doors():
    sc = scenario(2, "residence", closed_frac=0.6)
    r = run_search(sc, default_team(), SearchParams(delay=1.0, max_time=240))
    assert r["metrics"]["feasible"] and r["metrics"]["doors_opened"] >= 1
