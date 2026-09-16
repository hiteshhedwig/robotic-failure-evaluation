# Robotic failure evaluation: G1 and Go1

Both robots execute a 0.5 m/s forward command for 10 simulated seconds, with 2 s warmup and at least 2 m scored world-X progress. No lateral corridor is required. One optional world-frame force pulse lasts 0.2 s. Ground-truth contact and posture monitors are robot-specific.

| Robot | Pulse | Completed | Falls | Posture violations | Task timeouts | Valid | Fall 95% Wilson interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | 0.0 N | 8 | 0 | 0 | 0 | 8 | Not estimated |
| G1 | 25.0 N | 8 | 0 | 0 | 0 | 8 | 0.0%–32.4% |
| G1 | 100.0 N | 8 | 0 | 0 | 0 | 8 | 0.0%–32.4% |
| G1 | 175.0 N | 4 | 2 | 0 | 2 | 8 | 7.1%–59.1% |
| G1 | 250.0 N | 0 | 8 | 0 | 0 | 8 | 67.6%–100.0% |
| GO1 | 0.0 N | 8 | 0 | 0 | 0 | 8 | Not estimated |
| GO1 | 250.0 N | 7 | 1 | 0 | 0 | 8 | 2.2%–47.1% |
| GO1 | 500.0 N | 0 | 7 | 1 | 0 | 8 | 52.9%–97.8% |
| GO1 | 1000.0 N | 0 | 4 | 4 | 0 | 8 | 21.5%–78.5% |

## Interpretation

- Exploratory, conditional on each model, policy, ground and disturbance distribution; no physical-robot inference.
- Identical nominal reset repetitions are not independent reliability samples; no interval for references.
- Force tiers have matched schedules within each robot. Different robot masses, policies, time steps and severity ranges preclude a cross-robot robustness ranking.
- G1 175 N was selected after 100/250 N bracketing. Go1 tiers were selected after 20-1000 N pilot bracketing. These are exploratory, not held-out estimates.
- G1 physics 2 ms; Go1 physics 4 ms; policy and recorded-state traces 20 ms for both.
- Injection, physical response and outcome are recorded separately. Association does not establish an internal policy failure mechanism.
- Each pushed condition uses eight seeded direction/onset schedules: world +/-X or +/-Y; onset sampled in [3.0, 3.8] s, quantized to each physics step. See each saved design.json for realized parameters.
- Infrastructure/invalid episodes are excluded from robot-outcome denominators; separately counted total: 0.
- Zero falls in eight trials still permits an approximately 32% upper Wilson limit. There is no hardware safety claim or statistically demonstrated software improvement.

## Reproduction and evidence

Each trial contains scenario, manifest, timestamped state/command/contact traces, events, result and supervisor receipt. Rerun its scenario.json with scripts/run_experiment.py into a new output folder. The manifests retain source/model/policy fingerprints. Historical G1 results remain archived; current-code baseline checks verify that the adapter refactor preserves its behavior.
