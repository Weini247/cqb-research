"""Decisions of model v0.3, from an agent's own knowledge only.

Coordinated search: an agent heads for the reachable cell from which it would see the most points
it does not know yet, discounted by distance and by the targets its teammates last announced.
Attention goes to the nearest unknown point in sight within the head range, else ahead.
These are scripted rules for a first closed-loop model, not a model of any real procedure.
"""

from __future__ import annotations

import math

import numpy as np

from .agents import AgentState, Limits, wrap

CLAIM_R = 2.0  # m: cells this close to a teammate's announced target are worth less
CLAIM_FACTOR = 0.3


def choose_target(
    a: AgentState, cand: np.ndarray, centers: np.ndarray, visf: np.ndarray, claims: list[np.ndarray]
) -> int:
    """Index into `cand` of the best cell for agent a, or -1 if nothing unknown is visible."""
    gain = visf @ (~a.known).astype(np.float32)
    if gain.max() <= 0:
        return -1
    d = np.linalg.norm(centers[cand] - a.pos, axis=1)
    value = gain / (1.0 + d)
    for c in claims:
        value[np.linalg.norm(centers[cand] - c, axis=1) < CLAIM_R] *= CLAIM_FACTOR
    return int(np.argmax(value))


def attention_goal(a: AgentState, los: np.ndarray, q: np.ndarray, lim: Limits) -> float:
    """Direction the agent wants to attend to."""
    unk = np.nonzero(los & ~a.known)[0]
    if len(unk):
        ang = np.arctan2(q[unk, 1] - a.pos[1], q[unk, 0] - a.pos[0])
        rel = (ang - a.heading + math.pi) % (2 * math.pi) - math.pi
        ok = np.abs(rel) <= lim.head_range
        if ok.any():
            d = np.linalg.norm(q[unk[ok]] - a.pos, axis=1)
            return float(ang[ok][np.argmin(d)])
        # unknown points only behind: the body has to turn, attention leads within its range
        return wrap(a.heading + math.copysign(lim.head_range, rel[np.argmin(np.abs(rel))]))
    return a.heading
