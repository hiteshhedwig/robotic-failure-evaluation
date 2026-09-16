> Historical two-robot integration checkpoint. See [modular workflow verification](modularity-verification.md) for the current architecture and tests.

# Two-robot extension verification

The shared runner now dispatches G1 or Go1 based on the scenario's robot field. Missing robot retains G1 compatibility. Unsupported robots fail before simulation as infrastructure errors. The package was renamed from humanoid_eval to robot_eval.

## Existing components

G1 continues to use the original pinned Unitree RL Gym model and recurrent policy. Go1 uses Google DeepMind MuJoCo Playground revision 56420458c8d81acd6942779d9dab327382117175 and Menagerie revision 370c43965323c0944b433b202aac5058b5f907a9. Its supplied ONNX policy is not trained here.

The Go1 adapter follows play_go1_joystick.py observation order, previous action reset, home keyframe, action scale 0.5, position actuators, 4 ms physics and 20 ms policy period. Direct scenario commands replace the gamepad. The full-collision flat-floor XML is used to make trunk-ground contact measurable. The virtual file asset map follows upstream get_assets() without importing JAX/training dependencies.

ONNX Runtime 1.20.1 is isolated in .runtime/python. Existing environment packages and upstream sources were not modified.

## Verified gates

1. Existing-policy Go1 baseline: completed the distance task with observable leg actions and normal floor contacts.
2. Shared integration: both robots use the same protected subprocess runner, 50 Hz trace format, report and comparator. Actual Go1 actuator effort is recorded separately from its position targets.
3. Outcome checks: real walking contacts produce no false fall; an upside-down passive Go1 fixture creates real trunk contact and triggers FALL. Initial side-on fixture did not settle onto the trunk and was corrected to an unambiguous upside-down physical fixture. Robot-specific heights prevent applying humanoid thresholds to a quadruped.
4. Exploratory campaign: 32 Go1 episodes, all valid and zero infrastructure failures. 250 N: seven completions and one fall. 500 N: seven falls and one posture violation. 1000 N: four falls and four posture violations. Eight nominal references completed.
5. Reproduction: two fresh-process repeats of strong-seed0 produced FALL at 5.208 simulated seconds with 262 trace samples and maximum joint-position difference zero locally.
6. Infrastructure: actual Go1 worker kill after trace creation classified INFRASTRUCTURE_ERROR. Parent 0.1 s deadline classified INFRASTRUCTURE_TIMEOUT.
7. G1 compatibility: current shared-code nominal progress matched the archived baseline exactly locally. Original G1 evidence and source fingerprints were preserved.
8. Full test suite: 22 passed. A new report test proves equally named G1 and Go1 conditions are not pooled.

The first Go1 pilot attempt hit an adapter metadata-key duplication before stepping and correctly produced infrastructure-error receipts. It was fixed and rerun in a separate output directory; failed receipts remain in artifacts/go1/pilots. They are excluded from evaluation statistics. Exploratory pilots and bracketing also remain separate from the 32-episode campaign.

## Evidence

- artifacts/two-robot-tests.log
- artifacts/go1/campaign/batch.json
- artifacts/two-robot/evaluation/report.md
- artifacts/go1/reproductions/summary.json
- artifacts/go1/infrastructure/summary.json
- artifacts/two-robot/g1-compatibility-check.json
- artifacts/go1/demo/media-validation.json
- artifacts/demo/two-robot-media-validation.json

The archived G1 test/report documents describe the original single-robot checkpoint. This record and the current README describe the extension. Historical results are not relabeled as executions of the new source version.

## Interpretation

The force sweep is exploratory and differs between robots. Identical nominal repeats are reset checks. Pushed schedules are matched within each robot; no cross-robot ranking or cross-machine determinism claim is made. A lower confirmed fall count at the largest force does not mean higher reliability when the remaining trials violate posture. Failure detection and attribution remain separate.
