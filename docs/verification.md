# Verification record

## Gate 1 — working walking baseline

Five independent fresh-process launches each completed ten simulated seconds:
3.7813 m forward progress during the evaluated eight seconds, peak tilt 3.663 degrees,
minimum evaluated root height 0.7625 m, no rigid-upper-body ground contact.
The same nominal state produced identical local traces. These repeats do not constitute
independent reliability samples. Evidence: artifacts/baseline-gate1/summary.json.

## Gate 2 — measurable outcomes, not injected-fault labels

Development cases used a +Y pulse at 3.0 s for 0.2 s:

| Force | Observed task outcome | Balance recovery confirmation latency after pulse |
| --- | --- | --- |
| 0 N | COMPLETED | Not applicable |
| 25 N | COMPLETED | 0.448 s |
| 100 N | COMPLETED | 1.454 s |
| 250 N | FALL | Not observed |

Actual applied impulses were 0, 5, 20 and 50 N*s respectively. Normal walking contacts
did not trigger a fall. A physically fallen model did. The recurrent-memory reset
was checked. Evidence: artifacts/push-pilot/ and artifacts/gate2-tests.log.

## Gate 3 — orchestration, crash handling and reproduction

The runner uses one subprocess per trial with a parent wall deadline, process-group
cleanup, atomic worker results and separate supervisor receipts.

Tests killed an actual initialized G1 worker with an already-written trace, checked
that it became INFRASTRUCTURE_ERROR, and verified process reaping. A parent deadline
became INFRASTRUCTURE_TIMEOUT; an unreachable distance objective became TASK_TIMEOUT.
Invalid input was not classified as robot failure. Evidence: artifacts/gate3-tests.log.

The selected strong-seed0 case was rerun in three fresh processes. All returned FALL
at 4.202 simulated seconds. Recorded qpos traces matched exactly on this machine.
This is local reproduction evidence, not a cross-machine determinism guarantee.

## Gate 4 — campaign, uncertainty and demonstration

The initial 32 episodes covered reference, 25 N, 100 N and 250 N conditions over eight
matched schedules. A midpoint follow-up added eight 175 N episodes. All 40 evaluation
episodes produced valid robot outcomes, with zero infrastructure failures.

- Reference: 8 completed.
- 25 N: 8 completed.
- 100 N: 8 completed.
- 175 N: 4 completed, 2 fell, 2 missed the forward-distance objective while upright.
- 250 N: 8 fell.

The report includes counts, matched design, conditional Wilson intervals and the
exploratory selection of 175 N. Zero observed falls among eight trials has an upper
95% Wilson limit around 32%; it does not establish a fall-free robot.

The full test suite passed 16 tests. See artifacts/tests.log. Four explanatory chapters
and one combined video are exported, with full-decoding metadata in
artifacts/demo/media-validation.json. Representative push, fall and task-timeout frames
were visually inspected for readable captions and faithful displayed measurements.

The tests and campaign are actual physics/policy execution. Video playback is a
clearly labeled reconstruction of saved physical states, slowed to 0.5x with reading
holds; it is not evidence of an additional policy rollout.

## Limits

One reduced G1 model, one pretrained policy, a flat floor and a finite impulse family
were tested. No hardware, new controller, training, certified safety, universal failure
attribution, large-scale benchmark or software-version improvement is claimed.
