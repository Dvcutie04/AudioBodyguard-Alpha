# Voice error guidance — 0.23

October 23, 2026. This wording increment follows the tested 0.22 candidate.
Android Voice check previously displayed a generic message and a numeric speech
error. Common reported failures now receive a short explanation and a next step.
The existing callback admission check and stop/cleanup operation are retained.

## Existing research and source refresh

The [Android microphone lifecycle research](android-microphone-lifecycle-2026-10-20.md)
already covers on-device recognition, callback admission and cleanup. The public
[SpeechRecognizer error definitions](https://developer.android.com/reference/android/speech/SpeechRecognizer)
and [RecognitionListener.onError contract](https://developer.android.com/reference/android/speech/RecognitionListener#onError(int))
were refreshed before this edit. They define the reported categories and require
handling integer errors beyond the known constants. No new platform API or
recognition subsystem is introduced.

| Reported constant | Guidance |
| --- | --- |
| ERROR_AUDIO | Check microphone access, then explicitly Start again. |
| ERROR_SPEECH_TIMEOUT | Try another explicit Start and speak normally. |
| ERROR_NO_MATCH | Explain that no words matched and offer another explicit Start. |
| ERROR_RECOGNIZER_BUSY | Wait before another explicit Start. |
| ERROR_INSUFFICIENT_PERMISSIONS | Check app permissions before another explicit Start. |
| ERROR_TOO_MANY_REQUESTS | Wait before another explicit Start. |
| ERROR_LANGUAGE_NOT_SUPPORTED | Explain unsupported recognition here; suggest Live sound check for input levels. |
| ERROR_LANGUAGE_UNAVAILABLE | Explain current language unavailability; suggest Live sound check for input levels. |
| Any other integer | Give a generic stopped message and another explicit Start without inventing a diagnosis. |

Each message keeps the warning that displayed words may be incomplete. The text
describes the speech service's report. It does not establish room silence,
microphone hardware state, correct transcription or final recognized intent.
The permission category does not overwrite the independently checked OS grant.
Language unavailability does not imply that a download is definitely missing.

## Behavior and validation scope

The message is selected only after the current run passes the existing identity,
foreground/focus, permission and elapsed-time checks. It is then passed to the
existing stop operation; cleanup failure still overrides ordinary status text
and keeps capture blocked. There is no automatic retry, model download, cloud
fallback, new permission, stored data, background capture or output authority.
The helper returns fixed, bounded text even for an unfamiliar integer.

This is a reversible wording change. It uses source review against the native
constants and the existing behavioral regression suites, rather than adding a
test that merely repeats the message table. All existing assertions remain.
The Android native walkthrough records its actual speech-service attempt; it
does not inject a service, words or callbacks. If the host has no on-device
recognizer, that observation cannot establish the native appearance of every
error message. Exact final runs, observations and APK identity are recorded in
the candidate's draft pull request after verification.

Both native app candidates use the 0.23 release identity: Android code 23 /
`0.23-voice-error-guidance-live-input`, Apple 0.23.0 / build 1. iPhone production
logic retains 0.22 behavior and receives the normal regression and archive
checks. Handset speech accuracy, signed iPhone delivery, continuous protection,
TV control and N2b–N5 remain unqualified.
