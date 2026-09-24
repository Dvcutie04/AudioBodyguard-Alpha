# Audio Bodyguard Alpha

Audio Bodyguard Alpha is the development repository for AQSS-36-OMEGA. It contains Python reference implementations and tests for acoustic inference, controller authority, protected device handoff, and physical verification, plus Swift and Kotlin feedback contracts.

The alpha includes simulations, mocks, and synthetic conformance tests. Passing software tests do not establish physical output containment, acoustic safety, or production readiness. The endpoint handoff barrier and production execution guard intentionally remain closed.

## Repository restoration

This branch is restoring the newer phone checkout to GitHub. The uploaded source archive has been verified, but several required phone files were omitted from the export. Older GitHub-only modules and tests were retired from the active tree, with [each path recorded](docs/retired-legacy-paths.md) and its contents retained in Git history. Full-suite and native validation are pending. See [restoration status](docs/repository-restoration.md) for evidence and remaining work.

## Development checks

Run commands from the repository root. The Python CI job uses Python 3.13:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tools/generate_native_feedback_contracts.py --check
PYTHONPATH=. python -m pytest -q
```

The test configuration includes both `src` and `tests`. Do not restrict collection or remove a failing safety test to make a restoration pass. These commands are the intended gates; the incomplete restoration currently has the blockers recorded in the status document.

Native contract checks use the existing Swift package and Android library:

```sh
swift test --package-path native/ios
gradle -p native/android testDebugUnitTest
```

The Android job uses Java 17 and Gradle 8.10.2 with the SDK required by `native/android/build.gradle.kts`. The Swift job runs on macOS. Neither command measures physical output on a phone or audio device.

## Project map

| Location | Purpose |
| --- | --- |
| `src/control` | Controller authority, intent validation, protection evidence, and bridge admission |
| `src/device_fabric` | Fencing, endpoint journals, transaction finality, and physical verification contracts |
| `src/inference`, `src/policy`, `src/voice` | Inference and policy reference implementations |
| `src/edge`, `src/interface` | Resource handling, TV selection, and feedback adapters |
| `src/extensions` | Extension proposals and admission checks |
| `tests`, tests within `src` | Python regression and invariant tests |
| `contracts` | Shared JSON fixtures and documented contract boundaries |
| `native/ios`, `native/android` | Feedback models and synthetic fixture conformance tests |
| `tools/generate_native_feedback_contracts.py` | Generator for the Swift and Kotlin feedback models |

Change generated feedback models through their contract and generator, then check with `--check`. The [endpoint native boundary fixture](contracts/endpoint_native_boundary_v1.md) has capability `test_only_trace_conformance`; it cannot be used as a retirement certificate or execution authorization.

## Evidence and local data

[The audit matrix](docs/audit_matrix.md) distinguishes reported phone results, reproduced software checks, and outstanding native or physical validation. Earlier benchmark and research reports are historical records, not qualification evidence for this branch.

Keep credentials, local databases, caches, and phone recovery copies out of commits. The restoration removes previously tracked machine-local artifacts from its proposed tree. This does not erase them from older Git history.
