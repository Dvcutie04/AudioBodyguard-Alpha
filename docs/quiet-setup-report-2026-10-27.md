# Android 0.37 quiet check with setup notes

October 27, 2026. This is the Android counterpart to the reviewed iPhone/iPad
intake work, prepared independently while those native checks finished under
the owner's request to keep phases moving. Android Live Test becomes
0.37-quiet-setup-live-input/build 40. iPhone/iPad source remains 0.38.0/build 1.

## Explicit report handoff

Sound → Output inventory → Quiet output check → Start quiet check → Review
check report → Add setup notes opens the existing optional worksheet with the
exact already-reviewed quiet report. Its original phone-clock review time,
run label and framework return trace stay unchanged. Notes receive their own
review time. The installed build envelopes must match exactly.

This adds no audio backend, signal, volume change, microphone capture or new
worker. The 0.36 quiet-check contract remains intact. A returned Android write
count and cleanup call are still software observations, not audible output,
silence, native retirement, calibrated latency or protection.

The worksheet accepts one typed attachment: inventory or quiet check. A single
main-thread handoff slot retains at most one bounded snapshot. Replacing either
kind retires its old opaque ticket. Take is single-use; wrong/stale tickets and
stale discard cannot consume another report. Intents carry a process-local
label, never report text or an audio handle. Labels provide no authentication
or output authority. Missing process history shows unavailable details rather
than reconstructing a report. The former inventory-only fixture remains intact;
the app now uses the shared typed slot through both explicit entry points.

## Review and lifetime

Clear notes keeps the attachment. Remove output details keeps the notes. Back
from review returns to the same draft, then Back closes it and returns to the
original quiet report. Recreating the worksheet retains its typed attachment
and frozen review. Closing or a new process discards the draft. A completed
quiet capture and its report are not restarted or rewritten by any handoff.

Standalone and inventory reports preserve their existing v1 output and limits.
A quiet attachment uses v2, a separate Attached quiet check report section,
and limits of 49,152 UTF-16 units and 49,152 UTF-8 bytes. Those include the
already bounded quiet report, brief quoted notes and section labels. Notes
retain their original 160-unit per-field limit. The original quiet report is
copied verbatim once. No user audio, raw photos or system logs are added.

Native Share sends the exact frozen combined preview after a separate tap.
Framework-only and physical-uncertainty notices remain visible. Synthetic
notes in instrumentation are never presented as the owner's arrangement.

## Verification and remaining gates

Tests-first and final source-bound receipts belong to the draft PR: model
validation and handoff identity, actual native quiet stream/report, combined
preview/Intent equality, configuration retention, Clear/remove, immediate
parent return, normal/large text, the full existing Android regression, lint,
APK identity/signature, original artwork and test-code exclusion. The delivered
APK must be the one inspected in that full run.

The owner still has not supplied a physical phone report. N2b–N5, actual setup,
independent acquisition/calibration, protection and signed iPhone distribution
remain pending. Continuing software preparation does not supply those facts.
