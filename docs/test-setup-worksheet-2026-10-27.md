# Two-phone setup worksheet — 0.34

October 27, 2026. The owner requested the next build while testing 0.33.
The next physical gate is still the actual N2b inventory. This increment
implements the already researched phone-only intake requirements from the
[qualification record](n2b-lab-qualification-record.md),
[private inventory protocol](n2b-inventory-preparation-2026-10-24.md) and
[two-phone research](phone-output-research-2026-10-24.md). It adds a small
manual worksheet to both mobile app sources, before a playback adapter.

## Decision and scope before implementation

The existing JSON checker expects a computer-side private record. The owner
has two phones. A worksheet in Sound makes six useful observations shareable
from either phone: playback phone/model/OS, intended output, second phone,
recording app/mode, placement and constraints. These are explicitly user notes,
not detected routes, verified acquisition or a complete N2b record. Every
answer is optional and blanks display Unknown. Unavailable equipment can be
entered as such. Compiler/backend, ownership, negotiation, capture, calibration,
clock mapping and consent still need their own review and evidence.

| Choice | Resource and truth implications | Decision |
| --- | --- | --- |
| Wait for a computer-side form | No implementation work, but contradicts the reported phone-only setup | Add a phone worksheet using the same intake requirements |
| Discover another phone or probe playback | Adds radio/audio owners and new backend/acquisition research | Outside this increment |
| Six bounded optional notes, explicit review and native sharing | Small foreground form, no polling or new audio/radio API | Select |
| Save drafts to disk automatically | More retained user-entered text and restoration obligations | Keep a bounded in-memory draft instead |

This is implementation of the existing researched inventory and review/share
contracts, not a new substantive output-backend investigation. The standing
model-switch requirement still applies before that later investigation.
Resource comparisons above are design decisions, not handset measurements.

Current primary UI references were consulted for implementation details:
[Android LengthFilter](https://developer.android.com/reference/android/text/InputFilter.LengthFilter),
[Activity configuration retention](https://developer.android.com/reference/android/app/Activity#onRetainNonConfigurationInstance()),
[SwiftUI TextField](https://developer.apple.com/documentation/swiftui/textfield) and
[autocorrection controls](https://developer.apple.com/documentation/swiftui/view/disableautocorrection(_:)).
The existing native Sharesheet/presenter and 0.33 sharing research are reused.
Retain only plain note strings and an immutable report across configuration;
never retain an Activity, View or controller. A missing retained draft opens an
empty form. On iOS the presentation parent owns the draft so sheet content
rebuilds retain the same notes and frozen report. Process recreation and closing
discard notes.

## Contract

Sound → Test setup → Review setup report → Share setup report.

The form has six single-line fields, each bounded to 160 UTF-16 units with
surrogate-safe clipping at the input boundary. Report capture rejects oversized
values, invalid UTF-16, malformed installed-build envelopes and out-of-range
phone clocks. It normalizes line/control/format separators, escapes quotes and
backslashes, and presents each supplied value in quotes. This prevents notes
from masquerading as an added report field. Blank values remain Unknown.

Review freezes one text snapshot including the installed build and phone-clock
UTC review time. The shared body is exactly the reviewed body. It is bounded
to 4 Ki UTF-16 units and 8 KiB UTF-8. A fixed notice remains above Share.
Back returns to the same draft; Clear removes its values; Close and a new app
process open an empty worksheet. Rotation and text-size changes preserve the
bounded in-memory draft/review when the platform retains it. Background and
native Cancel/Copy/receiver round trips do not regenerate the report.

The worksheet asks for no passwords, account, network address, serial number,
audio, recognized words or photo. User-entered technical notes must be reviewed
before sharing and can still contain information the user chooses to enter.
The app supplies only text to the native share UI, with no recipient, file or
URI. A selected target or clipboard can retain that explicitly shared text.
The app writes no worksheet file or preference and collects no telemetry.

The fixed report facts remain: actual playback route/format Unknown, backend
and ownership review Pending, independent capture Not recorded, calibration
and clock mapping Unknown, playback/capture consent Not collected, and physical
output/protection Not verified. A completed worksheet neither fills all eight
N2b rows nor authorizes recording, playback, a trial or successor activation.

## Verification obligations

A tests-only source is preserved before implementation. Its Kotlin/Swift report
cases must reject the missing model API, and real native UI tests must reach
Sound and fail on the missing Test setup entry before accepting the candidate.
Then verify optional/empty notes, quoted text and control
normalization, bounds/Unicode, build/clock validation and frozen snapshots.
Native checks cover six-field entry, preview without sharing, Cancel without
delivery, exact native text handoff, Back/edit/Clear, rotation/background,
process/Close clearing and large text on Android, iPhone and iPad. Native
permissions and connection state remain unchanged. Probes stay outside the APK.

The implementation PR records actual red/green runs, source identities,
screenshots, clipboard/receiver receipts and APK byte/signature identity.
iPhone/iPad simulator coverage is separate from signed iPhone distribution,
which still depends on the owner's Apple setup. N2b–N5 remain pending physical
inventory and qualification.

The tests-only source is `0e6fb98f8ca19bc657ae2e32f1f7ebdb433dc4fa`.
Android native run 40526754708 reached Sound and failed because its Test setup
entry was absent; core run 40526754639 rejected the missing Kotlin report API.
The same native run reproduced the missing worksheet entry on iPhone and iPad.
The original Swift unit job remained queued. The iPhone workflow also reruns
that exact preserved Swift source in isolation and requires its missing-API
diagnostic, keeping the negative control independent of the implementation.
Final model, simulator/device-build and installer results belong to the PR.
