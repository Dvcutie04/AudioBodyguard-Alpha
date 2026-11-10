# Voice Skip Intro / Skip Recap — build-day software gate
**November 10, 2026.** Owner priority: "Audio Bodyguard, skip intro" or "Audio Bodyguard, skip recap" should activate the corresponding available button without reaching for a remote. Both mobile platforms are targets. This proposal is an **owned-player-only software prerequisite**, not a delivered phone feature or any streaming/TV integration.

## Initial tested contract
- Version: voice-skip-v1. Exact final English utterances after case/space/punctuation normalization. The two actions SKIP_INTRO and SKIP_RECAP are distinct. No ad skip, arbitrary seek or "Next" substitution.
- An explicit Start binds one listening run and one selected owned player, playback session, content and affordance generation. Stop invalidates that run. Partial/negated/ambiguous speech cannot propose an action.
- The chosen control must be visible and enabled both when the proposal is created and immediately before dispatch; a changed owner/player/session/content/generation/target is refused. A run has at most one callback; permission loss, background state, a stale run, replay, or a duplicate is rejected with zero callback calls.
- The resulting REQUESTED means only that the app-owned button callback accepted the request, NOT that playback has changed. A physically VERIFIED state needs an independent observation and qualified execution boundary later. No state restoration from speech or appearance.
- First shared unit fixture: `src/voice/skip_command.py` and `tests/test_voice_skip_command.py` (33 focused passing tests at the initial source). Native iOS and Android policy gates now exist, and current source `0c8a89985aadd18f4b1061141e6bdddf64016045` connects final on-device transcript callbacks to the corresponding owned test-player button handler. This is a code-path and compile/unit observation, **not** observed spoken-command execution or any external playback support.
- No microphone permission, socket, third-party accessibility control, unconsented background recognition, cloud fallback, account, pairing or live actuation is added.

## Native and physical acceptance before claiming this feature
1. Implement matching finite phrase and single-callback policy in iOS and Android. Native speech final results from an explicitly user-started on-device session propose, rather than execute, the command.
2. Add clearly labeled owned-player fixture with actual distinct Skip Intro/Skip Recap buttons. Exercise each phrase to the matching callback once on iPhone and Android native test targets. For denied, stale, disabled, partial, unsupported, stopped or background cases, assert zero callbacks. Show distinct recognized/requested/unavailable outcomes.
3. Check actual OS permissions, supported on-device recognition by language and device, interruption handling, transition out of foreground, previous screen navigation and resource budgets; retain the explicit Start mode. No unconditional always-listening promise.
4. Only after documented external-player capability and authenticated device authority may a separate adapter be considered. Physical Commit requires independent state observation. Do not infer that an OS media Next command can skip an intro/recap, or claim Netflix/VIZIO/other providers are supported.

Official platform references consulted on November 10, 2026:
- Apple: https://developer.apple.com/documentation/speech/sfspeechrecognizer/supportsondevicerecognition
- Apple: https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition
- Android: https://developer.android.com/reference/android/speech/SpeechRecognizer
- Media3: https://developer.android.com/media/media3/session/control-playback

Source lineage: branch aqss/voice-skip-owned-player-fixture is stacked on #120 head 6ea247cc4ce8002e296b7c8d2d5846b939777a74, tree 11540179fa75705e866106563a2dca4213efe9e8. Earlier #120 Share failures remain and are not fixed by this increment. Keep iPhone and Android equal and the roadmap's N2b–N5 evidence gates unchanged.

## November 10 ~11:30 Pacific — focused native UI acceptance increment

Initial native gate source is [draft #121](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/121) at `0c8a89985aadd18f4b1061141e6bdddf64016045` / tree `873ee8cc9dab589fe0af66bb7f767e69cc6e66ca`. Exact-head [core CI 42879668388](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42879668388) passed 2,313 Python tests (+42 subtests), 144 Swift tests, Android build/unit, and C11; [unsigned preflight 42879677203](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42879677203) passed. Those passes **precede** this UI-test increment and cannot prove its newer source.

A new focused native UI harness is intended to check actual visible Skip Intro and Skip Recap test-player buttons and their independent disabled/reset states on iPhone Simulator and Android emulator, with screenshots and scoped source/revision receipts. It does **not synthesize spoken phrases** or claim external player control. Future separately consented microphone trials must produce actual recognizer final events, exercise the same matching callback once, verify a real player state transition, and document OS/language/device limitations. The phrase contract and owner authorization still fail closed for stale targets and unsupported players. A failed/queued native run must remain a failure/queued, not a success.

The verified Android 0.50/build52 and iOS Simulator 0.50.0/build5 downloads remain old baselines; no new signed app or TestFlight/Play distribution is authorized.

## November 10 — Cross-platform fail-closed policy refinement (proposed source update)

On all three shared/native owned-fixture gates, loss of permission or foreground ownership while a recognized final proposal is pending terminates that listening run. Restoration alone cannot revive its old result: another explicit Start and fresh run ID are required. The Python grammar now rejects non-ASCII padding as iOS/Android already do, preventing Unicode whitespace normalization drift. New regression tests on all platforms cover stale-result revival and Unicode padding rejection. This remains software-only evidence, not microphone-speech, third-party-player, TV or physical output verification. The exact commit and CI verdict must be recorded after the source update; this paragraph alone does not claim tests passed.

## November 10 ~13:30 Pacific — final-recognizer-event acceptance seam

The iPhone and Android final-recognizer callbacks now call a single `requestFinal` function also exercised in Swift/Kotlin native tests; the shared Python mirror uses `request_final`. This composes exact final-phrase parsing, fresh owned-control authorization, and one-at-most callback. New cases cover Intro and Recap, duplicate results, lost permission/foreground and changed control generation. This is **supplied final-recognition text testing**, not a microphone-spoken trial, external streaming/TV control or physical playback verification. No release/distribution was performed. Record exact-source Actions results after the commit; earlier results do not verify this new code.
