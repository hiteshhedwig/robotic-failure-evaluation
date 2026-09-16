# G1 walking under controlled pushes

The task is forward walking for ten simulated seconds, with a two-second warmup and at least 2 m of evaluated forward progress. A fall is sustained pelvis/rigid-torso ground contact. No lateral corridor constraint is imposed; lateral displacement is reported in each trial.

| Pulse force | Completed / valid | Falls / valid | Task timeouts / valid | Fall proportion, 95% Wilson interval | Median forward progress | Median recovery latency among recovered completions |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0 N | 8/8 | 0/8 | 0/8 | Nominal repeated baseline; no interval | 3.781 m | Not observed / not applicable |
| 25.0 N | 8/8 | 0/8 | 0/8 | 0% [0%, 32%] | 3.773 m | 0.411 s |
| 100.0 N | 8/8 | 0/8 | 0/8 | 0% [0%, 32%] | 3.495 m | 1.590 s |
| 175.0 N | 4/8 | 2/8 | 2/8 | 25% [7%, 59%] | 1.972 m | 2.038 s |
| 250.0 N | 0/8 | 8/8 | 0/8 | 100% [68%, 100%] | 1.051 m | Not observed / not applicable |

## How to interpret this

- Each push lasts 0.2 s. Direction is sampled from world +/-X and +/-Y, and onset from one 0.8 s gait cycle [3.0, 3.8], quantized to 2 ms. Configs record all realized values.
- The eight schedules are matched across severity levels. Cross-condition results are paired, not independent groups. The intervals describe within-condition sampling under the stated design.
- The 175 N follow-up was chosen at the midpoint after 100 N completed and 250 N fell in all initial schedules. All initial results are retained. This is exploratory testing, not a held-out benchmark.
- Zero observed falls among eight pushed trials still leaves substantial uncertainty. It does not establish a fall-free controller.
- Infrastructure errors are counted separately and excluded from robot-outcome denominators. There were 0 in these campaigns.
- Recovery latency includes the 0.4 s verification window and is reported only for trials that recovered and completed. Survivors are not assigned a fabricated time-to-fall.
- The reference repeats have identical nominal initial conditions; their repetition is a reset/reproducibility check, not eight independent reliability samples.
- Ground truth is simulator state/contact data, not a controller success signal. Body orientation, force intervals, policy output, and contacts are timestamped. Fall association does not diagnose the policy's internal cause.

## Evidence and reproduction

Each trial directory contains scenario.json, manifest.json, trace.jsonl, events.jsonl, result.json and supervisor.json. Parent process logs are in .logs/. Recorded scenario files can be passed unchanged to scripts/run_experiment.py --scenario ... --output NEW_DIRECTORY. Same configurations are reproducible; bitwise agreement is not promised across other machines or simulator builds.
