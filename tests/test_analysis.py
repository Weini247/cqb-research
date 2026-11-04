import json

import numpy as np
import pytest

from killhouse.analysis import (
    analyze,
    at_time_floor,
    check_rooms,
    corner_coefficient,
    family,
    h2,
    holm,
    is_corner,
    load_rooms,
    main,
    sign_test,
)
from killhouse.room import generated_rooms


def pair(name, gap=0.3, risk=0.5, t=1.6, fr=0.0, feasible=True, leaving=10, stable=True):
    return {
        "name": name,
        "feasible": feasible,
        "gap_selected": gap,
        "gap_by_method": {"cem": gap, "cmaes": gap},
        "gap_per_seed": [gap] * 5 + [gap - 0.1] * 5,
        "method_stable": stable,
        "seeds_leaving": leaving,
        "risk_multi": risk,
        "t_clear": t,
        "fratricide": fr,
    }


def room(name, w, door, doctrines):
    return {
        "room": {"name": name, "w": w, "d": 5.0, "door": door},
        "front": [[0.4, 0.9, 0.0]],
        "doctrines": doctrines,
    }


def rooms():
    out = []
    for i in range(8):
        corner = i % 2 == 0
        door = [0.5, 1.5] if corner else [3.0, 4.0]
        out.append(
            room(
                f"R{i}",
                7.0 + i % 3,
                door,
                [
                    pair("crisscross", 0.4 if corner else 0.2, risk=0.5),
                    pair("buttonhook+dead-space", 0.3, risk=0.6 if i else 0.4),
                ],
            )
        )
    return out


def test_family_ignores_the_dead_space_step():
    assert family("limited-penetration+dead-space") == "limited-penetration"
    assert family("crisscross") == "crisscross"


def test_door_class_uses_the_nearer_side_wall():
    assert is_corner({"w": 6.0, "door": [0.5, 1.5]})
    assert is_corner({"w": 6.0, "door": [4.5, 5.5]})
    assert not is_corner({"w": 6.0, "door": [2.5, 3.5]})


def test_sign_test_is_exact():
    assert sign_test(3, 3) == 0.125
    assert sign_test(0, 3) == 1.0
    assert sign_test(0, 0) == 1.0


def test_holm_steps_up_and_stays_monotone():
    assert holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {
        "a": pytest.approx(0.03),
        "c": pytest.approx(0.06),
        "b": pytest.approx(0.06),
    }
    assert holm({"a": 0.9, "b": 0.8}) == {"a": 1.0, "b": 1.0}  # capped at 1


def test_corner_coefficient_recovers_a_known_effect_at_equal_width():
    rng = np.random.default_rng(0)
    width = rng.uniform(3, 8, 60)
    corner = (rng.uniform(size=60) < 8 / (width + 4)).astype(float)  # confounded with width
    gap = 0.5 + 0.06 * corner - 0.03 * width + rng.normal(0, 0.005, 60)
    r = corner_coefficient(gap, corner, width, n_boot=300)
    assert r["coef_corner"] == pytest.approx(0.06, abs=0.01)
    assert r["coef_width"] == pytest.approx(-0.03, abs=0.005)
    assert r["ci"][0] > 0 and r["p"] < 0.01


def test_h2_compares_families_and_skips_rooms_without_both():
    rows = rooms()
    rows.append(
        room("R8", 7.0, [3.0, 4.0], [pair("crisscross"), pair("buttonhook", feasible=False)])
    )
    r = h2(rows)
    assert (r["wins"], r["n"]) == (7, 8)
    assert r["corner_fed"]["n"] + r["centre_fed"]["n"] == 8


def test_time_floor_needs_no_leaving_run_and_the_fastest_time():
    r = rooms()[0]
    assert at_time_floor(r, pair("x", t=0.9, leaving=0))
    assert not at_time_floor(r, pair("x", t=1.6, leaving=0))
    assert not at_time_floor(r, pair("x", t=0.9, leaving=3))


def test_analyze_holm_is_provisional_without_h4():
    a = analyze(rooms(), n_boot=100)
    assert a["n_rooms"] == 8 and a["valid_pairs"] == 16 and not a["holm_final"]
    assert a["rooms_with_step"] == 8
    assert a["gaps"]["pie+crisscross"] == {"n": 0}  # no valid pair of this family
    b = analyze(rooms(), n_boot=100, h4_p=0.5)
    assert b["holm_final"] and b["H2"]["p_holm"] >= a["H2"]["p_holm"]


def test_load_rooms_accepts_equal_repeats_and_rejects_conflicts(tmp_path):
    rows = rooms()
    a, b = tmp_path / "a.jsonl", tmp_path / "results.json"
    a.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    b.write_text(json.dumps({"rooms": rows[:2]}), encoding="utf-8")
    assert len(load_rooms([a, b])) == 8
    rows[0]["doctrines"][0]["risk_multi"] = 0.9
    b.write_text(json.dumps({"rooms": rows[:2]}), encoding="utf-8")
    with pytest.raises(ValueError, match="differ"):
        load_rooms([a, b])


def test_check_rooms_requires_exactly_the_generated_set():
    want = [{"room": r.to_dict()} for r in generated_rooms(1, 3)]
    assert len(check_rooms(want, 1, 3)) == 64
    with pytest.raises(ValueError, match="G1-02"):
        check_rooms(want[:2], 1, 3)


def test_cli_writes_the_result(tmp_path, capsys):
    f = tmp_path / "rooms.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rooms()), encoding="utf-8")
    main([str(f), "--out", str(tmp_path / "a.json")])
    assert "provisional" in capsys.readouterr().out
    assert json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))["n_rooms"] == 8
