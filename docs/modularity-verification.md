# Modular workflow verification

The refactor separates robot integration, monitoring, disturbances, experiment
generation, execution and reporting. G1 and Go1 remain the only validated physical
robot models. The external-profile example is still Go1, under a different ID.

## Checks actually executed

- Full suite: **41 tests passed**. Existing real-physics/controller/contact/process
  checks remain. New tests cover profile snapshots, external discovery, actual
  external-profile execution, matched schedule generation, force units, invalid
  recipes, mismatched bodies, aggregation boundaries, duplicate trials, all-infra
  reports and the complete one-command two-robot pipeline.
- Absolute-force JSON recipe: **12 valid episodes**, zero infrastructure failures.
  Both robots completed references and 100 N conditions; both failed the 500 N
  condition in the selected two schedules. See newton-sweep/report/report.md.
- Body-weight JSON recipe: **6 valid episodes**, zero infrastructure failures.
  Reference, 0.25 body-weight and 1.5 body-weight conditions were resolved from each
  loaded robot's rooted mass and gravity, then executed as explicit force vectors.
  This is an integration check, not a robot robustness ranking.
- External profile JSON: **2 valid Go1 episodes**, zero infrastructure failures.
  A directory outside configs/robots selected the existing Go1 adapter. The profile
  was embedded in scenarios and loaded in fresh workers without editing the runner,
  monitor, force scheduler or report.
- Archived motion compatibility: **8 actual reruns**, all passed. G1 baseline,
  recovery, fall and upright timeout plus Go1 baseline, recovery, fall and posture
  violation preserved outcomes, policy/model hashes and recorded qpos traces
  locally. See reference-checks/summary.json.
- Generic recorded-trial replay: the external Go1 profile's saved trial was rendered
  through scripts/render_trial.py and fully decoded. It loaded the saved profile
  and matching policy/model assets without stepping a new rollout.
- Current report logic was also run on the original 72-episode evidence, without
  overwriting that evidence.

These checks are separate from the archived 72-episode exploratory campaign.
They are not added to its reliability denominator. The small new recipes demonstrate
software integration and configuration handling, not a new statistically powered
evaluation or an improvement to either policy.

## Reproduce

Use new output directories:

~~~bash
python -m pytest tests -q
python scripts/evaluate.py --experiment configs/experiments/walking-push-sweep.json --output artifacts/check-newtons --workers 2
python scripts/evaluate.py --experiment configs/experiments/body-weight-sweep.json --output artifacts/check-body-weight --workers 2
python scripts/evaluate.py --experiment examples/external-profile-experiment.json --profiles examples/robot-profiles --output artifacts/check-external --workers 2
python scripts/check_reference_runs.py --cases configs/regression/reference-runs.json --output artifacts/check-reference-runs
~~~

## Evidence

- [Test output](../artifacts/modularity/tests.log)
- [Absolute-force report](../artifacts/modularity/newton-sweep/report/report.md)
- [Body-weight report](../artifacts/modularity/body-weight-sweep/report/report.md)
- [External-profile report](../artifacts/modularity/external-profile/report/report.md)
- [Motion compatibility](../artifacts/modularity/reference-checks/summary.json)
- [Generic replay](../artifacts/modularity/profile-replay/trial.mp4)
- [Replay validation](../artifacts/modularity/profile-replay/media-validation.json)
- [Original campaign through the new reporter](../artifacts/modularity/archived-campaign-report/report.md)
- [Verification summary](../artifacts/modularity/verification-summary.json)

## Boundaries

A JSON descriptor selects an existing adapter and explicit model-specific monitor
limits. A new policy observation/action format still requires an adapter and actual
integration verification. Assets and controller dependencies must be provisioned.
Existing helpers target free-floating MuJoCo walking; other tasks/backends need
corresponding integration. No third physical platform has been tested.

Generated scenarios snapshot profile settings. Legacy scenarios still resolve
installed defaults and expose changed profile hashes. Grouping separates available
source/model/policy/profile fingerprints, so fresh refactor results are not silently
pooled with historical code versions.
