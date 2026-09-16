# Add a robot or an experiment

The supported task is currently free-floating MuJoCo walking with a forward-distance
objective and an optional root-body force pulse. G1 and Go1 are the two validated
physical models. Extension points do not mean arbitrary robots are already tested.

## Everyday use: edit an experiment JSON

Use configs/experiments/walking-push-sweep.json. It contains:

~~~json
{
  "schema_version": 1,
  "id": "my-walking-test",
  "robots": ["g1", "go1"],
  "seeds": [0, 1],
  "task": {
    "duration_s": 10,
    "warmup_s": 2,
    "command": [0.5, 0, 0],
    "minimum_progress_m": 2
  },
  "disturbance": {
    "type": "root_force_pulse",
    "force_mode": "newtons",
    "duration_s": 0.2,
    "onset_range_s": [3, 3.8],
    "directions": [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]],
    "levels": [
      {"name": "reference", "magnitude": 0},
      {"name": "light", "magnitude": 100},
      {"name": "strong", "magnitude": 500}
    ]
  }
}
~~~

~~~bash
python scripts/evaluate.py --experiment configs/experiments/walking-push-sweep.json --output artifacts/my-evaluation --workers 2
~~~

This generates suite.json, executes each scenario in a fresh protected worker under
runs/, then writes report/report.md and report/summary.json. A valid task failure is
a result, not a failed experiment runner. Infrastructure failures still produce a
report and a nonzero pipeline exit code. Existing output directories are refused.

To inspect inputs before running:

~~~bash
python scripts/generate_suite.py --list-robots
python scripts/generate_suite.py --experiment configs/experiments/walking-push-sweep.json --output artifacts/my-suite.json
python scripts/run_experiment.py --suite artifacts/my-suite.json --output artifacts/my-runs --workers 2
python scripts/report.py artifacts/my-runs --output artifacts/my-report
~~~

Generation loads each selected model/policy to verify compatibility and obtain its
physics step, root-subtree mass and gravity; it does not step physics. Seeds select
a direction and requested onset once per schedule, matched across robots and force
levels. Direction vectors are normalized. Requested times are quantized to each
robot's physics grid during execution and recorded in manifest.json.

A zero-magnitude level is a nominal reference with no push. Labels are explicit
experiment metadata; report logic does not require names like reference or seed0.
The generator currently caps one local recipe at 256 trials; split larger campaigns.
The worker and report can already consume separately generated batches.

## Force units

- newtons: magnitude is an absolute force norm. Both robots receive the same selected
  vector for a condition, subject to their physics-time grid.
- body_weight: magnitude is a multiple of root-subtree mass × gravity magnitude.
  The generator resolves it to an explicit newton vector for each robot. It records
  the mass/gravity/scale with the scenario.

Use configs/experiments/body-weight-sweep.json for the second mode. The mass is the
robot's rooted subtree, so unrelated dynamic scene objects do not count toward its
weight. Normalization is a controlled experimental choice, not proof of equal
difficulty or fair cross-robot comparison.

## Add a robot profile

Drop a JSON descriptor into configs/robots/. Discovery is automatic; do not edit
run_trial.py, episode.py, monitor.py or reporting.py. A profile declares:

- A stable id and display label.
- An adapter import such as my_robot_package.adapter:MySimulation.
- Optional adapter_options passed as keyword arguments.
- Root body and floor geometry names.
- A policy-reset description.
- Explicit contact, posture and recovery monitor settings.

Start with configs/robots/go1.json. Its adapter can be reused without new Python if
the underlying model/controller integration is already supported. For a genuinely
new observation layout, policy interface or model, a small adapter is still required.
JSON cannot infer how an arbitrary learned controller should be called.

External profile files are supported without modifying the built-in directory:

~~~bash
python scripts/generate_suite.py --list-robots --profiles examples/robot-profiles
python scripts/evaluate.py --experiment examples/external-profile-experiment.json --profiles examples/robot-profiles --output artifacts/my-external-profile --workers 2
~~~

External profiles extend built-ins. Duplicate IDs are rejected; use a new ID for a
variant rather than silently replacing an installed robot. The example is the
existing Go1 under a different configuration ID, not a third robot model.

