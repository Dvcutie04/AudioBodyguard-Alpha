# Audio Bodyguard Alpha

Audio Bodyguard Alpha is the development repository for AQSS-36-OMEGA. It contains Python reference implementations and tests for acoustic inference, controller authority, protected device handoff, and physical verification, plus Swift and Kotlin feedback contracts and a separate C11 scripted output lab.

**INFERENCE IS NOT REALITY. AI proposes. Policy authorizes. Physical Commit verifies.**

The alpha includes simulations, mocks, and synthetic conformance tests. Passing software tests do not establish physical output containment, acoustic safety, or production readiness. The endpoint handoff barrier and production execution guard intentionally remain closed.

## Current a-Shell baseline

The source baseline comes from the verified a-Shell exports supplied on September 24, 2026: 423 original paths plus 18 supplement paths. Every exported file is accounted for in the [synchronization manifest](docs/a-shell-sync-manifest.json): 431 retain their exact bytes, nine have documented maintenance fixes, and one unused corrupt Python module was retired. This records the supplied snapshots; later edits on the phone require another synchronization.

Older GitHub-only modules and tests, 20 stale root files, and machine-local artifacts were retired from the active tree. The [legacy inventory](docs/retired-legacy-paths.md) records the source and test retirements, and Git history preserves prior versions. [Hosted CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml) checks the full Python suite and both native contracts. The verified baseline passed **1,625 Python tests, Swift, and Android**. See [restoration status](docs/repository-restoration.md) and the [audit matrix](docs/audit_matrix.md) for provenance and evidence limits.

## Current reference implementations

Development continues from that restored baseline. N1 adds eight native-work and eight context-invalidation cases, bringing the Python suite to **1,641 tests**. The first N2a compiled lab adds **six separate C cases** for partial writes, hold ordering, return accounting, and bounded traces. See the [development roadmap](docs/development-roadmap.md) for verification evidence, native build inventory, and next gates.

| Area | Source and behavior |
| --- | --- |
| Controller authority | `src/control` contains controller leases, signed commands, fencing, intent admission, and reauthorization contracts. |
| Protection state | The protection supervisor, evidence source, dispatcher, and platform event adapter preserve truthful paused, degraded, recovery, and unknown states. |
| Physical truth and finality | `src/device_fabric` contains world-state and physical contracts, execution journals, handoff gates, replay handling, and endpoint finality assertions. |
| Verified media state | Media profiles, undo candidates, and verified settings bind to matching observation and verification evidence. |
| Selection and resources | `src/edge` and `src/interface` provide resource contracts, TV selection, user feedback, and reference interfaces. |
| Extension admission | `src/extensions` validates and normalizes proposal-only extensions through deterministic admission checks. |
| Native contracts | Swift and Kotlin models consume shared feedback fixtures and 18 synthetic endpoint-boundary vectors. |
| Native work simulation | A bounded test-only endpoint tracks work across one handoff and rejects stale runtime, route, successor, protection, or expired synthetic submission context; it cannot grant production readiness. |
| Owned-output lab | A single-thread C11 owner retains an accepted prefix and blocks suffix retries after admission closes; its scripted backend has no physical output or production authority. |

Rejection paths must fail before physical actuation; the tests check `adapter.calls == 0` where applicable. Physical success requires observed postconditions and matching lineage. New platform callbacks or inference results do not establish that protection is active.

## Development checks

Run commands from the repository root. For a desktop or CI environment, the Python CI job uses Python 3.13:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tools/generate_native_feedback_contracts.py --check
PYTHONPATH=. python -m pytest -q
```

In the existing a-Shell environment, the corresponding commands are:

```sh
python3 tools/generate_native_feedback_contracts.py --check
PYTHONPATH=. python3 -m pytest -q --tb=short
```

The test configuration includes both `src` and `tests`. Do not restrict collection or remove a failing safety test to make a restoration pass. The restored checkout passed the full Python suite on Linux/Python 3.12; hosted CI independently passed it on Python 3.13.

Native contract checks use the existing Swift package and Android library:

```sh
swift test --package-path native/ios
gradle -p native/android testDebugUnitTest
```

The Android job uses Java 17 and Gradle 8.10.2 with the SDK required by `native/android/build.gradle.kts`. The Swift job runs on macOS. Neither command measures physical output on a phone or audio device.

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
| `native/ios`, `native/android` | Feedback models and synthetic fixture conformance tests |
| `native/lab/owned_output` | C11 partial-transfer and hold-accounting harness with a scripted backend |
| `tools/generate_native_feedback_contracts.py` | Generator for the Swift and Kotlin feedback models |

Change generated feedback models through their contract and generator, then check with `--check`. The [endpoint native boundary fixture](contracts/endpoint_native_boundary_v1.md) has capability `test_only_trace_conformance`; it cannot be used as a retirement certificate or execution authorization.

## Evidence and local data

[The audit matrix](docs/audit_matrix.md) distinguishes reported phone results, reproduced software checks, and outstanding physical validation. Older benchmark and research reports remain in Git history as historical records, not qualification evidence for this baseline.

Keep credentials, local databases, caches, and phone recovery copies out of commits. Previously tracked machine-local artifacts have been removed from the current source tree. This does not erase them from older Git history.
