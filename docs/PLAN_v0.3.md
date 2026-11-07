# KILLHOUSE v0.2 audit and v0.3 plan

Status: planning document, nothing implemented. Based on the code at v0.2.0 (commit f83f06c),
read locally. Not checked: rendering performance in a browser for large scenes, asset licences of
concrete character models, and anything that needs a run.

## A. Executive assessment

**Scientifically** the project is further along than it looks: a frozen and completed
preregistered study (E1), an analysis plan as code (`analysis.py`), pre-freeze checks
(`prefreeze.py`), 86 tests, archived data (`data/e1`) and a claims register. That is the strongest
asset, and every plan below has to protect it.

**Technically** the simulation is a **2D, open-loop** model. Agents follow precomputed keyframe
paths (`entry._keyframes`, `entry.trajectories`, `clearing._walk`); perception and the duel are
computed *afterwards* over the finished trajectories (`entry.perception_and_duel`,
`clearing.evaluate_episode`). Nobody reacts to what it sees. Body heading, gaze and weapon are one
angle (`gaze` array, shape T x n).

**Visually** there is a decent single-file three.js viewer (`viewer3d.html`, 472 lines, three
0.160 from a CDN) with orbit/top cameras, a timeline (`#seek`), speed control 0.25-4x, a ghost
comparison, cutaway walls, threat markers, door leaves and recording hooks (`window.killhouse`).
The figures are procedural primitives (`capsuleFigure`, `dummyFigure`); the walk cycle is driven
by speed (`pose`: `m.phase += speed * dt * 5.5`). No rigged characters, no head motion separate
from the body.

**Verdict:** a good base for evolution, not for a rewrite. The biggest gap for "cinematic and
behaviourally credible" is not rendering but the missing agent state: the viewer can only show
what the replay contains, and the replay contains position and one angle.

## Audit details (evidence)

| area | present and working | rudimentary | debt / risk |
|---|---|---|---|
| Geometry | `room.Room` (single room, door channel, wall thickness, `los` with `_through_door`), `geom.Floorplan` with axis-aligned boxes, `Grid`, A*, `visibility` | furniture as boxes, closed doors as LOS masks (`clearing.closed_door_masks`) | **two geometry models** (Room vs. Floorplan); `visibility` is a dense cells x points matrix: fine for apartments, quadratic for houses; no floors |
| Apartments | `apartment.generate_apartment` (hallway + room columns, door swing, closed doors, window, wardrobes), seeded | one topology family | layout tied to a hallway-with-columns scheme |
| Agents | `team.Operator` (size, speed), turn-rate limit, FOV cone, dwell | — | no state machine, no per-agent knowledge, no communication |
| Behaviour | playbooks (`doctrine.py`, `tactics.py`), episode scheduler (`clearing.run_clearing`) with door order, rear security, door watch | decisions are fixed in advance | open loop: perception cannot change behaviour |
| Simulation | numpy reference + torch batch (`fastsim.batch_trajectories`), DT 0.1 s, horizon 12 s | — | GPU float32 vs. numpy float64 (tests allow tolerance) |
| Replay | `bench._replay`, `clearing.run` output: `pos` (rounded to 0.01 m), `gaze` (0.01 rad), `first_seen`, plan, metrics, door open times | — | no own schema version (only `killhouse.bench/0` for the whole file), no units/axes declared, rounding, no per-agent state |
| Viewer | see above, `viewer3d.to_html` keeps `room`, `points`, `replays` | procedural figures | single file mixes UI, scene, animation; Python y maps to three -z implicitly |
| Legacy | `building.py`, `sim.py`, `viewer.html`, `cli.py` (spike 1) | — | unused by the research path, confuses readers |
| Validation | 86 tests incl. reference cases, analysis, determinism of seeds (shown in REPORT_M2) | no geometry fuzz tests, no viewer tests | no golden test that pins E1 numbers |

**What endangers E1:** any change in `entry.py`, `room.py`, `doctrine.py`, `optimize.py`,
`fastsim.py`, `bench.py` or the RNG use (`threat_sets` seeds by room name and salt). E1 is pinned
by the tag `e1-prereg`, but nothing *in main* fails if these behaviours drift. Rule for v0.3: the E1
path stays frozen in behaviour; new behaviour goes into new modules, and a golden test guards it.

**Assumptions to check before extending:** (1) how far the dense `visibility` matrix scales
(cells x points memory); (2) whether a rigged GLB character can follow a 10 Hz trajectory without
visible foot sliding; (3) whether CC0 character assets of sufficient quality exist; (4) browser
performance with 4-8 animated characters, shadows and a 15-room house.

## B. Gap analysis (v0.2.0 -> target)

