"""Model v0.3 (`sim2`): closed-loop agents with their own state, perception and knowledge.

Unlike the frozen E1 model (`entry.py`), agents here are not replayed along precomputed paths.
Every step each agent perceives with its own attention direction, updates its own knowledge,
receives delayed messages from teammates and decides from that knowledge alone. All agents know
the floorplan; nobody knows what a teammate has seen until a message arrives.

Modules: `agents` (state and motion limits), `perception` (field of view, line of sight, dwell),
`policy` (coordinated search decisions), `core` (loop, messages, export).
"""

from .core import SearchParams, run_search

__all__ = ["SearchParams", "run_search"]
