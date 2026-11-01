# iPhone Voice stop guidance — 0.24

October 23, 2026. This wording increment follows the tested 0.23 candidate.
The iPhone Voice check previously grouped four runtime checks into one guard.
Every failed check displayed “Check permissions,” even when both permission
checks had passed and recognition availability or the audio engine had changed.

## Existing research and source refresh

The [iPhone microphone lifecycle research](ios-microphone-lifecycle-2026-10-20.md)
already covers these checks, explicit Start, callback admission and cleanup.
The existing Apple definitions were refreshed before this edit:

- [Speech authorization](https://developer.apple.com/documentation/speech/sfspeechrecognizer/authorizationstatus()) reports authorization.
- [Recognizer availability](https://developer.apple.com/documentation/speech/sfspeechrecognizer/isavailable) reports current recognition availability, separately from authorization.
- [Engine running state](https://developer.apple.com/documentation/avfaudio/avaudioengine/isrunning) reports whether the app's audio engine is running.

No new platform API, recording backend or recognition subsystem is introduced.
The same four observations are checked in their original short-circuit order.

| First failed existing check | New guidance |
| --- | --- |
| Microphone permission is not granted | Explain unavailable microphone access; check app permissions before another explicit Start. |
| Speech authorization is not authorized | Explain unavailable speech access; check app permissions before another explicit Start. |
| Recognizer is not available | Explain current recognition unavailability; suggest Live sound check for microphone levels. |
| Engine is not running | Explain that voice input stopped; offer another explicit Start. |
| Recognition callback reports failure | Retain a generic stopped explanation and offer another explicit Start. |

Each new message retains the warning that words may be incomplete. A reported
check failure is not a root-cause diagnosis. The app does not infer a denied
permission from service loss, decode undocumented error domains, assume a
missing language model, or claim correct transcription or room silence.

## Behavior and validation scope

The sequential guards have the same admission condition and observation order
as the previous combined guard. Every failed condition still calls the existing
stop operation. Cleanup failure continues to override ordinary status text,
and both microphone tools remain blocked if cleanup fails. Existing result
mailbox closure, input limits, route checks, permission refresh and explicit
Start behavior are retained.

This is a reversible wording change. It uses review of the equivalent ordered
conditions and the existing behavioral regression suites rather than adding a
test that repeats message strings. No behavioral assertion is removed. Native
permission-return tests exercise real OS consent; they do not inject service
errors or establish every unavailable-service message on a physical phone.
Exact final runs, observations and source-bound artifacts are recorded in the
candidate's draft pull request after verification.

Android retains 0.23 input behavior. Both candidate identities advance:
Android code 24 / `0.24-ios-voice-stop-guidance-live-input`, Apple 0.24.0 / build 1.
No automatic retry, new permission, model download, cloud fallback, persistence,
background capture or output authority is introduced. Handset speech accuracy,
signed iPhone delivery, continuous protection, TV control and N2b–N5 remain
unqualified.
