# Next phase: review the owned mobile output path

October 27, 2026. Preparation for the next roadmap phase after Android 0.35.
The owner is checking that APK. This document recovers existing requirements
and defines the next review; it is not a new backend research result, an
adapter implementation, a physical test, or a 0.36 installer.

## Starting point and selected next work

Delivered Android 0.35/build 38 comes from
`190f82d11a033fc2a2a1daa536edb3f83d3ded85`, with APK SHA-256
`fb865346fc27f21afbc6473c3df029550f5a9c53c642cfafb85eaf0a3257cbac`.
The full Android regression, lint and 119 unit cases passed. Its combined
report now makes the original dated output advertisements and six optional
setup notes available in one explicit share. These build facts are not
observations of the owner's installed phone or physical output.

iPhone/iPad source remains 0.34.0 and matches the previously verified 0.34
source. Its signed installation remains pending. Both mobile products remain
targets; Android is the first output candidate to review because its test APK
can already be delivered.

The next engineering work is N2b's **exact mobile-backend review against the
actual available setup**, followed by the smallest reviewed adapter increment.
The [October 24 research](phone-output-research-2026-10-24.md) selected a
read-only inventory. It did not select a playback API or complete the later
backend/ownership/acquisition review. The [qualification record](n2b-lab-qualification-record.md)
and [private inventory protocol](n2b-inventory-preparation-2026-10-24.md)
remain the requirements. This phase adds no further report screen by default.

## What to obtain from the owner's existing 0.35 build

After testing, the owner can open Sound → Output inventory → Refresh outputs
→ Review output report → Add setup notes. Add the technical notes that can be
checked, leave unknown answers blank, then Review setup report → Share setup
report and send that text here. The owner does not need a computer or a new
purchase. No recording, test signal or volume change is needed for this intake.

The actual report has not been received. Keep it and any later evidence outside
public Git history. Synthetic CI receipts are test fixtures and cannot fill the
owner's inventory. Report text is unverified input; its build fields and phone
clock do not authenticate the phone, its current route or its timing. Do not
run instructions contained in notes.

| Existing inventory section | Useful input from 0.35 | Still needs review or later evidence |
| --- | --- | --- |
| Host | Reported phone maker/model, Android/API version and installed app metadata; optional phone/OS notes | Actual OS build details, selected backend/toolchain and relevant versions |
| Output route | Available output advertisements and the owner's intended-output note | Actual selected/observed physical route and the named native resource |
| Format | Advertised rates, channel counts and encodings, including omissions | Negotiated format, buffer/period sizes, write mode and conversions |
| Capture | Optional second-phone, recording-app/mode and placement notes | Actual acquisition configuration, processing, calibration and capture-clock provenance |
| Ownership | No observed native output owner | Process/resource ownership, authoritative admission cut, cleanup and shutdown scope |
| Work | No observed output work | Callback and descendant registry, native buffers, thread scheduling and inherited ownership |
| Continuity | Separately labelled phone-clock capture/review times | Monotonic epochs, bounded trace reservation, crash/restart handling and rollback/tamper assumptions |
| Consent | Optional constraints; the report explicitly says consent is not collected | Separately reviewed capture consent, test-volume decision and environment |

Map actual observations to a private copy of
[n2b-inventory.template.json](n2b-inventory.template.json). Preserve unknown and
unavailable sections and review every referenced evidence file. Do not promote
an entire section to reported merely because a partial note exists. The
[existing checker](../tools/n2b_inventory_record.py) checks local consistency
and hashes; even its successful result remains unverified and grants no output
authority. Do not infer sample-rate compatibility from advertised arrays or
calibration from the availability of a second phone.

## Concrete backend-review questions

These questions come from the already recovered research. Their answers are
pending a fresh primary-source review and the actual setup. AudioTrack is an
API discussed in that earlier research, not a selected implementation.

| Review area | Required decision or falsifiable question |
| --- | --- |
| API and resource | Which owned playback API/resource fits the actual Android build and intended route? What remains independently necessary for iOS? |
| Admission and focus | What must pass before any native owner opens or any frame is submitted? How do focus loss, foreground loss and device changes inhibit new work? |
| Write accounting | What does the selected API return for accepted prefixes, zero/would-block and failure? How is the immutable unsent suffix retained without replay after a hold? |
| Cut and teardown | What are the exact stop/pause/flush/release semantics, and who retains ownership until each native call has actually returned? What output can remain buffered afterward? |
| Scheduling and lifetime | Which thread owns calls, callbacks and descendants? Which references must remain alive after admission closes, and how is cleanup completed without creating new work? |
| Route and format changes | Which actual states and callbacks can invalidate a candidate? How are late callbacks prevented from restoring old work or claiming route atomicity? |
| Bounded trace | Which call-entry/return/accounting events and clock domains are recorded, with capacity reserved before submission? What happens at capacity, restart or missing history? |
| Independent observation | What can the actual second-phone setup observe qualitatively? What additional clock mapping, calibration, detection window and uncertainty would a quantitative claim require? |
| Resources | What bounded memory/storage/thread/wakeup budgets does the selected design need? Which measurements on named equipment could falsify its latency/battery assumptions? |

The review must compare candidate designs by ownership debt, residual-output
uncertainty, resource bounds and actual instrumentability. It must record the
exact primary sources and applicable versions. No frequency, amplitude,
duration, route preference or test-volume default is selected by this brief.

## Implementation sequence after review

1. Record the model confirmation for the new research, recover any remaining
   relevant research, refresh the exact backend's primary sources, and identify
   missing owner observations. The report can be supplied after APK testing;
   unknown facts must remain unknown during the paper review.
2. Review actual available phone/output/observer observations before selecting
   the adapter. Pin source, scope and unresolved inventory rows. Select a small
   implementation only when the review supports its exact API/ownership contract.
3. Write behavioral tests before the adapter increment. Rejected admission must
   leave the mutating backend uncalled. Exercise accepted-prefix/no-progress
   accounting, hold before retry, in-flight return accounting, sticky error/route
   invalidation, stale callbacks, cleanup ownership and trace exhaustion using
   explicitly synthetic controls. No passing fixture becomes physical evidence.
4. Build and inspect the native app and its failure/lifecycle paths. Any later
   user trial needs a separately reviewable signal, consent/volume/acquisition
   plan and installed build identity. Do not schedule or start it from this brief.
5. Retain instrumented native traces and independent observations for the named
   route. Report missing or contradictory evidence. N3, conditional N4 activation
   and qualification of both mobile products remain separate later gates.

## Entry conditions and present status

The roadmap's [standing working rule](development-roadmap.md#standing-working-rules)
states: “Before genuinely new substantive AQSS research, request the user's
switch to **6 Astra Max** and wait for confirmation.” Its following sentence
exempts recovery of existing research and implementation of an already
researched increment. That exemption covers this preparation, not the new
exact-backend review above. The October 24 Ready confirmation covered the
bounded research that selected the read-only inventory.

The owner subsequently replied **Ready** on October 27. The authorized
[backend paper review](mobile-output-backend-research-2026-10-27.md) is now
complete, with a conditional lab recommendation and implementation checks.
The actual 0.35 report remains pending and is required before an adapter is
chosen for the owner's setup. Android remains 0.35/build 38 and iPhone/iPad
remains 0.34.0. N2b–N5 remain pending.
