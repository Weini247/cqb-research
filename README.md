# Killhouse

**How close are established CQB room-entry techniques to the optimum?**
A simulation study of coordinated multi-agent search under visibility constraints, with
close-quarters room entry as the case study. Research concept: [docs/CONCEPT.md](docs/CONCEPT.md),
results: [E0](docs/REPORT_E0.md) (exposure model) and
[E1 draft](docs/REPORT_E1_draft.md) (duel threat model, sensitivity analysis).

## Entry benchmark (single room)

- `room.py`: rectangular rooms, door channel with wall thickness, furniture boxes, line of sight
- `entry.py`: 4-operator plans (stack, entry timing, threshold point, point of domination,
  gaze with turn-rate limit, pie slicing) -> trajectories -> duel risk, exposure, time to
  clear, collision, wall, fratricide
- `doctrine.py`: stylized crisscross, buttonhook, pie + crisscross, limited penetration
- `optimize.py`: cross-entropy search in the same 36-dim plan space, Pareto archive, gap metric
- `sensitivity.py`: one-at-a-time robustness of the doctrine ranking (8 model/geometry axes)
- `bench.py` + `report.html`: results JSON and a self-contained report (Pareto plot +
  synchronized replays with uncleared threat positions)

```
python -m uv sync
python -m uv run killhouse-bench --out out/bench-e1      # ~18 min, single core
python -m uv run killhouse-sens                          # ~15 s
python -m uv run killhouse-bench --quick --rooms M-center  # smoke run
```

## Building spike (spike 1)

- `building.py`: procedural building (default 30×40 m, 0.5 m grid, BSP rooms, 2 m corridors,
  doors via spanning tree + corridor links + loops, 3 outer entrances)
- `team.py`: 4 operators with different radius/height/speed
- `sim.py`: team state machine per room: transit → stack → crisscross entry → clear corners → next
- `replay.py` + `viewer.html`: replay JSON (`killhouse.replay/1`) and a standalone canvas player

```
python -m uv run killhouse --seed 7 --out out   # out/replay.json, out/replay.html
python -m uv run pytest
python -m uv run ruff check .
```

The building spike has no line of sight or collisions yet; the E0 model does.
