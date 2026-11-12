# Voice Skip: owned-playback evidence and first external compatibility review

**November 11, 2026, ~04:35 Pacific.** Evidence-gated V3/V4 checkpoint for
[voice milestones](voice-skip-next-milestones-2026-11-10.md) and
[long-term roadmap](long-term-roadmap-2026-11-10.md).
**No release, external control, network discovery, pairing or physical qualification.**
This document records results **at its source parent**, not a test pass for the
later documentation-only commit containing this file.

## Source-proven software state

At parent [`c3ca6424e847ebe2cf9b0e9e0fc270d9eb95f252`](https://github.com/Dvcutie04/AudioBodyguard-Alpha/commit/c3ca6424e847ebe2cf9b0e9e0fc270d9eb95f252),
tree `534b9e0b76ba1ee09060f7a5d4b5e2dbcc1b36bd`, open draft
[#121](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/121)
was stacked on unchanged #120. The [core workflow](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/43005373636)
passed **4/4** jobs on its exact branch source: 2,338 Python tests + 42
subtests, 149 Swift tests and iOS Simulator compilation, Android
contracts/APK compilation, and C11.

[Native UI workflow](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/43005373537)
completed successfully **on attempt 2**: iPhone XCTest retained the successful
original job (five selected, four passed, one OS-speech probe skipped); the
replacement Android job `130497525128` passed after an original API 36
*pre-app* emulator boot-dialog failure in job `130471414937`. The replacement
raw log checked out the exact branch head and tree and recorded all these
app-owned video fixtures:

- `VOICE_OWNED_FINAL_TEXT_FIXTURE_PASS`: supplied final **TEXT** for Intro
  and Recap goes through an isolated gate to the matching native MediaPlayer
  handler with independent position readback.
- `VOICE_OWNED_CANCELED_FINAL_TEXT_FIXTURE_PASS`: late canceled synthetic
  result does not seek the prepared player.
- `VOICE_OWNED_STALE_PLAYHEAD_FIXTURE_PASS`: competing manual playhead
  movement rejects the old request.
- `VOICE_OWNED_BACKGROUND_FINAL_TEXT_FIXTURE_PASS`: late text after Home
  cannot restore the stale player/session or seek.
- `VOICE_OWNED_BUTTON_FIXTURE_PASS`: native Intro and Recap buttons read
  back their respective local transitions.

The iPhone native XCTest suite covers the corresponding separate actions,
native AVPlayer position observation, cancellation and Home/recreation refusal.
These use an authored **silent 8-second local clip** and test-only supplied
text or manual buttons. They are **not audio recognition or a phone microphone
test**. A native callback being REQUESTED is distinct from independent
*software player* position observation; neither is proof of physical output.

[Unsigned iOS preflight](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/43005380917)
also passed 1/1 on *PR merge snapshot*
`8e95ac7bcf88c80a382653fc509e0dd6cd48cb28`, the same Git tree.
It is **not** a signed release.

## First V4 target evaluated: Jellyfin media segments

Jellyfin's [official media-segments documentation](https://jellyfin.org/docs/general/server/metadata/media-segments/)
says server 10.10 introduced typed segments, explicitly including both
`Intro` and `Recap`. **Plugins provide** beginning/end/type marker
metadata; availability is library-, plugin- and client-dependent. Clients
choose how to act on a provided segment, potentially displaying a Skip button.
Jellyfin's own [MPV Shim configuration](https://github.com/jellyfin/jellyfin-mpv-shim/blob/master/docs/configuration.md)
documents per-type `off` / `ask` / `always` behavior (including Intro
and Recap) **within that player's UI**. This establishes a documented
semantic *segment category and client behavior*, not an API granting
Audio Bodyguard the ability to remotely trigger that client's Skip button.

The reviewed primary materials **do not establish a supported, authenticated,
remotely callable semantic Skip Intro or Skip Recap command for an unrelated
controller**. Do not equate reading segment timestamps with authority to
seek; do not substitute generic playback Seek/Next, screen scraping,
coordinate taps, accessibility bots, DRM bypass, or ad skipping.
**Decision: external command adapter UNAVAILABLE pending a separately
documented client/controller capability, permission and observation contract.**
This is a bounded documentation finding, *not* a universal absence claim.

## Capability matrix (source-specific)

| Target / source | Real on-device speech input | Supplied final-text + gate | Semantic Intro/Recap action | Independent player readback | Authenticated external control | Physical verified |
| --- | --- | --- | --- | --- | --- | --- |
| AQSS iPhone Simulator, #121 parent above | **BLOCKED/UNRUN:** speech capability probe skipped; no authorized audio trial | **PASS** in simulator-only test pathway | **PASS**, authored AVPlayer local fixture, not another app | **PASS**, known 0→2s / 4→6s paths plus negative cases | Not implemented | **NO** |
| AQSS Android API 36 emulator, #121 parent above | **BLOCKED/UNRUN:** no qualifying on-device recognizer service reported; audio NONE | **PASS**, debug/emulator-only synthetic fixture | **PASS**, authored local MediaPlayer fixture, not another app | **PASS**, exact-source log markers above | Not implemented | **NO** |
| Jellyfin 10.10+ server/client with suitable media-segments provider | Not assessed | Not integrated with AQSS | **Documented conditional metadata and in-client Skip UI**; support depends on plugin/client/config/content | Not tested by AQSS | **Not established for a semantic remote Skip command** | **NO** |

## Next falsifiable decisions

1. **V2 acoustic gap:** only on a hosted/runtime configuration with granted
   permission, supported on-device recognition and proven authored-audio input
   provenance, feed each actual recording through the real OS final-result
   callback and selected owned-player gate; retain actual transcript, input
   hash, locale, no-op negatives and independently observed action. Do not
   mislabel supplied text as speech, or recorded-audio input as a microphone.
2. **V3 closure:** hold the exact green branch/tree and negative-control
   artifacts; preserve the first Android pre-app boot failure and the bounded
   successful rerun. A green workflow does not erase its failed attempt.
3. **V4 external prerequisite:** obtain a *primary documented*, client-
   advertised and authenticated semantic Skip command with a target identity,
   capability generation, content/segment state and independent readback.
   Otherwise display **unavailable**. No live Jellyfin server access is
   authorized under this shift.
4. **V5/V6 and core AQSS:** evaluate named iPhone/Android hardware and language
   constraints only with separate authorization. #120 Share, Wi-Fi return,
   compact/older iPadOS remain unresolved. #114 Android 0.50/build52 and
   #115 iPhone/iPad Simulator 0.50.0/build5 remain historical package baselines.
   T1/N2b–N5 physical identity/output/measurement/finality remain open.

**Evidence discipline:** GitHub job success and authored media readback establish
software behavior on these specific runners; they do not establish microphone
recognition, real external media control, TV pairing, real speaker output or
protective physical effectiveness.