| target area | gap | size |
|---|---|---|
| A Characters | rigged GLB, animation blending, head/gaze separate from body, materials, lighting, cinematic camera, slow motion (exists), shot export | large, mostly front end |
| B Buildings | houses with 8-15 rooms, several topologies, open areas, stairs/floors, furniture families, external geometry import, scalable visibility | large |
| C Behaviour | explicit agent state, own knowledge per agent, closed-loop decisions, communication delay/errors, collision avoidance between agents during motion | large, scientific core |
| D Consistency | versioned replay schema, declared conventions, state-to-animation sync rules, golden E1 test, geometry tests, motion limits | medium, prerequisite for all |
| E Viewer | agent selection, follow camera, knowledge overlays, perception events, run comparison beyond one ghost, video export | medium |

## C. Architecture proposal

Eight components, all in the existing Python package plus the viewer:

| component | module (new = *) | responsibility | interface |
|---|---|---|---|
| 1 Environment | `geom.py` (extended), `*buildings/` (generators, importers) | logical geometry only: floors, walls, doors, windows, furniture, portals (stairs) | `Floorplan` v2: list of floors, each with boxes and typed openings; `to_dict()` |
| 2 Simulation core | `*sim2/core.py` | fixed-step loop (DT), world state, closed-loop tick | `step(world, actions) -> world` |
| 3 Agent state and perception | `*sim2/agents.py`, `*sim2/perception.py` | per-agent body pose, heading, **attention direction with its own turn rate**, motion mode, knowledge map (seen cells, last seen, uncertainty) | `AgentState` dataclass; `perceive(world, agent) -> Observation` |
| 4 Behaviour | `*sim2/behavior.py` | task allocation and decisions from *own* knowledge only; communication as delayed, possibly noisy messages | `Policy.act(observation, messages) -> action`; scripted policies first |
| 5 Motion representation | `*sim2/motion.py` | turns actions into kinematically limited paths (speed, acceleration, turn rates) and contact checks | trajectory segments with timestamps |
| 6 Animation and rendering | `viewer3d/` (split into modules, still built into one HTML) | **only interprets** replay data: chooses clips, blends, places head look-at; never invents state | reads replay schema v1 |
| 7 Replay and export | `*replay.py` | schema `killhouse.replay/1`: units, axes, DT, per-tick agent state, events (seen, door opened, message), provenance (commit, seed) | JSON (+ optional compressed binary arrays) |
| 8 Validation | `tests/` | golden E1 test, schema tests, geometry fuzzing, motion limits, replay determinism, viewer smoke test | pytest |

**Data flow:** building generator -> Floorplan v2 -> sim2 (agents perceive, decide, move) ->
replay v1 -> viewer. The E1 path (`entry`, `bench`) stays as it is and gets an *adapter* that
writes its results as replay v1, so the new viewer also shows E1 replays without touching E1.

**Conventions to fix once:** metres; x right, y forward (into the building) in Python; three.js
y-up with z = -y; angles in radians, 0 = +x, counter-clockwise; time in seconds from episode
start; DT 0.1 s simulation, the viewer interpolates and never extrapolates.

**State versus picture:** the viewer may add cosmetic motion (breathing, foot placement, arm
swing) but nothing that changes position, heading or attention. Every cosmetic layer can be turned
off ("model view"), and the docs list what is cosmetic.

**External fusion modules later:** the knowledge map and the `Observation`/message interface are
the seam. An external perception or information-fusion module can plug in behind `perceive` and
the message channel, without changes to that module's own code.

## D. Technology decision

| | Three.js (keep) | Godot | Unreal |
|---|---|---|---|
| fits the current code | yes, viewer exists | rewrite of the viewer | rewrite, C++/Blueprints |
| sharing | a single HTML file, opens anywhere, embeddable in GitHub Pages | export per platform or WebAssembly build | heavy builds, no simple web sharing |
| characters | GLTF/GLB, `AnimationMixer`, cross-fading, bone look-at: enough for 4-8 agents | very good animation tree | best visual quality (MetaHuman etc.) |
| research use | Python writes JSON, browser reads it: trivial | needs import pipeline | needs import pipeline, large team skills |
| cost | low | medium | high |

**Recommendation: keep Three.js for v0.3 and v0.4.** It delivers rigged characters, blending,
better lighting (PBR materials, environment light, soft shadows) and cinematic cameras within the
existing pipeline. Reconsider Godot only if, after v0.3, there is a concrete need that Three.js
cannot meet (for example hundreds of agents or navmesh-heavy interaction). Unreal is out of
proportion for a one-person research project.

## E. Milestone roadmap

Effort in working sessions of a few hours, rough.

### v0.2.1 Foundation (1-2 sessions)
- **Scope:** golden E1 test (re-evaluate techniques and stored `x_selected` plans of 3 E1 rooms,
  compare with `data/e1`); replay schema v1 plus an exporter for existing bench and apartment
  replays; conventions documented; spike-1 modules moved to `legacy/` or removed.
- **Files:** `tests/test_e1_golden.py`, `src/killhouse/replay.py`, `docs/CONVENTIONS.md`,
  `building.py`, `sim.py`, `viewer.html`, `cli.py`.
