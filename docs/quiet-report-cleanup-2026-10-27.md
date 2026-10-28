# Android quiet-report cleanup observations and native intake

October 27, 2026. Candidate Android 0.38-quiet-report-live-input/build 41
corrects a report label without changing the quiet-check worker. iPhone/iPad
application source remains 0.38.0/build 1, with 121 Foundation regression cases.
The exact delivered installer and source-bound checks belong to the draft PR.

## Cleanup that ran versus admission that was denied

A pre-stopped, inactive or busy check can return without constructing the
backend or entering a cleanup operation. The earlier report displayed
`Resource cleanup calls: Returned` whenever its cleanup-success flag was true,
including those no-work results. That flag was suitable for resource exclusion
but did not by itself establish that a cleanup call had entered and returned.

The report now preserves these distinctions:

| Report value | Meaning within this run |
| --- | --- |
| `Not entered` | No cleanup operation entered, and this run has no unresolved call accounting |
| `Returned` | Cleanup entered and the worker reported successful cleanup/accounting |
| `Unresolved` | Cleanup failed or entered-call accounting remains incomplete |

An additional `Call accounting incomplete` field exposes the existing result's
uncertainty. An earlier cleanup failure stays unresolved even if a later release
call returns. Busy admission during another owner's quarantine still reports
no cleanup entered by this run; the separate process-quarantine field remains
true. Neither a return nor a successful exclusion release proves physical
retirement, silence or protection.

The source samples, gain request, retries, time budget, stop cut, ownership,
callback retirement, cleanup sequence and sticky quarantine are unchanged.
Four added model/report cases exercise denied admission, returned cleanup,
failure followed by later returns, and an unreported entered call. Native
observers also open the actual denied-admission report before a fresh framework
check, verify its zero samples/attempts and retain its exact text and screenshot
at normal and enlarged fonts.

## Intake of actual native shared text

The [native intake verifier](../tools/verify_native_setup_intake.py) connects the
[private intake tool](mobile-setup-intake-2026-10-27.md) to Android's actual
combined quiet-report preview and iPhone/iPad's actual copied combined report.
Each native workflow supplies its expected installed labels and declared source
revision. The verifier runs the engineering CLI, checks exact source bytes/hash,
then runs the existing N2b inventory checker against the resulting local files.

The expected result remains `PHONE_REPORT_RECORDED_UNVERIFIED` and
`INCOMPLETE_INVENTORY`. All eight row statuses remain unknown; qualification
and production flags stay false, authentication stays unestablished and the
observation date stays null. The CI receipts contain explicit synthetic test
notes, not owner observations. A copied text or matching label does not prove
hardware state, trusted source execution or recipient delivery.

The full Android regression must inspect the same APK that is delivered.
Focused/native checks cover the denied report, normal quiet stream/report,
exact sharing, notes handoff, recreation, Clear/remove, parent return, font
scales and source byte retention. iPhone/iPad checks retain review/Copy,
worksheet lifecycle and largest-text coverage while exercising intake too.
The original artwork and exclusion of observer/fixture code remain required.

No new platform API, microphone permission, recording, route selection or
physical trial is added. The actual phone report, N2b–N5 qualification and
signed iPhone distribution remain pending.
