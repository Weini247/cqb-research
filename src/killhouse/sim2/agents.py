"""Agent state and kinematic limits of model v0.3. Body heading and attention are separate."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

MOVE, WAIT, HOLD, OPEN = 0, 1, 2, 3  # motion modes, exported per step


@dataclass(frozen=True)
class Limits:
    body_turn: float = 4.0  # rad/s, as TURN_RATE in the E1 model
    head_turn: float = 8.0  # rad/s, attention turns faster than the body
    head_range: float = 1.2  # rad, attention at most this far from the body heading
    accel: float = 3.0  # m/s^2


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def turn_towards(cur: float, want: float, max_step: float) -> float:
    d = wrap(want - cur)
    return wrap(cur + max(-max_step, min(max_step, d)))


@dataclass
class AgentState:
    pos: np.ndarray
    heading: float
    attention: float
    speed: float = 0.0
    mode: int = MOVE
    known: np.ndarray = field(default=None)  # bool per point: own sight or received message
    dwell: np.ndarray = field(default=None)  # steps each point has been in view
    target: int = -1  # grid cell the agent is heading for
    path: list = field(default_factory=list)  # remaining waypoints
    waited: int = 0  # consecutive steps spent waiting for a teammate
    next_plan: int = 0  # step of the next scheduled replan
    yield_until: int = -1  # while k < yield_until the agent walks out of a teammate's way
    open_until: int = -1  # while k < open_until the agent opens door `opening`
    opening: int = -1

    def clamp_attention(self, lim: Limits) -> None:
        rel = wrap(self.attention - self.heading)
        if abs(rel) > lim.head_range:
            self.attention = wrap(self.heading + math.copysign(lim.head_range, rel))