- **Tests / acceptance:** golden test green on main; schema validation test; existing viewers
  still render.
- **Demo:** none visible; this is the safety net.

### v0.3-a Research viewer (2 sessions)
- **Scope:** select an agent; follow camera and cinematic camera path; attention ray and FOV cone
  per agent toggleable; perception events on the timeline (first seen, door opened); compare two
  runs side by side; PNG and WebM export via the existing hooks.
- **Files:** `viewer3d.html` split into modules (scene, ui, figures, timeline), bundled into one
  HTML by `viewer3d.py`.
- **Tests:** viewer smoke test in a headless browser (page loads, `killhouse.duration()` > 0,
  `setTime` works); replay v1 fixtures.
- **Demo:** an E1 room, technique vs. best found, with visible attention and events.

### v0.3-b Characters (2-3 sessions)
- **Scope:** one rigged CC0 character in GLB (several colour/size variants per operator),
  idle/walk/turn clips, speed-matched blending, head and torso look-at from the attention
  direction, better lighting and materials; procedural figures stay as fallback.
- **Risks:** foot sliding at 10 Hz paths, asset licence, file size of the single HTML.
- **Tests:** foot-sliding metric in the smoke test (clip speed vs. path speed within a
  tolerance), size budget for the HTML.
- **Demo:** new README GIFs.

### v0.3-c Agent state (3-4 sessions)
- **Scope:** `sim2` with `AgentState` (body heading and attention separate, each with its own
  turn rate), motion modes, per-agent knowledge map, scripted policies that reproduce today's
  apartment clearing **but** decide from their own knowledge; communication with a fixed delay.
- **Files:** `sim2/*`, adapter from `clearing.py` scenarios.
- **Tests:** agents never use cells they have not seen (information test, as in
  `test_information_model_plans_never_see_sampled_threats`); turn and speed limits; replay
  determinism by seed; knowledge exported per tick.
- **Demo:** viewer shows what each agent knows (fog per agent).

### v0.3-d Larger buildings (3 sessions)
- **Scope:** Floorplan v2, a topology-first generator (room graph -> layout) for houses with 8-15
  rooms and open areas, furniture families, scalable visibility (on-demand ray casting with a
  cache instead of the dense matrix).
- **Tests:** generator invariants (all rooms reachable, doors in walls, no overlaps) over many
  seeds; visibility equals the old dense matrix on the existing apartments; time and memory budget
  for a 15-room house.
- **Demo:** a full house cleared by four agents in the new viewer.

**v0.3 = a + b + c + d.**

### v0.4 and later
- Multi-storey buildings (floors linked by stair portals), external geometry import.
- Closed-loop task allocation under incomplete information, communication errors.
- Interface for external knowledge-fusion and active-perception modules, optional.
- Study E2 on the new model, with its own preregistration.
- Later: LLM planner benchmark, robot scouts, faster GPU simulator.

## F. First implementation slice

**v0.2.1 plus a small visible part of v0.3-a:** golden E1 test, replay schema v1 with an exporter
for existing results, and in the viewer the agent selection plus attention ray. It protects E1,
fixes the data contract everything else builds on, and already shows something new. About 2
sessions.

## G. Risks and open questions

- **Scientific:** visual realism can suggest more validity than the model has. Countermeasure: a
  "model view" without cosmetic layers, and every new scientific claim only through a new study.
- **Ethics and perception:** a cinematic CQB look raises the question what the project is for.
  It stays a search and coordination simulator; aiming is modelled as attention direction, not
  as weapon handling, and there is no development of engagement tactics. Worth deciding: show
  weapons at all, or neutral equipment.
- **Technical:** foot sliding and animation-state mismatch; dense visibility does not scale; a
  growing single HTML file; GPU/numpy differences in new code.
- **Assets:** only CC0 or clearly licensed models; no commercial game assets.
- **Organisational:** one-person project, large scope. Every milestone must end in a demo, and
  anything without a demo moves to v0.4.
- **Open:** weapons visible yes/no; target hardware for the viewer (laptop GPU?); whether E2
  should wait for `sim2` or run on the current model.

## H. Definition of done for v0.3

- The golden E1 test is green; E1 numbers reproduce from the tag and from main.
- Replay schema v1 is documented, versioned and validated in tests; old replays convert.
- A 15-room house is generated from a seed, cleared by four agents with separate attention and
  own knowledge, within the time and memory budget.
- The viewer shows rigged characters, agent selection, follow and cinematic cameras, knowledge
  overlays, perception events, run comparison and video export, and has a model view without
  cosmetic layers.
- Tests cover geometry invariants, information limits, motion limits, replay determinism and a
  viewer smoke test; CI green.
- README GIFs and a short demo video come from reproducible demo scenarios (seed + commit).
- No claim about real procedures; CLAIMS and ETHICS updated.
