# Model v0.3 (`sim2`): closed-loop agents with own knowledge

Status: **exploratory**, first version (milestone v0.3-c). It does not change the frozen E1 model
(`entry.py`); the E1 golden test guards that. No scientific claim rests on it yet; any claim needs
its own study.

## What is new compared with model v0.2

| | v0.2 (E1) | v0.3 (`sim2`) |
|---|---|---|
| motion | precomputed paths, perception computed afterwards | closed loop: perceive, exchange messages, decide, move, every 0.1 s |
| angles | one angle per agent | body heading and attention separate, each with its own turn rate |
| knowledge | team view only | per agent: own sight (field of view around attention, line of sight, 0.3 s dwell) plus messages |
| communication | none | messages with a fixed delay (0 s, 1 s, or none) carrying newly seen points and the agent's target |
| bodies | collision counted afterwards | agents wait, side-step or give way; bodies may brush (85 % of the summed radii, also against walls) |

## Decisions (scripted rules, not a model of a real procedure)

- **Target:** the reachable cell from which the agent would see the most points it does not know,
  divided by (1 + distance), worth 30 % within 2 m of a teammate's announced target or of an own
  target it got stuck on.
- **Attention:** the nearest unknown point in sight within 1.2 rad of the body heading, else ahead.
- **Giving way:** after 1 s of waiting, the lower-priority agent of a blocking pair (higher index;
  finished agents always count as lower) walks to the nearest spot off the other's path and stays
  there for 3 s; if no spot is reachable it steps back 0.5 m.
- **Done:** an agent stops when it knows 99.5 % of the points; the run ends when all have stopped
  and no message is still on its way, or after 120 s.

## Parameters (all free modelling choices)

Body turn 4 rad/s (as in E1), attention turn 8 rad/s, attention range +-1.2 rad, acceleration
3 m/s^2, contact share 0.85, replan every 1 s, give-way time 3 s, stuck check every 5 s (< 0.3 m
moved). Field of view, dwell and clearing threshold are taken from E1 (`entry.py`).

## Checks (`tests/test_sim2.py`)

- Without messages an agent's knowledge equals its own sightings, and those follow from its
  exported track (independent batch recomputation, 98 % exact at 0.1 mm export precision).
- With messages, every point becomes known exactly at min(own sight, a teammate's sight + delay).
- Turn, attention-range and speed limits hold in every step; bodies stay within the contact
  tolerance of each other and of walls.
- Runs are deterministic; the export is a valid `killhouse.replay/2` document with per-agent
  knowledge and separate attention.

## Known limitations

- Interior doors are all open in this version (no door opening yet).
- Houses (`--building house`): on 12 generated houses x 2 conditions (messages after 1 s, none)
  all 24 runs reached 99.5 % coverage within 240 s; with messages the team needed 31-75 s,
  without 70-162 s. Exploratory, development seeds only.
- No threats and no risk: the outcome is coverage over time, not the E1 duel model.
- On 8 development apartments x 3 delays, 23 of 24 runs reached 99.5 % coverage; one run without
  communication ended in a standoff. Deadlocks between bodies are reduced, not excluded.
- Whether messages make the team faster varies between apartments in this first version (the
  scripted target rule makes agents bunch up); this is an observation to study, not a result.
- Bodies may intrude up to 15 % of their radius into walls (about 4.5 cm).
