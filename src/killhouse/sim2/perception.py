"""Perception of model v0.3: line of sight from the precomputed visibility matrix, a field of view
around the *attention* direction, and a dwell time before a point counts as seen."""

from __future__ import annotations

import numpy as np

from ..entry import DT, DWELL, HALF_FOV
from ..geom import Grid

DWELL_STEPS = max(1, round(DWELL / DT))


def in_view(
    grid: Grid,
    vis: np.ndarray,
    q: np.ndarray,
    pos: np.ndarray,
    attention: float,
    half_fov: float = HALF_FOV,
) -> np.ndarray:
    """Bool per point: in line of sight and inside the field of view around `attention`."""
    los = vis[grid.see_index(pos)]
    ang = np.arctan2(q[:, 1] - pos[1], q[:, 0] - pos[0])
    return los & (np.abs((ang - attention + np.pi) % (2 * np.pi) - np.pi) <= half_fov)


def sight_steps(
    grid: Grid,
    vis: np.ndarray,
    q: np.ndarray,
    pos: np.ndarray,
    att: np.ndarray,
    half_fov: float = HALF_FOV,
) -> np.ndarray:
    """Batch version over a finished track (T, 2) / (T,): step at which each point is first
    seen by this agent alone (len(track) if never). Used to check the incremental loop."""
    count = np.zeros(len(q), int)
    first = np.full(len(q), len(pos))
    for k in range(len(pos)):
        count += in_view(grid, vis, q, pos[k], att[k], half_fov)
        new = (count >= DWELL_STEPS) & (first == len(pos))
        first[new] = k
    return first
