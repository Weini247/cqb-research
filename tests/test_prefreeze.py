import pytest

from killhouse.prefreeze import (
    calibration,
    candidate,
    main,
    scenario_table,
    smallest_sufficient,
)


def test_scenario_table_scales_with_the_square_root_of_the_count():
    t = scenario_table([0.04] * 5, [0.01] * 5)
    assert t[128]["se_gap_median"] == pytest.approx(0.02)
    assert not t[64]["meets_target"] and t[128]["meets_target"]
    assert smallest_sufficient(t) == 128


def test_no_scenario_count_is_chosen_if_the_target_stays_out_of_reach():
    assert smallest_sufficient(scenario_table([1.0] * 5, [1.0] * 5)) is None


def test_candidate_respects_time_and_fratricide():
    r = {
        "front_plans": [
            {"metrics": [0.3, 2.0, 0.0], "x": [1.0]},
            {"metrics": [0.4, 1.0, 1.0], "x": [2.0]},
            {"metrics": [0.5, 1.0, 0.0], "x": [3.0]},
        ]
    }
    assert candidate(r, {"t_clear": 1.5, "fratricide": 0.0})[1] == 0.5
    assert candidate(r, {"t_clear": 1.5, "fratricide": 1.0})[1] == 0.4
    assert candidate(r, {"t_clear": 0.5, "fratricide": 1.0}) is None


def test_calibration_reports_a_rate_for_the_null_model():
    rows = [
        {
            "room": {
                "name": f"R{i}",
                "w": 4.0 + i % 5,
                "d": 5.0,
                "door": [0.5, 1.5] if i % 2 else [2.0, 3.0],
            },
            "doctrines": [
                {"name": "crisscross", "feasible": True, "gap_selected": 0.3 + 0.01 * (i % 7)}
            ],
        }
        for i in range(20)
    ]
    c = calibration(rows, n_sim=20, n_boot=50)
    assert 0 <= c["rate_at_0.05"] <= 1 and c["n_rooms"] == 20


def test_confirmatory_rooms_are_refused(tmp_path):
    with pytest.raises(SystemExit):
        main(["precision", str(tmp_path / "x.jsonl"), "--generated", "2026", "40"])
