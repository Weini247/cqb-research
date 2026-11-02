# Apartments v0: multi-room clearing (stage 2)

Status: first working version, exploratory, doctrines only (no optimizer at building level
yet). Reproduce: `python -m uv run killhouse-apartment --seeds 1 3 5 --out out/apartment`
(about 1 min per apartment on one core), then open `out/apartment/viewer3d.html`.

## What is modelled

- **Generator** (`apartment.py`): 80-130 m², hallway with 1-2 rooms on each side, living room
  at the far end, often a kitchen reachable only through the living room. Doors 0.8 m (entrance
  0.9 m), centre- or corner-fed. Every door is open at 90° on a random hinge side and blocks
  sight and bodies; the pocket behind it is a real dead space. Wardrobes on free walls, and a
  stairwell landing in front of the entrance.
- **Geometry** (`geom.py`): walls, door leaves and furniture as boxes. Visibility is
  precomputed from every free 0.25 m observer cell to every threat position (0.3 m grid),
  about 8 s per apartment.
- **Clearing** (`clearing.py`): The team enters the hallway with a two-man corridor
  technique, then clears rooms depth-first, nearest door first, using the selected playbook
  in each room's local frame. #3/#4 hold the hallway (rear security) when they do not enter.
  Dead space, including the pocket behind the door, is cleared by the strict dead-space step.
  Between rooms the team walks through cleared space (A*).
- **Metrics:** the same perception and duel model as for single rooms, over the whole episode.
  Threats in uncleared rooms see the team through open doors.

## First numbers (3 apartments, 2 threats)

| apartment | crisscross R2 / T | buttonhook R2 / T | limited penetration R2 / T |
|---|---|---|---|
| APT1 (6 rooms) | 0.931 / 58.6 s | 0.924 / 57.3 s | 0.902 / 54.0 s (one room not fully seen) |
| APT3 (4 rooms) | 0.871 / 43.7 s | 0.879 / 41.3 s | 0.845 / 40.0 s |
| APT5 (6 rooms) | 0.866 / 63.3 s | 0.917 / 59.7 s | 0.832 / 56.0 s |

## Observations

1. **The single-room ranking does not transfer automatically.** In apartments, limited
   penetration (+ dead-space step) has the lowest risk and is fastest in all three cases,
   while it was the worst technique in single rooms. A plausible mechanism: exposure in an
   apartment comes mostly from uncleared rooms looking into the hallway through open doors,
   so time spent in the hallway counts more than the details of a single entry. This is
   exactly the kind of multi-room effect the stage was built to reveal. It is a hypothesis
   until the optimizer and more apartments are run.
2. **The combination with the dead-space step changes what "limited penetration" means.**
   An operator who goes back to look behind the door is effectively entering the room. The
   label must be read as "limited penetration with dead-space step".
3. **Absolute risks are high (0.83-0.93).** Each scenario places 2 threats somewhere in
   the *whole* apartment (32 scenarios, uniform over all threat positions), not 2 per room.
   The high values come from long episodes and many rooms looking into the hallway.
   (Corrected after review R2; an earlier version said "2 threats each".)
   As before, only comparisons are meaningful.

## Not yet included (next steps)

- Building-level optimization (order of rooms, technique per door, team splitting)
- Closed doors, opening them, and checking which way they swing
- Real floorplans from public datasets (licence check pending)
- 2D report and sensitivity analysis for apartments; more apartments per comparison
