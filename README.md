# Audio Bodyguard Alpha

Audio Bodyguard Alpha is the development repository for AQSS-36-OMEGA. It contains Python reference implementations and tests for acoustic inference, controller authority, protected device handoff, and physical verification, plus Swift and Kotlin feedback contracts and a separate C11 scripted output lab.

**INFERENCE IS NOT REALITY. AI proposes. Policy authorizes. Physical Commit verifies.**

The alpha includes simulations, mocks, and synthetic conformance tests. Passing software tests do not establish physical output containment, acoustic safety, or production readiness. The endpoint handoff barrier and production execution guard intentionally remain closed.

The [2026-10-11 pre-beta audit](docs/pre-beta-audit-2026-10-11.md) records local
repairs and **1,867 passing Python tests plus 19 subtests**. Fresh native CI,
a signed TestFlight build and actual phone trials remain required before beta
invitations. The current beta scope is the read-only interface and setup guides.

The [October 15 Android live-input increment](docs/android-live-sound-check-2026-10-15.md)
adds an optional **Sound → Live sound check** using real foreground microphone
samples. Its separate **Audio Bodyguard Live Test** APK can coexist with the
preview. Digital input levels do not establish acoustic safety or active
protection. TV control and qualified output paths remain unavailable.

The [private support report](docs/private-support-report-2026-10-22.md)
lets testers preview installed build details and up to five temporary meter
summaries in **Settings → Advanced Settings → Private support report**, then
choose **Share support report**. It excludes audio, words, photos, TV/network
details and generic logs. Native sharing does not prove recipient delivery or
physical audio protection.

The [0.21 Insights entry](docs/insights-sound-checks-2026-10-22.md) opens
**Recent sound checks** directly from Insights. Review or clear the existing
five temporary completed-check summaries, then Close returns to Insights.
The microphone tool does not open; Audio trends remain separate.

The [0.20 report choice](docs/support-report-choice-2026-10-22.md) lets testers
leave recent sound checks out of the shared text without clearing recaps.

The [0.22 startup cleanup repair](docs/input-activation-cleanup-2026-10-23.md)
keeps iPhone microphone ownership through cleanup when session configuration
throws. A cleanup error blocks both input tools until the app process exits.

The [0.23 Voice guidance](docs/voice-error-guidance-2026-10-23.md) replaces
common Android speech error numbers with a short explanation and next step.
Stopping, permission checks and cleanup retain their existing behavior.

The [0.24 iPhone Voice guidance](docs/ios-voice-stop-guidance-2026-10-23.md)
distinguishes unavailable microphone access, speech access, recognition and input
when a running check stops. Recognition or input loss no longer points to
permissions when the permission checks have passed.

The [0.25 recap shortcut](docs/recap-support-report-2026-10-23.md) adds
**Review support report** inside Recent sound checks on Android and iPhone/iPad.
Review the visible recap snapshot, optionally exclude checks, then explicitly
Share. Back returns to the same recap list.

The [0.26 responsiveness evidence repair](docs/frame-clock-evidence-2026-10-23.md)
rejects comparisons when recorded Android uptime regresses and retains hosted
renderer snapshots around report Open and Back. App behavior remains 0.25;
these diagnostics do not establish installed-phone smoothness or physical latency.

The [0.27 process attribution repair](docs/frame-process-evidence-2026-10-23.md)
also requires one matching observed PID/name pair in both frame dumps. Missing,
changed, ambiguous or malformed process headers withhold attribution and timing
summaries. Matching headers do not prove uninterrupted process/device identity;
the app flow and physical qualification boundaries remain unchanged.

The [0.28 completion evidence repair](docs/frame-completion-evidence-2026-10-24.md)
preserves an observed frame start even when its completion field is unreadable.
New unreadable completions withhold timing summaries while retaining valid-subset
diagnostics; an already observed start cannot become a new frame on completion.

