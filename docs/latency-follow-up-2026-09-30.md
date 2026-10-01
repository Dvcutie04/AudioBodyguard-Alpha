# Responsiveness follow-up — September 30, 2026

The expanded read-only preview remains functionally validated. Its final hosted Android Roku trace counted 54 frames, 52 janky frames, a 73 ms median and 250 ms 95th percentile. The interval included Next, closing, reopening, selecting a route, resuming, Next and finishing. It cannot establish the cost of any single action.

The same trace counted 52 slow draw-command frames and 21 slow UI-thread frames. The Skia/OpenGL GPU histogram placed 51 samples in its highest 4,950 ms bucket. This anomaly warrants renderer/device investigation; it does not prove a 4.95-second delay or establish the cause of the user's jitter. The software-rendered hosted emulator is not an installed-phone qualification environment.

## Measurement change

The Android walkthrough now records before/after `gfxinfo framestats` for three labeled interactions: Roku picture 3 → 4, resume → picture 4, and picture 4 → 5. The first baseline is captured before resetting aggregate counters, so reset does not erase the baseline. Functional destination assertions remain independent.

The parser selects newly started, completed, unflagged frames after the baseline watermark, rejects invalid timestamps, deduplicates repeated rows and reports unavailable baselines without inventing samples. It exports durations, sample count, median and maximum. Tiny per-interaction samples do not support reliable tail-percentile comparisons. No performance pass threshold is imposed on a hosted renderer.

These values describe rendered frames. UiAutomator and screenshot work occurs in the observation interval; no touch timestamp, native first-draw marker, energy evidence or physical outcome is measured. A missing sample is unknown, not zero latency. Aggregate counters and raw snapshots remain available for investigation.

## Runtime inspection

The illustrated setup activity preserves its root/ScrollView but rebuilds step content, header and footer on a new step. Progress writes are asynchronous and skip unchanged values. No blocking sleep, synchronous preference commit, network discovery or account request was found in this step-render path. Rebuilding a changed step is not sufficient evidence that it causes the measured jank. The previously removed tutorial choice/redraw resets remain removed.

No speculative native rendering change is made in this increment. Next: capture installed-phone FrameTimeline/Perfetto or equivalent iOS instrumentation, correlate layout/draw costs with individual actions, then reproduce a specific regression before repairing it. Measure AQSS eligible-event → independently observed physical response separately under the research charter's latency, energy, memory and ecosystem constraints. Production actuation remains closed.

Regression evidence: the new-frame parser test failed before implementation and passed afterward; additional cases cover an in-flight baseline frame, duplicated rows and unavailable evidence. Final CI observations are recorded in draft PR #32.
