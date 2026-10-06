# Foreground voice feedback and photo-assisted TV setup

Research date: 2026-09-29. Scope: the existing iOS/Android read-only shells.

## Problem and boundary

The user needs visible confirmation that speech is reaching the microphone, plus less typing during TV setup. A microphone level is not word recognition, a transcript is an estimate, a photo is not device identity, and an IP address is not authority. No input from either feature may invoke a physical adapter or change coverage from UNKNOWN_PHYSICAL_STATE. There is no qualified pairing adapter in the shells today.

## Evidence matrix

| Source | Established fact | Grade and limits | Use |
|---|---|---|---|
| [Apple live speech](https://developer.apple.com/documentation/speech/recognizing-speech-in-live-audio) | Audio buffers can feed recognition | Primary API documentation; reproducible on supported devices, no accuracy or latency guarantee | Foreground AVAudioEngine + explicit microphone/speech permission |
| [Apple on-device recognition](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition) | On-device requests require supported recognizer | Primary, platform-specific; availability varies by locale/device | Require local recognition; no silent cloud fallback |
| [Android SpeechRecognizer](https://developer.android.com/reference/android/speech/SpeechRecognizer) and [RecognitionListener](https://developer.android.com/reference/android/speech/RecognitionListener) | On-device recognizer available from API 31; RMS and partial-result callbacks available, not guaranteed for all implementations | Primary API contract; measure provider behavior | Explicit short voice check; truthful missing-level state |
| [Apple Vision OCR](https://developer.apple.com/documentation/vision/recognizing-text-in-images) | Vision extracts text from images | Primary; blur, glare and unusual fonts can cause errors | Local photo recognition, bounded image size |
| [ML Kit text recognition](https://developers.google.com/ml-kit/vision/text-recognition/v2/android) | Bundled and downloaded models; focus/resolution matter | Primary; vendor documentation; no promise of exact device identification | Bundled Latin OCR; no dependency on model-download availability |
| [Samsung pairing instructions](https://www.samsung.com/us/support/answer/ANS10005262/) | Model-dependent SmartThings setup and TV approval/account steps | Primary manufacturer support; not proof of universal compatibility | Explain approval; do not bypass with OCR/IP |
| [Mobile speech research](https://arxiv.org/abs/1603.03185) | Compact on-device speech can be practical; measured word errors remain | Academic preprint, older hardware/model, not performance evidence for AQSS | No claim of recognizing every sound or syllable |

Source prestige does not establish AQSS behavior. User feedback supplies the usability requirement; native tests and later physical trials supply implementation evidence.

## Synthesis and alternatives

Use four separate mechanisms: short opt-in capture, visible input-level history, provisional local transcription, and bounded OCR followed by human review. This is AQSS composition, not a claim of new recognition algorithms. Local processing avoids uploading recordings/TV labels. A moving meter demonstrates input activity only; it is not a frequency equalizer, calibrated dB SPL, syllable counter, or independent output observer. Do not fabricate moving bars when samples are missing.

Reject continuous listening (battery/privacy/platform cost), cloud OCR/LLM device selection (avoidable data disclosure and nondeterminism), and URL/IP execution from OCR (untrusted input). No photo serial number, password, QR payload or URL is used as an endpoint. Accept only explicitly labeled, unambiguous private IPv4 candidates as editable hints. The TV's rear label usually identifies brand/model, whereas its current IP is found in network settings and may change. Exact menu paths vary by model.

## Smallest architecture and truthful states

- Voice: idle → permission request → listening → stopped/error/unavailable. Start is a deliberate tap. Stop on close, app background/interruption or 30-second timeout. No background mode or automatic restart. Buffer only 40 display levels and 500 transcript characters. No raw audio persistence. Late callbacks cannot revive a stopped session. Recognition does not execute a command.
- Photo: pick/capture → local OCR → review hints → connection instructions. Missing/conflicting text remains unknown. Raw text is not retained or logged; only brand/model/IP hints are shown. Close/delete clears hints. Image work is bounded to 2048 pixels on its longest side. A camera/gallery may retain its original photo outside AQSS; AQSS does not save a copy.
- Identified and connected are distinct. This iteration identifies/prepares only. Production control remains blocked. Real automatic pairing requires a separately researched, authenticated vendor adapter, explicit approval, capability leases, physical commit and independent observation.

## Optimization targets and empirical debt

Target microphone-event to meter update <200 ms, with at most 10 UI updates/sec and no continuous wakes after stop. This is a measurement target, not a promise. Speech/OCR completion has no sub-200 ms guarantee. On-device OCR model increases Android APK footprint; choose bundled availability over first-use network delay. No sub-milliwatt claim: microphone and speech recognition consume power while active. Measure latency percentiles, energy, interruption recovery, speech errors, clipped input, room noise, accents and OCR glare on installed phones. Simulator success cannot qualify these.

## Stage-gated test plan

1. Red/green deterministic tests: unknown/multiple labels, invalid/public/loopback IPs, mislabeled gateway/DNS, hostile URLs and overlong data. Never auto-correct OCR into an address.
2. Implement opt-in native tools with cyan controls, local-only processing, no actuation dependencies and honest unavailable states.
3. Validate denied permissions, missing recognizer/camera, close/background/timeout, stale callback cancellation, bounded UI state and source data clearing. Run full deterministic regressions and native builds.
4. Simulator navigation checks: tools start idle, no unsolicited permissions, clearly identified transcription vs input level, no connection claim.
5. Installed-device trial before release: microphone waveform/recognition latency and accuracy, photo quality, permission interruption races and battery/memory. Then select one vendor integration and research its supported auth/pairing APIs separately. Do not imply a universal photo-to-control path.
