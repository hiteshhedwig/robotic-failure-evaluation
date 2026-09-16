# Robotic failure evaluation

Robots: **G1, GO1**. 12 valid robot trials from 12 attempts; 0 infrastructure/invalid outcomes.

| Group | Robot | Experiment / condition | Pulse | Completed | Falls | Posture | Task timeout | Valid | Infra/invalid | Fall 95% Wilson interval |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | G1 | shared-walking-push-v1 / reference | 0.000 N | 2 | 0 | 0 | 0 | 2 | 0 | Not estimated |
| 2 | G1 | shared-walking-push-v1 / light | 100.000 N | 2 | 0 | 0 | 0 | 2 | 0 | 0.0%–65.8% |
| 3 | G1 | shared-walking-push-v1 / strong | 500.000 N | 0 | 2 | 0 | 0 | 2 | 0 | 34.2%–100.0% |
| 4 | GO1 | shared-walking-push-v1 / reference | 0.000 N | 2 | 0 | 0 | 0 | 2 | 0 | Not estimated |
| 5 | GO1 | shared-walking-push-v1 / light | 100.000 N | 2 | 0 | 0 | 0 | 2 | 0 | 0.0%–65.8% |
| 6 | GO1 | shared-walking-push-v1 / strong | 500.000 N | 0 | 2 | 0 | 0 | 2 | 0 | 34.2%–100.0% |

## Recorded task and group configuration

- Group 1: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration None; force mode newtons, requested magnitude 0; No interval: nominal reset repetitions. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 2: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 100; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 3: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 500; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 4: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration None; force mode newtons, requested magnitude 0; No interval: nominal reset repetitions. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 5: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 100; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 6: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 500; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.

## Interpretation

- Exploratory and conditional on recorded models, policies, task and disturbance sampling. No physical-robot inference.
- Robots, experiment IDs, conditions, task settings, force magnitude/mode/duration and available fingerprints define separate groups. Historical missing fingerprints stay explicit.
- Matched schedules and normalized body-weight forces do not establish equivalent difficulty or a cross-robot ranking.
- Wilson intervals are conditional proportions, not a guarantee of independence. Nominal repeats and duplicate seed/push configurations receive no interval. Inspect the experiment design.
- Injected disturbance, system response and measured outcome are distinct. Outcome detection does not establish internal policy cause.
- A lower fall count is not an improvement when other task failures replace falls. All valid task-failure categories remain visible.

## Evidence and reproduction

The resolved suite and each trial's scenario, manifest, trace, events, result and supervisor receipt preserve inputs and observations. Rerun a scenario into a new output directory and use scripts/compare.py with --reference and --candidate. Report generation never overwrites an existing directory.
