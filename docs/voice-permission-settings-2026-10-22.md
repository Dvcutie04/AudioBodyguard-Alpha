# Voice-check permission recovery — October 22, 2026

Version 0.16 extends the dedicated meter's permission guidance to Voice check.
The increment covers Android microphone access and the distinct iPhone
microphone and Speech Recognition permissions. It adds no device-control
authority, automatic listening or claim of speech-model availability.

## Research and selected design

| Primary source | Design consequence |
| --- | --- |
| [Android runtime permissions](https://developer.android.com/training/permissions/requesting) and [Activity permission callbacks](https://developer.android.com/reference/android/app/Activity#onRequestPermissionsResult(int,java.lang.String[],int[])) | Keep the existing user action and speech-availability gate. Read actual permission on callback and return; empty/canceled results never authorize capture. |
| [Android app-specific Settings](https://developer.android.com/reference/android/provider/Settings#ACTION_APPLICATION_DETAILS_SETTINGS) | Use the public package-specific details action, with a manual fallback if launch fails. |
| [Apple speech authorization](https://developer.apple.com/documentation/speech/asking-permission-to-use-speech-recognition), [current authorization](https://developer.apple.com/documentation/speech/sfspeechrecognizer/authorizationstatus()), and [restricted status](https://developer.apple.com/documentation/speech/sfspeechrecognizerauthorizationstatus/restricted) | Microphone consent and speech consent are distinct. Requery their current values, keep microphone denial first, and distinguish user-denied speech from a device restriction. A restriction must not promise a user-changeable Settings switch. |
| [Apple app-specific Settings URL](https://developer.apple.com/documentation/uikit/uiapplication/opensettingsurlstring) | Open only the public app-specific URL, with an unsuccessful-opening fallback. |

Repeated permission prompts on resume would add interruptions without a new
user action. A Settings link alone would leave stale permission guidance.
The selected combination is an explicit Settings action, an event-driven
native permission query on return, and the existing explicit Start,
foreground and microphone ownership gates.

Guidance begins at a permission attempt and ends at a granted explicit Start.
The shortcut appears only for denied access, and stays hidden during
ordinary idle/listening states and blocking cleanup failure. iPhone guidance
identifies microphone denial, speech denial, restricted speech, speech consent
not yet chosen, or permissions granted. A microphone grant never requests
speech or starts recognition by itself. Neither permission request completion
nor Settings return acquires a microphone lease or starts an input run.

Swift Settings completions are bound to an attempt identity. A newer Start,
Stop, Clear or permission refresh invalidates an older completion. Permission
callbacks keep the existing request identity and read the actual OS status.
Cleanup failure remains blocking. Android retains its availability check
before requesting microphone access; unsupported recognition stays unavailable
and has no cloud fallback.

Speech authorization can also be denied on an unsupported device. Guidance
therefore asks users to check Settings; granting access does not establish
recognizer/model/language availability. The existing availability check still
runs at the next explicit Start.

There is no new dependency, permission, polling timer, background task,
network request, audio retention or stored preference. Extra work consists of
bounded state and permission queries during the existing UI events. This is a
design policy; latency, battery and memory on actual phones remain unmeasured.

## Verification contract

Regression checkpoint `73fcc26dcc8a42f86ae4209b77a5e9a56155c503` changes only
native regressions, their CI configuration and screenshot export. Production
app code and version remain 0.15. Each native permission case must first fail
at the missing Voice Settings shortcut after actual denial and idle checks.
Exact red/green observations belong to the draft PR.

The isolated speech case compiled on 0.15, denied the real first Speech
Recognition prompt and confirmed idle input/words. Run `39862137425`, job
`120115217012`, then failed at `Missing voice permission Settings shortcut`;
its thrown sentinel produced a second failure record for the same missing
control. Android run `39862137261`, job `120115215157`, compiled and passed
the earlier meter, photo, camera and voice checks, then denied the real
microphone dialog in the new Voice fixture. It failed at
`Missing tap target: Open app settings` after the idle/empty-word checks.
The iPhone microphone suite in run `39862137425`, job `120115216497`,
passed the five original denied/idle/photo tests and the existing meter
Settings test. Its isolated Voice microphone case then failed at the same
missing shortcut after actual denied-access and idle checks, with the same
thrown sentinel. Granted-input verification was skipped after that expected
failure. These three cases establish the missing behavior before production
code changes; they do not qualify actual handset input or output.

Android's test-only instrumentation starts the real Voice Activity and asks
for its existing microphone permission using `Activity.requestPermissions`.
The external observer denies the actual system dialog, opens actual Settings,
returns while denied, then grants actual permission while Settings is
foreground and returns again. The fixture is necessary because an emulator
may lack the speech model required by the normal user Start path. It injects
no permission callback, recognition service, words or audio samples, and does
not qualify recognizer availability. Both returns must show no live samples,
no recognized words and Start, with no running microphone app-op. The grant
must remove the denied shortcut and show fresh granted guidance. The observer
and fixture must be excluded from the delivered APK.

iPhone microphone recovery runs after the other denied tests and meter
Settings test, with its own native denied precondition. It uses the real
Microphone switch and leaves access granted for the following explicit-input
suite. A separate fresh Simulator job establishes microphone access, denies
the real first Speech Recognition prompt, tests the still-denied return, then
enables the real Speech Recognition switch. Both cases require the actual
app-specific Settings page, idle returns, empty words and no surprise consent
prompt. Tests handle an OS-induced relaunch through the real Exit Home guide
action before reopening Voice check. Switch taps target the trailing toggle
within the identified labeled row; native values are observed before continuing.

Existing sound-meter Settings, voice, photo, camera, deadline, ownership,
cleanup, recap and physical-control contract checks remain required. Native
screenshots and exact source/APK identity are retained as CI evidence. Actual
phone behavior, restriction-policy behavior, speech accuracy, calibrated
acoustics, TV pairing, continuous protection and signed iPhone distribution
remain separate qualification work.
