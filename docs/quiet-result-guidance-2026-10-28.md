# Android 0.39 quiet-check result guidance

October 28, 2026. The owner requested starting 0.39 while testing 0.38.
Candidate Android is `0.39-quiet-guidance-live-input`, build 42. iPhone/iPad
application source remains 0.38.0/build 1; its independent playback and signing
requirements remain pending.

## A useful next step after a check

The prior quiet screen used a generic report prompt for user stops, focus loss,
timing faults, attempt exhaustion, write/result/backend failures and worker
interruption. The new pure presentation model maps every existing ending reason
to a bounded explanation and an explicit next step. It distinguishes an
output-change notice from a verified route change and control-clock problems
from the phone's calendar date. A busy result asks the owner to wait for the
other tool to finish closing before choosing another Start.

Unresolved cleanup takes precedence over every ending reason, including a
previously completed check. A failed-cleanup flag, quarantine, unreported call
or current process block keeps Start disabled. When a report exists, the message
asks the owner to review or save it **before** force-stopping the app, because
the report is temporary. An empty blocked screen does not offer a report that
does not exist. Opening a blocked screen does not start a worker.

A retained check that has not completed stays **Closing quiet check…** after
Activity recreation, with Start and Review disabled until completion is
observed. A completed historical report remains the same immutable snapshot
after later process quarantine; the screen does not rewrite its original run
to pretend that it observed another owner's cleanup failure.

The presentation's Start flag is a UI control, not native admission or output
authority. The existing worker and process exclusion gate still enforce actual
resource admission. Only a new explicit Start can request work. No resume,
focus gain, report review, callback or guidance message restarts a check.

## Verification and evidence scope

Eight new model cases cover all ending reasons, distinct interruption/failure
guidance, clock wording, cleanup precedence across every reason and uncertainty
flag, preserving report access, missing-result handling and absence of physical
success claims. Their inputs are synthetic and open no native resource.

Tests-first source `15fba3b919ede7e265a09d0e22c289951d6f8775` precedes the model
and UI implementation. Its core Android compile fails because
`QuietOutputGuidance` is not yet defined in Android job `123105544758` of
[run 40770295581](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40770295581).
The focused native observer built successfully, then failed on the actual busy
screen's missing wait-for-cleanup instruction in job `123105355438` of
[run 40770295574](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40770295574).
Those two receipts cover the missing model and the baseline UI behavior;
they do not claim isolated native failures for every ending reason.

The final native lane retains actual busy admission and one emulator framework
check, then inspects exact report/share/notes retention. Two observer-only
fixtures extend presentation coverage: toggling the already completed capture's
completion flag checks a retained closing screen without introducing another
real worker; a synthetic exclusion lease with failed cleanup checks sticky
process quarantine, exact retained report/share and empty blocked entry. Neither is an
observed delayed Android call or real native cleanup failure. The observer does
not reset quarantine inside the process; the next font-scale run force-stops
the target first. Normal and enlarged-font screenshots and exact status text
are retained for inspection.

The full regression must inspect the same APK that is delivered, including
unit tests, lint, prior input/photo/navigation behavior, quiet checks, exact
sharing and private intake. Source/run/build identity, original artwork,
signature verification and exclusion of observer/share-fixture code remain
required. Final runs, counts and installer hashes belong to the draft PR and
delivery report, rather than being inferred from a queued run.

The first implementation's core and focused checks passed. Full run
`40771307515` passed the existing app regression, then its new blocked-share
observer clicked immediately after opening the report, before waiting for that
window's focus. It saw no share intent; the product intentionally ignores an
unfocused click. The observer now waits up to five seconds for the showing
report window to have focus, keeping the exact-one-intent and byte-equality
assertions. This corrects the test interaction, not the application's focus
guard, sharing implementation or audio worker. Final delivery requires the
subsequent complete APK run.

The focus-corrected focused run `40773895314` subsequently failed in the
older configuration-retention observer before reaching the new blocked-share
interaction. That observer accepted the first monitor result after requesting
recreation. A separate observer-only continuation waits for the old window to
regain focus and then observes a distinct recreated Activity within a bounded
ten-second test window, ignoring a late resume event for the old instance.
The distinct-instance, retained-capture and exact-report assertions remain.
This changes only the observer/workflow and this note; Android application,
core model, resources, dependencies and versions remain identical. The APK's
full run is allowed to finish independently. Delivery records must distinguish
the APK source from any later observer source and check their application trees
for equality rather than silently treating different revisions as one.

No quiet-check source samples, gain, budget, retry policy, trace, native API,
permission, resource ownership or cleanup sequence changes. The original
report schema and raw ending reason remain available. The work implements
already reviewed state/reporting requirements; it is not new backend research.
Actual phone behavior, physical output/silence/latency/protection, N2b–N5 and
signed iPhone distribution remain unqualified.
