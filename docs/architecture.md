# Focused evaluation architecture

The system evaluates one stock Unitree G1 walking policy in one flat-ground MuJoCo
model. It is a compact CLI workflow, not general-purpose robotics middleware.

## Ownership

Upstream provides the twelve-leg-joint robot model, pretrained recurrent policy,
observation scaling, default pose, PD gains, gait-phase input and control cadence.
The adapter imports upstream PD and gravity-orientation math. This project owns
experiment isolation, pulse scheduling, ground-truth monitoring, outcome classification,
artifact persistence, analysis, matched comparison and recorded-state replay.

The upstream observation buffer defaults to float64, which the supplied float32
checkpoint rejects in the inspected PyTorch version. The adapter uses float32 input.
It removes viewer pacing and uses simulation-step counts rather than wall time for
episode length. Vendor files are not patched.

## Timing and reset

- Physics step: 0.002 s (500 Hz).
- Policy update: every ten physics steps (50 Hz).
- One fresh process and freshly loaded/reset LSTM per episode.
- Policy hidden/cell state, previous action, phase counter and physics all start fresh.
- Task horizon and force scheduling use simulation time.
- Parent deadlines use monotonic wall time; process groups are terminated and reaped.
- Up to two worker processes per batch; policy inference has one Torch CPU thread.
- A new run directory is required. Existing evidence is never silently overwritten.

Each pulse is an actual external Cartesian force applied through MuJoCo's
xfrc_applied array, at the center of mass of the rigid upper-body/pelvis body.
The force is cleared every physics step outside its scheduled interval. Actual
onset/end and integrated impulse are recorded. Directions are in world coordinates.

## Task and outcome definitions

The robot receives a forward velocity command of 0.5 m/s. The task is to cover at
least 2 m in world +X during the eight-second scoring interval after a two-second
warmup, without a confirmed fall or persistent posture violation. There is no
lateral corridor constraint in this prototype.

| Outcome | Evidence |
| --- | --- |
| COMPLETED | Full task horizon, progress >=2 m, no confirmed fall or persistent posture violation |
| FALL | Ground contact on the model's pelvis/rigid-upper-body body persists for 0.02 s |
| POSTURE_VIOLATION | Tilt >60 degrees or root height <0.45 m persists for 0.1 s, without a confirmed fall |
| TASK_TIMEOUT | Valid simulation reaches the task horizon without required forward progress |
| INVALID_SIMULATION | Simulator warning or invalid numerical state makes the episode unsuitable for robot reliability inference |
| INFRASTRUCTURE_ERROR | Setup/worker/receipt failure, including worker death without a completed result |
| INFRASTRUCTURE_TIMEOUT | Parent wall-clock budget expires |

The reduced model's head and fixed arms share the pelvis body. Thus FALL is an
operational upper-body-contact criterion for this model, not a universal fall detector.
Foot-floor contact is normal. Tests exercise actual walking and physically fallen
states; threshold correctness is not claimed for all imaginable poses or models.

Balance recovery is observed, not implemented by the evaluator. It requires tilt
<=10 degrees, height >=0.65 m, |world vx - commanded vx| <=0.25 m/s and
|world vy| <=0.25 m/s for 0.4 s after the pulse ends. A trial can recover balance
and still miss the forward task. No getting-up policy is provided.

Contacts and kinematics are inspected at physics-step resolution; sampled traces
are written at 50 Hz with terminal event samples. Timing precision is bounded by
physics stepping and trace sampling, not by an infinitely precise sensor.

## Evidence and reproduction

The immutable run input is scenario.json. Manifest metadata includes model-tree,
checkpoint and configuration hashes, upstream revision, package versions, initial
qpos/qvel and recurrent-reset semantics. Evaluation source hashes identify the worker
and monitor implementation.

trace.jsonl contains position, velocity, joint state, policy output, applied force and
floor-contact bodies. events.jsonl records injection, task start, posture/fall detection,
recovery and termination. result.json is written atomically by the worker;
supervisor.json records exit status, wall deadline and infrastructure classification.
A crash may leave only partial traces and a parent receipt; that is not a robot fall.

No database, broker, ROS graph or policy training is required. Failed case
reproduction reruns the recorded scenario from the initial state. Full checkpoints of
arbitrary mid-episode LSTM state are not implemented.

## Statistical scope and regression comparison

Eight seeded direction/onset schedules are matched across force levels. Initial
reference repeats are identical and do not justify independent reliability intervals.
Pushed-condition Wilson intervals are conditional on the stated sampling distribution,
fixed model, policy, floor and task. The 175 N tier is explicitly exploratory, selected
after the initial 100/250 N bracket; it is not a held-out benchmark.

scripts/compare.py refuses differing scenario inputs/IDs and compares categorical
outcomes for matched runs. It flags new task failures or infrastructure errors.
It is checked against actual reproduced failures. No improved controller or new policy
version is claimed. Formal statistical software-version regression testing is outside
this small prototype.

## Replay provenance

Videos render saved physical qpos/qvel records through MuJoCo. They do not rerun the
policy or synthesize a new trajectory. Source states are sampled at 50 Hz and played
at 25 fps (0.5x). Explicit reading holds freeze a source frame and its telemetry.
Force arrows are explanatory geometry added only during rendering.

CPU OSMesa rendering was verified but slow; EGL rendering was used for the exported
clips. Simulator execution and policy inference remain CPU-only. GUI startup is not
required or claimed as verified.
