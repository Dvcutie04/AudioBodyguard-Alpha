# Repository restoration status

Status: work in progress, not ready to merge. No runtime permission or physical qualification is granted by this restoration.

## Source provenance

| Input | Evidence |
| --- | --- |
| GitHub base | `Dvcutie04/AudioBodyguard-Alpha`, commit `bb94b174e11ddbe09e11c05598f80aa9e7161be0` |
| Phone branch reported by the owner | `aqss36-native-feedback-v1` |
| Phone test output reported by the owner | 1,625 passed, one dependency deprecation warning, Python 3.13 on iOS |
| Uploaded archive | `AQSS_CI_REVIEW_1625.zip`, 475,077 bytes, 423 source files |
| Archive SHA-256 | `38c25ea2e5c1ce761b3623f5266c4758e9c721160fe4da7c5230eb07eba768f7` |
| Import verification | ZIP integrity, safe paths, and every source file size and SHA-256 matched the archive manifest |

The archive's declared scope is source review, incomplete until dependencies are checked. It is not a full repository backup or a commit of the phone checkout. Its source files have been overlaid onto this isolated branch. The phone's code and tests are unchanged in the import; `.gitignore` and CI configuration are separately updated for repository maintenance.

## Transfer gaps

The export omitted the root `audio_engine` package and `state_logger.py`. The older GitHub `state_logger.py` also imports `acoustic_engine.py` and `signal_router.py`; the phone copies of these modules must be checked. The export excluded `src/device_fabric/quarantine`, including `manager_legacy.py`, whose presence an existing safety test requires.

The initial exported snapshot could not collect 13 test modules because of the missing imports. A diagnostic run using the older GitHub root modules collected the same 1,625 tests and returned **1,615 passed, 10 failed**. Nine failures are `audio_engine.DecisionEnvelope` interface mismatches in the pipeline integration tests. One is the missing quarantine file. This demonstrates why substituting the old dependencies cannot reproduce the reported phone result.

The diagnostic did not alter tests or insert a placeholder quarantine file. It is not a full validation of this branch.

## Prepared changes

- Import the verified 423-file source snapshot, including its 18-vector synthetic endpoint contract and Swift/Kotlin fixture readers.
- Remove 231 tracked machine-local, backup, recovery-conflict, credential, or shell-fragment artifacts from the proposed tree. Original history is retained.
- Replace the broad `*token*` ignore pattern with specific credential and local-state patterns, and ignore native build output and review ZIPs.
- Restore Python 3.13, Swift, and Android conformance jobs from the phone workflow. Add read-only workflow permissions, bounded job durations, pip caching, branch/manual triggers, and cancellation of superseded runs.
- Record 74 older GitHub-only source, test, and backup paths absent from the current phone export, and retire them from the active tree. The [complete path inventory](retired-legacy-paths.md) points back to the base commit, where their contents remain available.
- Document evidence limits and remaining restoration work.

The retired paths include older physical transaction contracts and a `tests/conftest.py` fixture with an incompatible contract constructor. No phone source or test imports a retired module. Retirement removes incompatible historical code from the active test suite; it does not claim that every old invariant already has an equivalent current test.

## Required next steps

1. Receive and verify the omitted phone dependency and quarantine files.
2. Run the complete Python suite and generator drift check in the restored checkout.
3. Compile and run Swift and Android conformance tests in their CI jobs.
4. Review any historical invariant worth migrating as a separate current-contract test, then review the final diff and evidence before merging.

The public base commit includes an SSH private key. Its removal from this proposed tree does not revoke it or remove earlier copies. The owner must revoke or replace the corresponding credential wherever it is authorized. No credential contents are reproduced here.
