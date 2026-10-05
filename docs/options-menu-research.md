# Options menu: read-only native preview and capability-bound model

## Boundary and measurable goal

Expose the media options already modeled by `MediaControlOptionsMenu` in an
inspectable iPhone and Android simulation menu, with additional Dialogue and
Night preset choices and advanced explanations. The native shells have no
qualified output, capability manifest, independent observation, authority,
or physical adapter. Opening the menu can only change the local view. It
cannot show ACTIVE, call an adapter, or imply background protection. The
interactive expansion target is a responsive local UI; the charter's <200 ms
sensor-to-eligible-response target does **not** apply to these non-actuating
buttons and is not established by an emulator test.

## Evidence matrix and synthesis

| Source | Establishes | Scope, strength, and remaining gap |
| --- | --- | --- |
| Existing `src/control/media_control_capabilities.py`, `src/control/media_control_options.py` and `src/control/media_control_options_page.py` | Four supported operation types: volume, captions, preset, EQ bands. `SEMANTIC_PRESETS` includes Dialogue and Night. Profile recovery proposes manifest-bound requests or saves verified settings. | Direct code evidence, reproducible with focused tests. The model accepts a manifest object; it does not establish that a phone has one or that a physical adapter was called. |
| [Apple SwiftUI button documentation](https://developer.apple.com/documentation/swiftui/button) and [Apple touch guidance](https://developer.apple.com/design/tips/) | A native button can toggle the visible menu; Apple's touch guidance recommends a 44-point target. | Official platform guidance; a simulator test can inspect UI, but installed-device VoiceOver and large-text behavior remain unmeasured. |
| [Android accessibility guidance](https://developer.android.com/guide/topics/ui/accessibility/apps) and [settings organization](https://developer.android.com/develop/ui/views/components/settings/organize-your-settings) | Use discoverable controls and group related options; touch targets should be at least 48 dp. | Official Android guidance; Activity tests and emulator captures establish only simulated UI behavior. |
| Existing [native-shell scope](read-only-native-prototypes.md) and [Apple audio-session route documentation](https://developer.apple.com/documentation/avfaudio/responding-to-audio-route-changes) | A foreground callback is an app-session or device-inventory hint, not independent physical observation. | Repo contract plus official route API; no microphone, output, signed install, or real-device evidence. |

**Combination (inference):** a collapsed read-only menu, built from local
labels and gated future device options, can make the app easier to explore
without increasing monitoring duty cycle or implying that an option works.
The AQSS design keeps the prototype's unknown physical state visible even
when advanced details are expanded. Preset availability in the Python model
follows `EqCapability.SEMANTIC_PRESETS`; it is only capability metadata, not
authorization or physical success. The native preview has no manifest and
marks every audio option unavailable. No raw audio, new permissions, polling,
network requests, or profile writes are added by opening it.

## Alternatives and tradeoffs

| Approach | Assessment |
| --- | --- |
| Interactive audio sliders or switches that stay enabled without a verified connection | Rejected for this stage: no qualified adapter or observed output; a lasting enabled control would imply unsupported functionality. The owner's October 5 revision authorizes a two-second cyan attempt followed by automatic off, with an explicit Not connected prompt. |
| A separate third-party settings SDK | Adds binary size and state without improving the existing contract. |
| Local expandable Options / Advanced options, with passive details | Selected: minimal CPU and storage, no wakeups or permissions; menu text can be tested in both simulators. |

## Stage gates and empirical debt

1. Check deterministic menu contracts: Dialogue and Night appear only for
   semantic preset capability; unsupported controls retain a reason and
   advanced details never upgrade physical state.
2. Run XCUITest and Android emulator hierarchy assertions after explicitly
   opening both sections. Keep coverage/handoff unknown checks intact.
3. On signed physical devices, independently inspect VoiceOver/TalkBack,
   large text, rotation, OS lifecycle, and responsiveness. Measure actual
   opening latency, battery and storage if this becomes a persistent feature.
4. Before enabling *any* device option, establish signed capability and
   authority, deterministic policy, adapter isolation, physical commit,
   independent observation, and complete lineage. Maintain the closed
   handoff barrier and rejecting production factory until their own gates pass.
