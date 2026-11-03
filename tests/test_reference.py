import numpy as np
import pytest

from killhouse.optimize import cem_minimize, cmaes_minimize
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


def test_cmaes_finds_the_l_corridor_watchman_optimum_in_most_seeds():
    # plain CMA-ES without restarts: 17/20 seeds measured (REPORT_M2); seeds 0-7 give 6/8
    wm = Watchman(l_corridor())
    _, d_ex = wm.exhaustive(res=0.1)
    lo, hi = np.zeros(2), np.full(2, 6.0)
    hits = 0
    for s in range(8):
        x0 = np.random.default_rng(100 + s).uniform(lo, hi)
        x, _ = cmaes_minimize(wm.score, lo, hi, [x0], iters=30, pop=32, seed=s)
        hits += wm.unseen(x) == 0.0 and np.linalg.norm(x - wm.S) <= d_ex + 0.1
    assert hits >= 6


def test_cmaes_solves_a_shifted_sphere():
    lo, hi = np.zeros(10), np.ones(10)
    target = np.linspace(0.2, 0.8, 10)
    f = lambda xs: [float(((x - target) ** 2).sum()) for x in xs]  # noqa: E731
    x, fx = cmaes_minimize(f, lo, hi, [np.full(10, 0.5)], iters=80, pop=16, seed=0)
    assert fx < 1e-4
