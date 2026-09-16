# Robotic failure evaluation

Robots: **G1, GO1**. 72 valid robot trials from 72 attempts; 0 infrastructure/invalid outcomes.

| Group | Robot | Experiment / condition | Pulse | Completed | Falls | Posture | Task timeout | Valid | Infra/invalid | Fall 95% Wilson interval |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | G1 | legacy / reference | 0.000 N | 8 | 0 | 0 | 0 | 8 | 0 | Not estimated |
| 2 | G1 | legacy / mild | 25.000 N | 8 | 0 | 0 | 0 | 8 | 0 | 0.0%–32.4% |
| 3 | G1 | legacy / moderate | 100.000 N | 8 | 0 | 0 | 0 | 8 | 0 | 0.0%–32.4% |
| 4 | G1 | legacy / boundary | 175.000 N | 4 | 2 | 0 | 2 | 8 | 0 | 7.1%–59.1% |
| 5 | G1 | legacy / strong | 250.000 N | 0 | 8 | 0 | 0 | 8 | 0 | 67.6%–100.0% |
| 6 | GO1 | legacy / reference | 0.000 N | 8 | 0 | 0 | 0 | 8 | 0 | Not estimated |
| 7 | GO1 | legacy / moderate | 250.000 N | 7 | 1 | 0 | 0 | 8 | 0 | 2.2%–47.1% |
| 8 | GO1 | legacy / strong | 500.000 N | 0 | 7 | 1 | 0 | 8 | 0 | 52.9%–97.8% |
| 9 | GO1 | legacy / extreme | 1000.000 N | 0 | 4 | 4 | 0 | 8 | 0 | 21.5%–78.5% |

## Recorded task and group configuration

- Group 1: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration None; force mode newtons, requested magnitude 0.0; No interval: nominal reset repetitions. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 2: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 25.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 3: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 100.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 4: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 175.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 5: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 250.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 6: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration None; force mode newtons, requested magnitude 0.0; No interval: nominal reset repetitions. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 7: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 250.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 8: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 500.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.
- Group 9: task {"command": [0.5, 0, 0], "duration_s": 10, "minimum_progress_m": 2, "warmup_s": 2}; pulse duration 0.2; force mode newtons, requested magnitude 1000.0; Conditional pushed-trial interval. Fingerprints and resolved robot profiles are retained in summary/trial manifests.

## Interpretation

- Exploratory and conditional on recorded models, policies, task and disturbance sampling. No physical-robot inference.
- Robots, experiment IDs, conditions, task settings, force magnitude/mode/duration and available fingerprints define separate groups. Historical missing fingerprints stay explicit.
- Matched schedules and normalized body-weight forces do not establish equivalent difficulty or a cross-robot ranking.
- Wilson intervals are conditional proportions, not a guarantee of independence. Nominal repeats and duplicate seed/push configurations receive no interval. Inspect the experiment design.
- Injected disturbance, system response and measured outcome are distinct. Outcome detection does not establish internal policy cause.
- A lower fall count is not an improvement when other task failures replace falls. All valid task-failure categories remain visible.

## Evidence and reproduction

The resolved suite and each trial's scenario, manifest, trace, events, result and supervisor receipt preserve inputs and observations. Rerun a scenario into a new output directory and use scripts/compare.py with --reference and --candidate. Report generation never overwrites an existing directory.
