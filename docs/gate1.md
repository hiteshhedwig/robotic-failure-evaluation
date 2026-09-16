# Gate 1 — verified before adding disturbances

The pinned G1 TorchScript policy ran with the supplied model, effort gains, observation
scaling, phase and update cadence. The headless adapter imports the existing upstream
PD and gravity-orientation functions. GUI pacing is removed; task duration is simulation time.

Five fresh processes completed ten simulated seconds with a two-second warmup:
forward progress 3.7813 m over the evaluated eight seconds, peak tilt 3.663 degrees,
minimum evaluated pelvis height 0.7625 m, no pelvis-floor contact.

All five nominal runs were identical in this environment. Seeds did not introduce
random variation in those checks; they are reproducibility evidence, not independent
reliability samples. Raw evidence is in artifacts/baseline-gate1/.

The checkpoint is recurrent (an LSTM with hidden and cell buffers). Every process loads
it anew with both buffers zero. Resetting physics alone would not reset this policy.

The unmodified upstream graphical entry point was attempted, but its viewer startup
did not complete promptly in this session and was terminated. No successful GUI run is
claimed. The measured headless physics/policy runs are the verified baseline.

Compatibility adaptation: upstream creates float64 observations, which the supplied float32 checkpoint rejects on this PyTorch version. The adapter uses float32 observations, while preserving dimensions, scaling, phase, gains and cadence. The recurrent policy is explicitly reset at construction. Upstream files remain unmodified.
