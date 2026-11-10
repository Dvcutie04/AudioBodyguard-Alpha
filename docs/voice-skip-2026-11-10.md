# Voice Skip Intro / Skip Recap — build-day software gate
**November 10, 2026.** Owner priority: "Audio Bodyguard, skip intro" or "Audio Bodyguard, skip recap" should activate the corresponding available button without reaching for a remote. Both mobile platforms are targets. This proposal is an **owned-player-only software prerequisite**, not a delivered phone feature or any streaming/TV integration.

## Initial tested contract
- Version: voice-skip-v1. Exact final English utterances after case/space/punctuation normalization. The two actions SKIP_INTRO and SKIP_RECAP are distinct. No ad skip, arbitrary seek or "Next" substitution.
- An explicit Start binds one listening run and one selected owned player, playback session, content and affordance generation. Stop invalidates that run. Partial/negated/ambiguous speech cannot propose an action.
- The chosen control must be visible and enabled both when the proposal is created and immediately before dispatch; a changed owner/player/session/content/generation/target is refused. A run has at most one callback; permission loss, background state, a stale run, replay, or a duplicate is rejected with zero callback calls.
- The resulting REQUESTED means only that the app-owned button callback accepted the request, NOT that playback has changed. A physically VERIFIED state needs an independent observation and qualified execution boundary later. No state restoration from speech or appearance.
- First unit fixture: src/voice/skip_command.py and tests/test_voice_skip_command.py. Native iOS and Android foreground recognizers currently display words only; neither yet invokes this Python gate or a real button. A native authored player fixture and both native policy implementations are next milestones.
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
