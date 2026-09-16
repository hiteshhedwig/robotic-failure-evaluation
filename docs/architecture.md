# Architecture

The project evaluates two existing locomotion policies through one experiment path.
G1 and Go1 use independent model/policy adapters; the rest of the workflow is shared.

## Episode lifecycle and isolation

A scenario selects robot g1 or go1 (missing robot retains the original G1 default),
initial reset seed, velocity command, duration/warmup, progress objective and optional
world-frame force pulse. Validation rejects unsupported robots and malformed inputs.

The parent creates a fresh worker process group with a monotonic wall-clock deadline.
Each worker loads a new model, data and policy instance. It writes its manifest before
stepping, records sparse evidence, and atomically renames a complete result receipt.
The parent checks the receipt against the worker exit code. Missing/malformed receipts,
crashes and deadline expiry remain infrastructure outcomes. Process groups are
terminated and reaped; result directories are never overwritten. Batch concurrency
is bounded at two workers. No shared MuJoCo globals or control callbacks are installed.

## Robot adapters and reuse

| Component | G1 | Go1 |
| --- | --- | --- |
| Model/policy | Unitree RL Gym pinned assets | MuJoCo Playground policy/XML + Menagerie meshes |
| Policy observations | Angular velocity, gravity, command, joints, previous action, phase | Local linear velocity, gyro, gravity, joints, previous action, command |
| Policy state | LSTM hidden/cell reset per episode | Feedforward ONNX; previous action reset |
| Control | Existing PD calculation driving torque actuators | Existing position-actuator model and policy target scaling |
| Physics step | 2 ms | 4 ms |
| Policy update | Every 10 steps | Every 5 steps |
| Trace sampling | Every 20 ms plus terminal sample | Every 20 ms plus terminal sample |

The Go1 adapter reproduces the upstream deployment's observation order and
callback-before-step timing without requiring its gamepad or training imports.
Its full-collision flat-floor XML makes trunk contact observable. Both adapters
return position, velocity, tilt, contacts, qpos/qvel, actions and actual efforts.
Go1 also records its position targets separately.

The Go1 adapter reuses the G1 class's state/fingerprint helpers. This is intentionally
a small shared implementation, not a dynamically extensible middleware layer.

## Simulation and wall time

Task horizon, warmup, force schedule, contact dwell, posture dwell and recovery are
evaluated in simulation time. Force onset/duration are quantized to each physics
step; the realized interval and impulse are logged. Wall time is used only by the
supervisor deadline and runtime measurements.

The same controller and observation cadence is used regardless of how quickly the
machine can advance simulation. Physics/policy execution is CPU-only. EGL rendering
is an optional offline artifact-generation step.

## Monitoring and classification

Physics-step ground truth is evaluated independently of policy output:
- FALL: G1 pelvis or Go1 trunk contacts the floor continuously for 0.02 s.
- POSTURE_VIOLATION: tilt >60 degrees or root height below 0.45 m (G1) / 0.12 m (Go1)
  continuously for 0.1 s.
- Recovery after a pulse: tilt <=10 degrees, height >=0.65 m (G1) / 0.22 m (Go1),
  world vx within 0.25 m/s of command and |vy|<=0.25 m/s for 0.4 s.
- At the full horizon, require at least 2 m of scored world-X progress after warmup.

Fall ends the episode. Persistent posture violations remain recorded even if posture
later improves. Final precedence is fall, posture violation, distance completion,
then task timeout. Infrastructure/invalid simulation outcomes are separate.
A root-contact detector is deliberately narrower than every colloquial meaning of
falling; other unstable postures are not silently promoted to FALL.

Floor contacts are identified by actual MuJoCo geometry/body IDs. Ordinary foot
contacts are expected. G1's fixed head/arms share the pelvis body. Go1's calf bodies
contain foot geometries; the fall check concerns the trunk, not ordinary leg contact.

## Evidence and provenance

Each episode stores a resolved scenario, software/model/policy/source fingerprints,
initial state, detector limits, 50 Hz state/action/contact/force trace, physics-step
events, atomic task result and supervisor receipt. Failed infrastructure attempts
retain partial artifacts instead of inventing task outcomes.

Numerical warnings invalidate an episode; non-finite state or execution exceptions
are excluded from robot-outcome statistics. Cached MuJoCo kinematics/contact state
can lag qpos by one physics step. Detection and sampled trace resolution are recorded
rather than presented as continuous physical measurement.

Source fingerprints changed during the package rename to robot_eval. Original G1
evidence remains archived under its original fingerprint. A fresh G1 baseline
verified unchanged nominal progress after the refactor.

## Reproduction and comparison

The runner can execute a saved scenario unchanged in a new directory. Fresh reset,
fixed policy assets and recorded versions support reproduction; seeding alone is not
a guarantee of bitwise determinism. Selected local G1/Go1 failure repeats did match.

The comparator requires identical scenario IDs and resolved configurations. It flags
new task/infrastructure failures and reports changed fingerprints. It does not claim
statistical significance from one matched run or proof of a policy improvement.

Reports group by both robot and condition, so equal condition names are never pooled.
Within-robot force tiers use matched seeded schedules. Wilson intervals describe the
conditional pushed-trial proportions; identical nominal resets receive no interval.
The exploratory choice of severity ranges is disclosed. Cross-robot force sweeps are
not a fair robustness ranking.

## Demo provenance

Replay exports load recorded qpos/qvel into the matching model and render them
without running inference or advancing a new episode. States recorded at 50 Hz play
at 25 fps, plus labeled editorial holds. Checkpoint holds select the first saved
sample at or after the event, so displayed force/state has reached the event.
A red force arrow is an explanatory overlay, not another physical interaction.
Video manifests map source trials and hold checkpoints; FFmpeg fully decodes exports.
