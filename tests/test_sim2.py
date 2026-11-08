"""Model v0.3 (sim2): information limits, motion limits, determinism and export."""

import math

import numpy as np
import pytest

from killhouse.clearing import OPEN_TIME
from killhouse.entry import DT
from killhouse.replay import from_results, validate
from killhouse.sim2.agents import OPEN, Limits
from killhouse.sim2.core import CONTACT, SearchParams, results, run_search, scenario
from killhouse.sim2.perception import DWELL_STEPS, in_view, sight_steps
from killhouse.team import default_team

TEAM = default_team()


@pytest.fixture(scope="module")
def sc():
    return scenario(3)


@pytest.fixture(scope="module")
def runs(sc):
    return {d: run_search(sc, TEAM, SearchParams(delay=d)) for d in (0.0, 1.0, None)}


def wrap(a):
    return (np.asarray(a) + math.pi) % (2 * math.pi) - math.pi


def test_without_messages_an_agent_knows_only_what_it_saw_itself(sc, runs):
    r = runs[None]
    assert np.array_equal(r["first_known"], r["own_seen"])
    # and its own sightings follow from its exported track (independent batch recomputation);
    # tracks are exported to 0.1 mm, so allow a few boundary points
    pos, att = np.array(r["pos"]), np.array(r["attention"])
    for i in range(len(TEAM)):
        batch = sight_steps(sc.grid, sc.vis, sc.q, pos[:-1, i], att[:-1, i]) + 1
        batch = np.minimum(batch, len(pos))
        assert np.mean(np.abs(batch - np.array(r["own_seen"][i])) <= 1) >= 0.98


@pytest.mark.parametrize("delay", [0.0, 1.0])
def test_with_messages_knowledge_arrives_exactly_one_delay_after_a_teammate_saw_it(runs, delay):
    r = runs[delay]
    own, known = np.array(r["own_seen"]), np.array(r["first_known"])
    lag = max(1, round(delay / DT))
    end = len(r["pos"])
    for i in range(len(TEAM)):
        others = np.delete(own, i, axis=0).min(0) + lag
        assert np.array_equal(known[i], np.minimum(np.minimum(own[i], others), end))


def test_motion_respects_turn_speed_head_and_contact_limits(sc, runs):
    lim = Limits()
    for r in runs.values():
        pos, head, att = np.array(r["pos"]), np.array(r["gaze"]), np.array(r["attention"])
        eps = 2e-3
        assert np.abs(wrap(np.diff(head, axis=0))).max() <= lim.body_turn * DT + eps
        assert (
            np.abs(wrap(np.diff(att, axis=0))).max()
            <= lim.head_turn * DT + lim.body_turn * DT + eps
        )
        assert np.abs(wrap(att - head)).max() <= lim.head_range + eps
        step = np.linalg.norm(np.diff(pos, axis=0), axis=2)
        assert (step <= np.array([o.speed_mps for o in TEAM]) * DT + eps).all()
        for i in range(len(TEAM)):
            for j in range(i + 1, len(TEAM)):
                d = np.linalg.norm(pos[1:, i] - pos[1:, j], axis=1)
                assert d.min() >= CONTACT * (TEAM[i].radius_m + TEAM[j].radius_m) - 0.02
        # bodies may brush walls by the contact tolerance, never more
        boxes = np.array(sc.ap.fp.blockers)
        for i, o in enumerate(TEAM):
            p = pos[:, i, None, :]
            dx = np.maximum(np.maximum(boxes[:, 0] - p[..., 0], 0), p[..., 0] - boxes[:, 2])
            dy = np.maximum(np.maximum(boxes[:, 1] - p[..., 1], 0), p[..., 1] - boxes[:, 3])
            assert np.hypot(dx, dy).min() >= CONTACT * o.radius_m - 0.005


def test_runs_are_deterministic(sc, runs):
    again = run_search(sc, TEAM, SearchParams(delay=1.0))
    assert again["pos"] == runs[1.0]["pos"] and again["first_known"] == runs[1.0]["first_known"]


def test_team_clears_the_apartment_and_communication_helps(runs):
    for d in (0.0, 1.0):
        assert runs[d]["metrics"]["feasible"] and runs[d]["metrics"]["coverage"] >= 0.995
    # without messages every agent has to see everything itself
    assert runs[None]["metrics"]["t_all_know"] is None or (
        runs[None]["metrics"]["t_all_know"] > runs[0.0]["metrics"]["t_all_know"]
    )


def test_export_is_a_valid_replay_with_knowledge_and_separate_attention():
    doc = from_results(results([3], [1.0]), "results.json")
    assert validate(doc) == []
    assert doc["model"]["attention_equals_heading"] is False
    a = doc["scenes"][0]["runs"][0]["agents"][0]
    assert len(a["first_known"]) == len(doc["scenes"][0]["points"]) and "mode" in a
    assert a["attention"] != a["heading"]


# ---- closed doors and threat scoring ----


@pytest.fixture(scope="module")
def door_run():
    sc = scenario(2, closed_frac=0.6)
    return sc, run_search(sc, TEAM, SearchParams(delay=1.0))


def test_closed_doors_block_sight_until_an_agent_opened_them(door_run):
    sc, r = door_run
    assert sc.closed and r["metrics"]["doors_opened"] >= 1
    pos, att = np.array(r["pos"]), np.array(r["attention"])
    opened = {di: t for di, t in enumerate(r["door_open"]) if t >= 0}
    for i in range(len(TEAM)):
        count = np.zeros(len(sc.q), int)
        first = np.full(len(sc.q), len(pos))
        for k in range(1, len(pos)):
            c = sc.grid.see_index(pos[k - 1, i])
            los = sc.vis[c].copy()
            for di, mk in sc.closed.items():
                if di not in opened or k <= round(opened[di] / DT):
                    los &= ~mk[c]
            count += in_view(sc.grid, sc.vis, sc.q, pos[k - 1, i], att[k - 1, i], los=los)
            first[(count >= DWELL_STEPS) & (first == len(pos))] = k
        assert np.mean(np.abs(first - np.array(r["own_seen"][i])) <= 1) >= 0.98


def test_a_door_opens_only_after_an_agent_spent_the_opening_time_at_it(door_run):
    sc, r = door_run
    modes = np.array(r["mode"])
    need = round(OPEN_TIME / DT)
    for t in (t for t in r["door_open"] if t >= 0):
        k = round(t / DT)
        assert (modes[:, k - need : k] == OPEN).all(axis=1).any()


def test_threat_scores_and_markers_are_exported(door_run):
    _, r = door_run
    m = r["metrics"]
    assert 0 <= m["risk"] <= 1 and 0 <= m["risk_multi"] <= 1 and m["exposure"] >= 0
    assert r["markers"] and {"x", "y", "t_detect", "t_id"} <= set(r["markers"][0])
