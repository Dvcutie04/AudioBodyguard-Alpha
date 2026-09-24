# AQSS validation evidence

This matrix records evidence available during repository restoration. Software conformance and physical qualification are separate requirements.

| Area | Evidence available | Limit or remaining check |
| --- | --- | --- |
| Phone Python checkout | Owner-provided output: 1,625 passed on Python 3.13/iOS | Physical output remains unqualified |
| Uploaded source and supplement | 423 original and 18 supplemental file hashes verified; 17 usable supplement files imported | One preexisting nonparseable, unimported module retired with history preserved |
| Endpoint and fencing regression tests | 47 tests reproduced on Python 3.12/Linux | Software reference implementations and fixtures |
| Full restored Python suite | 1,625 passed on local Python 3.12/Linux; all source/test files parse | Python 3.13 hosted CI pending |
| Diagnostic with older GitHub dependencies | 1,615 passed, 10 failed before supplement | Older interface mismatches resolved with exact phone files |
| Generated feedback models | Generator check reported `NATIVE_CONTRACTS_CURRENT` | Hosted CI independent check pending |
| Swift contract conformance | Package and XCTest fixture readers imported | Compilation and tests pending for this branch |
| Android contract conformance | Gradle library and Kotlin fixture readers imported | Compilation and tests pending for this branch |
| Endpoint retirement and physical output | Synthetic test-only trace contract exists | No qualified native output boundary or acoustic observation established |
| Production execution | Endpoint handoff barrier and bridge execution guard stay closed | Software test results do not authorize removing these guards |

Historical benchmark claims in earlier reports have not been revalidated in this restoration. A mock adapter or a test named “hardware-in-the-loop” is not evidence that a physical device was observed. See [restoration status](repository-restoration.md) for source provenance and remaining work.
