# Friends' beta: software preparation and remaining gates

The owner wants friends to use their own phones, Wi-Fi and TVs, without waiting
for the owner's TV. This increment supplies a self-service trial result on both
platforms and prepares an externally eligible iPhone build option. It does not
complete authenticated TV pairing, TV control or qualified audio protection.

## What a friend can test

The five-stage picture setup, TV photo interpretation, phone sound/voice checks,
navigation, large text and permission/recovery paths remain available. Devices
→ Device help now states the beta's actual scope. Only the VIZIO candidate TCP
service check is currently implemented inside Audio Bodyguard. A service reply
is not an authenticated TV identity. Other brands retain their official
companion-app picture guides; completing a guide does not connect this app.

The developer's [current Roku ECP documentation](https://developer.roku.com/dev/docs/external-control-api)
explicitly restricts ECP commands from third-party mobile platforms. Despite
its published diagnostic endpoints, this increment adds no Roku ECP request,
control client or workaround. Treat protocol availability and permission to
ship a consumer integration as separate requirements.

## Reviewed connection result

After a terminal or rejected check, Review test result creates one immutable
historical copy with the installed app version/build, a labelled phone-clock
review time and a fixed outcome. No address, Wi-Fi name, password, TV/device ID,
photo, audio, exception text or user-supplied notes is accepted by the report
model. The entered address and live result are cleared before opening Review.
Share is a separate native chooser action; the app sends nothing automatically.
Back, closing and process restart discard the review. A copy already reviewed
remains historical while the native chooser temporarily backgrounds the app.

The fixed outcomes distinguish rejected input, unavailable Wi-Fi, blocked
admission, an unauthenticated service response, no established response, Stop
and unresolved cleanup. Stop or a failure never becomes successful pairing.
Changing the address or starting a new check withdraws the previous live result.
Review is unavailable while this check is running or closing. The existing
worker ownership, cancellation and late-result guards still govern native work.

This format is a tester description, not signed evidence or an N2b qualification
record. It does not make its phone clock, reported build or sender trustworthy.
The existing private support report remains separate.

## TestFlight build-label repair

The release workflow generates labels such as `10.1`, but two iPhone report
validators and the private intake previously admitted digits only. That could
prevent worksheet/output reports from an actual TestFlight installation even
when Simulator tests using build `1` passed.

[Apple's current CFBundleVersion documentation](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion)
describes one to three period-separated numeric components. Reports and intake
now preserve those labels exactly, without float conversion, zero stripping or
attempt conflation. Report metadata stays bounded to 19 digits per component;
this bound is not a replacement for Apple's submission validation. Android's
integer version-code rule remains separate. Native iPhone source uses build
`1.1` so actual report/share/clipboard tests exercise dotted labels.

## Getting an installer to friends

- Android's separate Live Test APK can be used for personal trials once its
  exact source, signature, package identity and native checks are verified.
  It remains a development test package, not a Play release. An incompatible
  signing key can prevent an in-place update; preserve wanted reports before
  considering removal of an older test app.
- [Apple's internal-testing guidance](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers)
  says an Internal Only upload cannot be assigned to external testers. The
  [external-testing workflow](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers)
  requires a suitable build and review of the first external beta. Processing,
  beta review, tester assignment, invitation and installation are distinct.
- The manual release workflow now has `testing_audience=internal|external`.
  Internal remains the default; external explicitly configures an export that
  is not Internal Only. Its actual export plist is checked against the selected
  audience before upload and recorded in non-secret provenance. This is export
  configuration evidence, not proof of Apple's eligibility or review result.
- Source/tree pinning, all software/native gates, package/signature/profile
  validation, Apple validation/upload acceptance checks and cleanup remain.
  The existing protected GitHub environment is retained. No secret, account,
  compliance answer, tester group, invitation or Apple review submission is
  changed by this source increment. No new release has been dispatched here.

## Verification and next work

New tests cover exact TestFlight build labels, malformed/oversized inputs,
cross-build mismatch, Android integer separation, report bounds and outcome
wording, rejected-input native review without a network attempt, and export
audience mismatches. Actual native results belong to the final published tree.
Current-source iPhone UI checks must include the new review case and the existing
worksheet/output sharing cases with source build `1.1`.

Next: verify and deliver the exact installers, then collect independent friends'
phone/TV observations through explicit review. Authenticated vendor integration
still needs a reviewed certificate/authentication/enrollment design and real
device trials. N2b–N5 output, lifecycle and independent physical measurements
remain required before any audio-control/protection claim. A green simulated
test or service response cannot finish those gates.
