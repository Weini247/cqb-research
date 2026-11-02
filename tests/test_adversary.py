import numpy as np
import pytest

from killhouse.adversary import game_value, point_risk
from killhouse.entry import EVAL_CFG, evaluate
from killhouse.room import standard_rooms
from killhouse.tactics import build
from killhouse.team import default_team


def test_point_risk_mean_is_the_single_threat_risk():
    team, room = default_team(), standard_rooms()[3]
    pb = build("crisscross", room, team)
    assert point_risk(room, pb, team).mean() == pytest.approx(
        evaluate(room, pb, team, cfg=EVAL_CFG).risk
    )


def test_game_value_bounds():
    r = np.array([[1.0, 0.0], [0.0, 1.0]])  # matching pennies: mixing halves the worst case
    v, w = game_value(r)
    assert v == pytest.approx(0.5) and w == pytest.approx([0.5, 0.5])
    r2 = np.array([[0.2, 0.3], [0.9, 0.9]])  # a dominant technique needs no mixing
    assert game_value(r2)[0] == pytest.approx(0.3)
