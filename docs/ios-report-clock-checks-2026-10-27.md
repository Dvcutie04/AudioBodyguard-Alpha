# iPhone/iPad report clock boundary checks

October 27, 2026. This adds regression coverage without changing application
code or versions. iPhone/iPad source remains 0.38.0/build 1; Android's delivered
Live Test remains 0.37/build 40.

The worksheet and combined-report clock paths were checked at the Unix epoch,
one millisecond, 999 milliseconds, the next second, and the accepted upper date
limit with both .001 and .999 fractions. The current formatter retained the
expected text in the CI toolchain. A separate combined-report case checks that
the last supported notes-review millisecond remains distinct from an original
snapshot at the beginning of that second, preserving the exact source suffix.

These tests passed before any formatting change. The existing implementation
was retained; this is a verified boundary check, not a new clock repair or a
claim that all OS/toolchain combinations have been measured. Two additional
Foundation cases bring that suite to 121 tests. Exact source-bound receipts
belong to the draft PR.

The supplied dates remain untrusted phone-clock labels. They do not establish
correct wall time, cross-phone synchronization, monotonic timing or latency.
The source snapshot and notes date remain separate. No audio behavior, native
API, permission, protection gate or installer changes. Actual device testing,
physical qualification and signed iPhone installation remain pending.