The [0.29 uptime evidence repair](docs/frame-uptime-evidence-2026-10-24.md)
requires complete integer uptime tokens and agreement between repeated headers.
Malformed or conflicting clocks withhold timing summaries; existing valid-subset
diagnostics remain. Hosted observations do not establish a speed improvement.

The [0.30 frame-column evidence repair](docs/frame-schema-evidence-2026-10-24.md)
rejects duplicate or missing required column names before attributing frames.
The diagnostic JSON reports schema availability; the app's support report and
input flow retain their existing behavior.

The [0.31 CSV evidence repair](docs/frame-csv-evidence-2026-10-24.md)
handles malformed quoting and CSV field-limit errors as unavailable diagnostics.
These read errors withhold attribution and let native UI checks continue.
Valid quoting still works within the existing raw-capture limits.

The [N2b inventory preparation](docs/n2b-inventory-preparation-2026-10-24.md)
adds a private template and checker for the existing host, output route,
independent capture and related protocol inventory. It checks bounded local
evidence hashes while keeping every physical gate pending. The owner has now
confirmed two phones; the next research package reviews an owned mobile-output
path. Exact backend/route/capture details remain pending. The inventory-file
preparation itself does not change the mobile app.

The [0.32 phone-output research and preflight](docs/phone-output-research-2026-10-24.md)
adds **Sound → Output inventory** on Android. Tap **Refresh outputs** to see
this phone's current model/OS, available output types and advertised format
capabilities. The details clear when leaving. No sound is played, and actual
playback route and negotiated format remain unknown. The iPhone app remains
at 0.31; its signed installation and all physical output gates stay pending.

The [0.32.2 output freshness repair](docs/output-inventory-freshness-2026-10-25.md)
withdraws displayed Android inventory rows when an output-change notice arrives.
Tap **Refresh outputs** to read again. Background visits retire their listener,
so late old callbacks cannot alter a newer snapshot. The Samsung setup repair
from 0.32.1 stays included; iPhone source remains 0.32.1.

The [0.32.3 TV-picture review](docs/tv-guide-review-2026-10-26.md)
checks the nine other supported TV brand choices and their platform variants.
It separates TV codes from phone entry and opening the phone scanner from scanning, makes optional account choices neutral,
adds matching LG/VIZIO/Google TV phone checks and a manual Google TV fallback,
and makes Philips/Fire decision paths return correctly with Back. The shared
catalog now contains 51 routes and 436 illustrations. Android build 35 and
current iPhone/iPad source identify as 0.32.3; physical pairing remains unverified.

The [0.33 output inventory report](docs/output-inventory-report-2026-10-27.md)
adds **Sound → Output inventory → Refresh outputs → Review output report**
on Android. Review shows a dated, bounded metadata snapshot; Share sends exactly
that text through the native Sharesheet. Live rows still clear on leaving or a
change notice. The report retains unknown route/format and unverified physical
output, and contains no audio-device names/addresses/IDs, audio, photos or TV
information. Android is build 36; iPhone source stays 0.32.3. This supplies partial
phone observations for N2b inventory and does not implement playback.

The [0.34 two-phone setup worksheet](docs/test-setup-worksheet-2026-10-27.md)
adds **Sound → Test setup → Review setup report** to Android and iPhone/iPad
source. Record six optional, brief technical notes about the phones, intended
output and observer arrangement. Blanks remain Unknown. Review freezes the
text before a separate native Share action. Back keeps the draft; Clear,
closing and a new process discard it. This is partial, unverified intake for
N2b and does not authorize playback or recording. Android is build 37; iPhone
source is 0.34.0. Native test results and installer identity belong to its PR;
signed iPhone delivery and physical output qualification remain pending.

The [0.35 combined setup report](docs/setup-output-report-2026-10-27.md)
adds **Add setup notes** to Android's reviewed output inventory. The worksheet
includes that exact dated output snapshot with optional notes in one reviewed
share. Remove output details and Clear notes are separate choices. Closing or
a new process discards both. Android is build 38; iPhone source remains 0.34.0.
This remains partial, unverified N2b intake before a playback adapter. Actual
test results and installer identity belong to its draft PR.

