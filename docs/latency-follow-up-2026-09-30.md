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

## Observed interaction evidence

Raw capture revision: `7a0e62893bcef5c99e547038d7886f081a70173c`, [native walkthrough run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36797456069). All seven jobs passed for that capture. The initial parser allowed one implausible timestamp; this follow-up repairs that evidence boundary and reprocesses the original snapshots.

| Interaction | New usable frames | Median / maximum | Qualification |
|---|---:|---|---|
| Picture 3 → 4 | 3 | 64.4 / 118.4 ms | Hosted rendered-frame samples only |
| Resume → picture 4 | 3 | 71.4 / 120.2 ms | Hosted rendered-frame samples only |
| Picture 4 → 5 | 2, plus 1 invalid | Withheld | Timestamp evidence is unqualified |

The invalid row reported IntendedVsync `456634339846` and FrameCompleted `7305508662576702820` nanoseconds, against a dump uptime of `459141` milliseconds. Its apparent duration is roughly 231 years. That is adverse timing evidence, not a real 231-year response. The cause of the bad field is not established.

The repaired parser uses the dump uptime with a generous 60-second diagnostic horizon, also bounding any individual duration to that horizon. This is a plausibility budget, not a performance target or a claim that long delays are acceptable. Missing clock evidence, missing baselines, invalid new timestamps or absent usable samples withhold the median/maximum qualification. Invalid evidence is counted and retained in raw snapshots; it is never clipped into a fast value or silently used in a percentile. Valid-subset durations remain diagnostic data when one frame invalidates the transition.

The same capture's aggregate was 50/53 janky frames, median 73 ms and p95 350 ms. Variation and corrupt timing reinforce the need for an installed-device trace. Two three-frame samples cannot establish smoothness, improvement over an earlier run or the charter's physical-response bound. No speculative native rendering change is claimed.

Parser regression with the actual implausible field failed first, then passed after repair. Additional coverage tests unavailable clocks and mixed valid/invalid samples. The complete local suite passes 1,813 tests and 14 subtests. Final publication/CI status is recorded in PR #32.
