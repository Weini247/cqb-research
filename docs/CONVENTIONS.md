# Conventions

Fixed for all code from v0.2.1 on. The replay format repeats them in every document.

| item | convention |
|---|---|
| length | metres |
| time | seconds from episode start; simulation step `dt` = 0.1 s |
| plan axes (Python) | x right, y forward, into the building; origin at the outside of the entry wall for single rooms |
| angles | radians, 0 = +x, counter-clockwise |
| viewer axes (three.js) | y up; a plan point (x, y) is drawn at (x, 0, -y); a heading `h` is `rotation.y = h` |
| precision of v0.2 sources | positions rounded to 0.01 m, angles to 0.01 rad |

## Replay format `killhouse.replay/2`

`killhouse.replay` writes it (`killhouse-replay results.json`), `killhouse.viewer3d` embeds it.
Version 1 belonged to the removed spike-1 prototype.

- `dt`, `conventions`, `model` (field of view, objective, `attention_equals_heading`),
  `provenance` (source file, results schema, commit), `agents` (body data per agent).
- `scenes[]`: `environment` (room or apartment geometry), `points` (threat positions), `runs[]`.
- `runs[]`: `steps`, `metrics`, per agent `x`, `y`, `heading`, `attention` (one value per step),
  optional `first_known` (step at which this agent knew each point, model v0.3) and `mode`
  (0 moving, 1 waiting, 2 done, 3 opening a door),
  `first_seen` (step at which each point was first seen), `markers`, `events` (`cleared`,
  `door_open`, sorted by time).

`validate()` checks the schema name, track lengths, finite values, the number of `first_seen`
entries and event times. The viewer converts the document once and never extrapolates.

## State versus picture

The viewer interpolates between steps and may add cosmetic motion. It never changes position,
heading or attention. In model v0.2 heading and attention are the same angle; the viewer draws
attention as its own ray so that later models can separate them.

| shown | from the replay | cosmetic |
|---|---|---|
| position, body heading | yes | — |
| attention ray, neck and head turn | attention minus heading | split 40 % neck / 60 % head, limited to 69 degrees |
| walk / idle blend and cycle speed | simulated speed | the clips themselves (leg swing, body bob, chest twist) |
| figure shape | body height and radius | limbs, helmet, equipment |

"Figur: Kapsel (Modell)" shows the simulated body without any cosmetic motion.

## Protected E1 path

`entry.py`, `room.py`, `doctrine.py`, `optimize.py`, `fastsim.py` and `bench.py` produced the
frozen E1 results. `tests/test_e1_golden.py` re-evaluates three E1 rooms and fails if their
numbers change. New behaviour goes into new modules.