The [internal TestFlight preparation](docs/testflight-beta-preparation.md)
automates checks on an exact reviewed source revision and provides a manually
requested signing/upload lane after Apple account and signing setup. It does
not invite testers or certify physical protection.

The [0.32.1 Samsung setup repair](docs/samsung-setup-review-2026-10-25.md)
starts one SmartThings guide, offers the PIN path when the TV asks for it, and
checks the existing SmartThings TV in the phone part. Back and resume preserve
the selected approval step. Guide completion does not verify a connection.

## Current a-Shell baseline

The source baseline comes from the verified a-Shell exports supplied on September 24, 2026: 423 original paths plus 18 supplement paths. Every exported file is accounted for in the [synchronization manifest](docs/a-shell-sync-manifest.json): 431 retain their exact bytes, nine have documented maintenance fixes, and one unused corrupt Python module was retired. This records the supplied snapshots; later edits on the phone require another synchronization.

Older GitHub-only modules and tests, 20 stale root files, and machine-local artifacts were retired from the active tree. The [legacy inventory](docs/retired-legacy-paths.md) records the source and test retirements, and Git history preserves prior versions. [Hosted CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml) checks the full Python suite and both native contracts. The verified baseline passed **1,625 Python tests, Swift, and Android**. See [restoration status](docs/repository-restoration.md) and the [audit matrix](docs/audit_matrix.md) for provenance and evidence limits.

## Current reference implementations

Development continues from that restored baseline. N1 added eight native-work and eight context-invalidation cases (1,641 Python tests at its checkpoint). The user's separate a-Shell checkout at `b0ca6cf` passed **1,685 Python tests** with one external dateutil warning and a clean `lg2 status -s`; Python did not execute the native app shells. The N2a compiled lab has **45 separate C cases**: six owner, five callback, four child, six acknowledgement, five retirement, nine retry/invalidation, six fixture PCM, and four typed-trace cases. The PCM profile exhaustively checks its bounded signed-16 arithmetic; the trace records typed backend outcomes and call ordering. These are scripted software fixtures, not sound processing or evidence of physical playback. Local normal and AddressSanitizer/UBSan runs passed; hosted and phone results for each newer revision must be checked separately. See the [development roadmap](docs/development-roadmap.md) for verification evidence, native build inventory, and next gates.

The merged reference increment adds **read-only session evidence projections** for coverage snapshots, unknown gaps, capability prerequisites, and scoped change wording. A separate owned-player authored-track finder distinguishes availability, player selection, and presentation callbacks while preserving manual choice priority. Python, Swift and Kotlin consume a shared 21-case synthetic status/capability fixture after the new REFERENCE_ONLY vector. The privacy-side timeline is bounded, redacted for export, and deliberately does not report uninterrupted coverage durations. P1 adds buildable read-only iOS and Android simulation shells that start with no observation. Both shells may display a foreground-only OS event hint, which cannot change coverage from Unknown; these are not installed or qualified real-device apps. See the [session evidence contract](docs/session-evidence-reference.md), [prototype limits](docs/read-only-native-prototypes.md), and [installed-device trial protocol](docs/p1-installed-device-trial.md).

