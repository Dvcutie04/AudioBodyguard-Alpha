# AQSS validation evidence

This matrix records evidence available during repository restoration. Software conformance and physical qualification are separate requirements.

| Area | Evidence available | Limit or remaining check |
| --- | --- | --- |
| Phone Python checkout | Owner-provided output: 1,625 passed on Python 3.13/iOS | Physical output remains unqualified |
| Uploaded source and supplement | 423 original and 18 supplemental file hashes verified; 17 usable supplement files imported | One preexisting nonparseable, unimported module retired with history preserved |
| Every exported source path | [Synchronization manifest](a-shell-sync-manifest.json) accounts for 441 paths: 431 exact, nine maintained, one retired | Describes the supplied a-Shell exports, not later edits on the phone |
| Endpoint and fencing regression tests | 47 tests reproduced on Python 3.12/Linux | Software reference implementations and fixtures |
| Full restored Python suite | 1,625 passed on local Python 3.12/Linux and hosted Python 3.13/Linux; all active source/test files parse | Software tests do not qualify physical output |
| Diagnostic with older GitHub dependencies | 1,615 passed, 10 failed before supplement | Older interface mismatches resolved with exact phone files |
| Publication-failure test clocks | Two failures reproduced with a 46-second default clock; both passed after explicit synthetic clock injection, followed by all 1,625 tests locally | Existing monotonic and fail-closed assertions retained |
| Generated feedback models | Generator check reported `NATIVE_CONTRACTS_CURRENT` locally and in hosted CI | Contract generation is not a production runtime proof |
| Swift contract conformance | Hosted macOS Swift package compilation and tests passed | Synthetic fixtures do not verify physical output |
| Android contract conformance | Hosted Android Gradle library compilation and tests passed | Synthetic fixtures do not verify physical output |
| Endpoint retirement and physical output | Synthetic test-only trace contract exists | No qualified native output boundary or acoustic observation established |
| Production execution | Endpoint handoff barrier and bridge execution guard stay closed | Software test results do not authorize removing these guards |

All three hosted jobs passed after source cleanup in [Actions run 36067699270](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36067699270); use the [workflow runs](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml) to verify the latest revision. Historical benchmark claims in older reports have not been revalidated in this restoration. A mock adapter or a test named “hardware-in-the-loop” is not evidence that a physical device was observed. See [restoration status](repository-restoration.md) for source provenance and remaining work.
