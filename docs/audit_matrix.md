# AQSS validation evidence

This matrix records evidence available during repository restoration. Software conformance and physical qualification are separate requirements.

| Area | Evidence available | Limit or remaining check |
| --- | --- | --- |
| Phone Python checkout | Owner-provided output: 1,625 passed on Python 3.13/iOS | Exact checkout is not yet fully transferred |
| Uploaded source | 423 file hashes and sizes verified against its manifest | Root dependencies and quarantined legacy source omitted by the export |
| Endpoint and fencing regression tests | 47 tests reproduced on Python 3.12/Linux | Software reference implementations and fixtures |
| Full exported Python suite | Missing imports initially blocked collection | Required phone files must be supplied |
| Diagnostic with older GitHub dependencies | 1,615 passed, 10 failed | Nine interface mismatches and one omitted quarantine file; not a validated restoration |
| Generated feedback models | Generator and shared contract imported | Run drift check against the final restored checkout |
| Swift contract conformance | Package and XCTest fixture readers imported | Compilation and tests pending for this branch |
| Android contract conformance | Gradle library and Kotlin fixture readers imported | Compilation and tests pending for this branch |
| Endpoint retirement and physical output | Synthetic test-only trace contract exists | No qualified native output boundary or acoustic observation established |
| Production execution | Endpoint handoff barrier and bridge execution guard stay closed | Software test results do not authorize removing these guards |

Historical benchmark claims in earlier reports have not been revalidated in this restoration. A mock adapter or a test named “hardware-in-the-loop” is not evidence that a physical device was observed. See [restoration status](repository-restoration.md) for source provenance and remaining work.