The [read-only UI smoke workflow](.github/workflows/read-only-ui-smoke.yml) now launches the iOS app in an iPhone Simulator using XCUITest and the Android APK in an API 35 emulator. [The PR #22 run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36288934014) passed both jobs, asserting visible simulation, unknown coverage, no output observation, unknown prerequisites, and unavailable handoff. The first iOS run exposed a missing app bundle version; it was fixed before the passing rerun. These are simulator UI observations, not real-device installation, accessibility qualification, or physical audio evidence.

The [iPhone device preflight](.github/workflows/iphoneos-device-preflight.yml) is a separate, unsigned arm64 archive check for the read-only shell; it does not make an installable build. The [P1 trial protocol](docs/p1-installed-device-trial.md) accepts an independently recorded TestFlight install with signed build provenance while keeping protection and physical-output claims unqualified.

The native shells include Options, Advanced options, contextual tutorials,
and persistent **Jump to** / **Help & tutorials** buttons. An expandable readiness
checklist explains all six unknown prerequisites without enabling controls.
The [native app audit](docs/native-app-audit-2026-09-27.md) records accessibility,
navigation and read-only contract improvements, their tests, and the staged
research required for future background and physical-output features.

The native interface now groups these features into **Home, Sound, Devices,
Insights and Settings**, with a shared Midnight/Daylight/System theme. Help
and section navigation remain available on every page. Insights has an honest
empty state and an optional, explicitly synthetic example with text values;
planned features open prerequisite explanations. Appearance, first-visit guide
dismissal and numbered setup bookmarks are saved locally. Voice check and TV
photo setup are optional foreground input tools; their results cannot authorize
device control. See the [interface research and design](docs/interface-design-research-2026-09-28.md).

The native launch experience uses the owner's white Audio Bodyguard artwork,
including its purple/black rose and Silicon Workforce credit. iOS displays it
from a static launch storyboard; Android transitions from its required system
splash to the full artwork during the first frame. There is no fixed loading
delay. See the [launch-artwork evidence and test plan](docs/launch-artwork-research-2026-09-28.md).

The merged increment passed **1,678 Python tests locally** with the generated feedback contracts current and the 45 scripted C lab cases passing both normal and sanitizer runs. [Hosted CI for the merged main revision](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36276387177) passed Python, Swift, Android and the scripted C lab. The user then fast-forwarded the a-Shell checkout to `0997133` and reported **1,678 Python tests passed in 5.90 seconds**, `NATIVE_CONTRACTS_CURRENT` and a clean status. The warning is the existing external dateutil deprecation. Neither run qualifies physical output.

The supervisor generation consistency fix passed **1,679 Python tests locally** and all four hosted main CI jobs. The in-process reference event producer captures software status separately from publication, exposes known lost samples through sequence gaps, and projects any software ACTIVE status as unknown physical state. Six new checks brought the local Python suite to **1,685 passed**; [all four hosted main CI jobs](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36278169070) passed, and the user subsequently ran the same count on the phone at `8e4a5c1`. This producer is neither a native event source nor physical qualification.

| Area | Source and behavior |
| --- | --- |
| Controller authority | `src/control` contains controller leases, signed commands, fencing, intent admission, and reauthorization contracts. |
| Protection state | The protection supervisor, evidence source, dispatcher, and platform event adapter preserve truthful paused, degraded, recovery, and unknown states. |
| Session explanation | Read-only session snapshots, a bounded reference producer, capability cards, scoped change wording and authored-track reports retain uncertainty and do not grant actuation. |
| Physical truth and finality | `src/device_fabric` contains world-state and physical contracts, execution journals, handoff gates, replay handling, and endpoint finality assertions. |
| Verified media state | Media profiles, undo candidates, and verified settings bind to matching observation and verification evidence. |
| Selection and resources | `src/edge` and `src/interface` provide resource contracts, TV selection, user feedback, and reference interfaces. |
| Extension admission | `src/extensions` validates and normalizes proposal-only extensions through deterministic admission checks. |
| Native contracts | Swift and Kotlin models consume shared feedback fixtures, 18 synthetic endpoint-boundary vectors, and 21 read-only session-view vectors. |
| Native work simulation | A bounded test-only endpoint tracks work across one handoff and rejects stale runtime, route, successor, protection, or expired synthetic submission context; it cannot grant production readiness. |
| Owned-output lab | A single-thread C11 owner preserves the unsent suffix across zero/EAGAIN returns and blocks retries after a hold or fault. Callback and child references retain metadata; acknowledgements match the exact cut within a fixed deadline; a two-slot retirement pool refuses new incarnations at capacity. Cleanup and slot reuse preserve physical uncertainty. The scripted lab has no physical output or production authority. |

Rejection paths must fail before physical actuation; the tests check `adapter.calls == 0` where applicable. Physical success requires observed postconditions and matching lineage. New platform callbacks or inference results do not establish that protection is active.

## Development checks

Run commands from the repository root. For a desktop or CI environment, the Python CI job uses Python 3.13:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tools/generate_native_feedback_contracts.py --check
python tools/generate_interface_content.py --check
python tools/generate_tutorial_content.py --check
python tools/generate_setup_guides.py --check
python tools/export_picture_guide.py --check
PYTHONPATH=. python -m pytest -q
```

To continue from GitHub while preserving the older phone checkout, first follow
[the separate-folder a-Shell instructions](docs/a-shell-continuation.md).
In the existing a-Shell environment, the corresponding checks are:

```sh
python3 tools/generate_native_feedback_contracts.py --check
PYTHONPATH=. python3 -m pytest -q --tb=short
```

The test configuration includes both `src` and `tests`. Do not restrict collection or remove a failing safety test to make a restoration pass. The restored checkout passed the full Python suite on Linux/Python 3.12; hosted CI independently passed it on Python 3.13.

Native contract checks and app prototype builds use:

```sh
swift test --package-path native/ios
xcodebuild -project native/ios-app/AQSSReadOnly.xcodeproj -scheme AQSSReadOnly -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
gradle -p native/android testDebugUnitTest :app:assembleDebug
```

The Android job uses Java 17, Gradle 8.13 and the API 36 SDK required by `native/android/build.gradle.kts`. The Swift jobs run on macOS with Xcode. These commands do not measure physical output on a phone or audio device.

The [owned-output lab](native/lab/owned_output/README.md) uses a C11 compiler and a POSIX shell on the build host:

```sh
sh native/lab/owned_output/run_tests.sh
AQSS_LAB_SANITIZE=1 sh native/lab/owned_output/run_tests.sh
```

The second command requires AddressSanitizer and UBSan support. A separate CI job runs both commands. These cases are not collected by pytest or run by the phone's Python command.

## Project map

| Location | Purpose |
| --- | --- |
| `src/control` | Controller authority, intent validation, protection evidence, and bridge admission |
| `src/device_fabric` | Fencing, endpoint journals, transaction finality, and physical verification contracts |
| `src/inference`, `src/policy`, `src/voice` | Inference and policy reference implementations |
| `src/edge`, `src/interface` | Resource handling, TV selection, and feedback adapters |
| `src/extensions` | Extension proposals and admission checks |
| `audio_engine`, `acoustic_engine.py`, `signal_router.py`, `state_logger.py` | Restored reference pipeline dependencies from the phone supplement |
| `config` | Reference configuration used by existing code and tests |
| `docs` | Source provenance, file verification, retirement inventory, and evidence limits |
| `tests`, tests within `src` | Python regression and invariant tests |
| `contracts` | Shared JSON fixtures and documented contract boundaries |
| `native/ios`, `native/android` | Feedback models, synthetic fixture conformance tests and an Android read-only app module |
| `native/ios-app` | iOS SwiftUI read-only simulation app target; no audio path or signed-device install |
| `native/lab/owned_output` | C11 owner, callback/child lifetime, scoped acknowledgement, and metadata-retirement harness with scripted backends |
| `tools/generate_native_feedback_contracts.py` | Generator for the Swift and Kotlin feedback models |

Change generated feedback models through their contract and generator, then check with `--check`. The [endpoint native boundary fixture](contracts/endpoint_native_boundary_v1.md) has capability `test_only_trace_conformance`; it cannot be used as a retirement certificate or execution authorization.

## Evidence and local data

[The audit matrix](docs/audit_matrix.md) distinguishes reported phone results, reproduced software checks, and outstanding physical validation. Older benchmark and research reports remain in Git history as historical records, not qualification evidence for this baseline.

Keep credentials, local databases, caches, and phone recovery copies out of commits. Previously tracked machine-local artifacts have been removed from the current source tree. This does not erase them from older Git history.
