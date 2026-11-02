import numpy as np
import pytest

from killhouse.optimize import cem_minimize
from killhouse.reference import Watchman, comb_check, l_corridor


@pytest.mark.parametrize("k", [2, 3])
def test_comb_gallery_needs_exactly_k_observers(k):
    c = comb_check(k)
    assert c["lower_bound_k"] and c["greedy_guards"] == k and c["all_seen"]


def test_cem_finds_the_l_corridor_watchman_optimum_from_every_seed():
    wm = Watchman(l_corridor())
    _, d_ex = wm.exhaustive(res=0.1)
    lo, hi = np.zeros(2), np.full(2, 6.0)
    for s in range(4):
        x0 = np.random.default_rng(100 + s).uniform(lo, hi)
        x, _ = cem_minimize(wm.score, lo, hi, [x0], iters=30, pop=32, seed=s)
        assert wm.unseen(x) == 0.0
        assert np.linalg.norm(x - wm.S) <= d_ex + 0.1  # within one grid step of the optimum
