"""Operators with different body dimensions."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Operator:
    name: str
    role: str
    radius_m: float  # shoulder half-width incl. kit
    height_m: float
    speed_mps: float  # walking speed in transit; entry is faster
    color: str

    def to_dict(self) -> dict:
        return asdict(self)


def default_team() -> list[Operator]:
    # Stack order: 0,1 on side A of the door, 2,3 on side B.
    return [
        Operator("Alpha", "point", 0.24, 1.78, 1.5, "#e4572e"),
        Operator("Bravo", "rifle", 0.30, 1.92, 1.35, "#29a8ab"),
        Operator("Charlie", "breacher", 0.27, 1.85, 1.4, "#f3a712"),
        Operator("Delta", "rear", 0.21, 1.66, 1.55, "#a05ee8"),
    ]
