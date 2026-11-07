import json

from killhouse.replay import SCHEMA, from_results, main, validate
from killhouse.viewer3d import to_html


def results(steps=5, doors=2):
    track = [[[0.1 * k, 0.0], [0.0, 0.1 * k]] for k in range(steps)]
    return {
        "schema": "killhouse.apartment/0",
        "config": {"dt": 0.1, "half_fov_deg": 50.0, "objective": "risk_multi", "commit": "abc1234"},
        "team": [{"name": "A"}, {"name": "B"}],
        "rooms": [
            {
                "room": {"name": "R", "doors": [{}] * doors},
                "points": [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]],
                "replays": [
                    {
                        "name": "t",
                        "metrics": {"t_clear": 0.3, "risk_multi": 0.5},
                        "pos": track,
                        "gaze": [[0.0, 1.5]] * steps,
                        "first_seen": [0, 2, 99],
                        "door_open": [0.2, -1.0],
                    }
                ],
            }
        ],
    }


def test_conversion_keeps_tracks_conventions_and_provenance():
    doc = from_results(results(), "results.json")
    assert doc["schema"] == SCHEMA and validate(doc) == []
    run = doc["scenes"][0]["runs"][0]
    assert run["steps"] == 5 and run["agents"][1]["y"][4] == 0.4
    assert run["agents"][0]["attention"] == run["agents"][0]["heading"]
    assert doc["model"]["attention_equals_heading"] is True
    assert doc["provenance"]["commit"] == "abc1234" and "length" in doc["conventions"]


def test_events_are_sorted_and_closed_doors_left_out():
    run = from_results(results(), "x")["scenes"][0]["runs"][0]
    assert run["events"] == [
        {"t": 0.2, "type": "door_open", "door": 0},
        {"t": 0.3, "type": "cleared"},
    ]


def test_validate_reports_broken_documents():
    doc = from_results(results(), "x")
    run = doc["scenes"][0]["runs"][0]
    run["agents"][0]["x"].pop()
    run["events"].append({"t": 9.0, "type": "cleared"})
    run["first_seen"].pop()
    problems = validate(doc)
    assert len(problems) == 3
    doc["schema"] = "killhouse.replay/1"
    assert any("schema" in p for p in validate(doc))


def test_viewer_embeds_the_replay_document():
    html = to_html(results())
    assert f'"schema":"{SCHEMA}"' in html and "/*__DATA__*/null" not in html


def test_cli_writes_a_valid_replay(tmp_path):
    f = tmp_path / "results.json"
    f.write_text(json.dumps(results()), encoding="utf-8")
    main([str(f)])
    assert validate(json.loads((tmp_path / "replay.json").read_text(encoding="utf-8"))) == []