Generated scenarios embed complete profile snapshots. The worker can therefore
resolve an external profile in its own fresh process and rerun a saved scenario
without the original profile directory. Later edits to installed defaults do not
change the embedded snapshot. Adapter code/assets must still be available, and their
fingerprints are recorded. Legacy scenarios without snapshots resolve current
installed defaults; changed profile fingerprints remain visible in comparisons.

Profiles are trusted local Python import configuration. They are not a sandbox for
untrusted plugins.

## Adapter contract

See robot_eval/base.py for RobotAdapter and the optional MuJoCoAdapter helper.
G1 and Go1 are independent subclasses; neither inherits the other's controller.

An adapter is constructed as Adapter(command, seed, **adapter_options). It must:
1. Load an existing MuJoCo model and controller/policy; create fresh model/data/state.
2. Expose model, data, root, floor, config and counter. Root/floor are actual MuJoCo
   IDs. config.control_decimation is a positive integer.
3. Implement step() with the correct observation ordering, reset, action mapping and
   policy/controller cadence. Increment counter for each physics step.
4. Implement state(): time_s, world root position/linear velocity, tilt_deg, qpos,
   qvel, action, actual effort, and floor_contact_bodies.
5. Implement apply_force_world(force): clear prior applied forces and apply the given
   world-frame force at the root body center of mass.
6. Implement fingerprint(): versions and policy/model/config hashes.

The optional base implements state, force application and file fingerprints using
model_path, policy_path, config_path, action, and optional asset_directories. Supply
controller-specific metadata in fingerprint() as the current adapters do.

The 20 ms trace period must be divisible by the physics timestep. Unsupported timing
is rejected instead of silently changing cadence. Validate root/floor names and all
configured fall-contact bodies against the actual loaded model.

Existing helpers assume a free-floating root with qpos[:3]/qvel[:3] representing
world translation. A fixed-base arm, another simulator or a different task interface
needs additional task/state integration; adding only a JSON file is not enough.

Provision new assets using that upstream project's instructions or a dedicated
setup script. The existing bootstrap provisions only the two validated stacks.
Avoid adding a generic downloader or training pipeline to the evaluator.

## Verify a new integration

Before extending campaign size:
1. Run nominal walking and inspect actual ground-truth progress and contact names.
2. Verify normal support contacts do not trigger a fall.
3. Confirm physically invalid posture/contact is detected using an unambiguous
   simulated fixture and validated thresholds.
4. Apply one small pulse; verify realized force interval, integrated impulse and
   response. A tolerated pulse must not be labeled a failure.
5. Run a small seeded batch, reproduce an interesting failure, and test worker
   termination/deadline cleanup.
6. Review report grouping, missing data and uncertainty before making reliability
   claims.

A profile with the wrong root/floor or missing body fails as infrastructure, not as
a robot fall. Nonfinite physics state/warnings produce INVALID_SIMULATION.

## Reporting without per-robot changes

Reports read task parameters and condition metadata from each saved scenario,
outcomes from receipts and provenance from manifests. They do not hardcode robot
names, 10-second tasks, eight samples or one force bracket.

Groups separate robot, experiment, condition, force units/magnitude/duration, task
settings and available policy/model/profile/adapter/evaluator fingerprints. This
prevents accidentally pooling different configurations/software versions. Source
hashes missing from older artifacts remain explicit.

Infrastructure and invalid runs have separate counts and are excluded from robot
failure denominators. Identical nominal resets get no interval. Duplicate seed/push
configurations suppress the conditional Wilson interval rather than suggesting
independent samples. Repeated input directories are rejected. These checks do not
establish all statistical independence assumptions.

~~~bash
python scripts/report.py artifacts/batch-a artifacts/batch-b --output artifacts/combined-report
python scripts/compare.py --reference artifacts/reference --candidate artifacts/candidate --output artifacts/comparison.json
~~~

The comparator requires matched input scenarios and exposes changed fingerprints.
Reports support any number of repetitions, but do not turn a few smoke tests into a
validated reliability benchmark.

## Replay any supported robot

~~~bash
python scripts/render_trial.py --trial artifacts/my-runs/go1-light-seed0 --output artifacts/my-replay --title "My recorded experiment"
~~~

The replay resolves the saved profile, verifies policy/model hashes, and renders
saved states without another rollout. Camera defaults derive from initial root
height. Force arrows, event cards and progress limits are configuration-driven.
