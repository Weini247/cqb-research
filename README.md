# Killhouse

CQB/Killhouse simulation prototype (spike 1).

- `building.py`: procedural building (default 30×40 m, 0.5 m grid, BSP rooms, 2 m corridors,
  doors via spanning tree + corridor links + loops, 3 outer entrances)
- `team.py`: 4 operators with different radius/height/speed
- `sim.py`: team state machine per room: transit → stack → crisscross entry → clear corners → next
  (DFS over the door graph, always from an already cleared room)
- `replay.py` + `viewer.html`: replay JSON (`killhouse.replay/1`) and a standalone canvas player

```
python -m uv sync
python -m uv run killhouse --seed 7 --out out   # out/replay.json, out/replay.html
python -m uv run pytest
python -m uv run ruff check .
```

Known simplifications: no operator-operator collision, no line-of-sight, no threats.
