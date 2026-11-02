import numpy as np
import pytest

from killhouse import fastsim
from killhouse.doctrine import doctrines
from killhouse.entry import EVAL_CFG, evaluate
from killhouse.optimize import HI, LO, decode
from killhouse.room import standard_rooms
from killhouse.team import default_team

pytestmark = pytest.mark.skipif(not fastsim.available(), reason="torch not installed")
TEAM = default_team()


@pytest.mark.parametrize("name", ["S-center", "M-corner", "L-corner-box", "M-center-box"])
def test_batch_matches_numpy_reference(name):
    room = next(r for r in standard_rooms() if r.name == name)
    rng = np.random.default_rng(0)
    lo, hi = np.tile(LO, 4), np.tile(HI, 4)
    pbs = doctrines(room, TEAM) + [decode(rng.uniform(lo, hi), room, TEAM) for _ in range(6)]
    for cfg in (None, EVAL_CFG):
        kw = {} if cfg is None else {"cfg": cfg}
        fast = fastsim.evaluate_batch(room, pbs, TEAM, **kw)
        for pb, f in zip(pbs, fast, strict=True):
            ref = evaluate(room, pb, TEAM, **kw)
            assert f.risk == pytest.approx(ref.risk, abs=2e-3)
            assert f.risk_multi == pytest.approx(ref.risk_multi, abs=2e-2)
            assert f.exposure == pytest.approx(ref.exposure, abs=2e-3)
            assert f.t_clear == pytest.approx(ref.t_clear, abs=0.11)
            for x, y in (
                (f.collision, ref.collision),
                (f.wall, ref.wall),
                (f.fratricide, ref.fratricide),
            ):
                assert x == pytest.approx(y, abs=1e-5)
