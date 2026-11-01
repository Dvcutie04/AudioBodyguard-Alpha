# Setup experience review — 31 October 2026

Reviewed before implementation against the installed iPhone 1.0.0 (6.1) screenshots and Android 0.42 source. Both platforms use the same learning content; the later native branch also contains the current sound-check tools.

| Journey | Finding | Change |
| --- | --- | --- |
| First opening | Feature catalog competes with starting setup | One Start action, TV → phone illustration, optional `? Setup help` |
| Identify TV | Large brand list, More brands and photo action compete | Photo action plus one complete brand picker; confirmation still required |
| Home app | Required Alexa/Google question even when neither is used | Default to TV maker's app; choose a home app only from contextual help |
| TV pictures | Pairing alternatives and long route descriptions appear before needed | One instruction, illustration, Next; alternatives and sources inside `? Step help` |
| Phone pictures | Repeats device/platform choices already known | Keep the selected TV companion and platform-specific phone route |
| Completion | Generic full-app message gives little direction | Clear setup-guide result and direct sound-check shortcut in help |
| Home | Status details compete with setup | One main setup action; `? Status help` opens details and relevant jumps |
| Sound | Test arrangement, output reports, live and voice checks all look equally important | Two everyday checks; test/report tools behind `? More sound tools` |
| Devices | Photo, guides and a second tutorial entry overlap | Setup guide first; photo and diagnostic shortcuts in help |
| Insights | Example graph competes with actual recent checks | Recent checks first; examples in `? Insights help` |
| Settings | Three appearance buttons and advanced tools shown together | Current appearance opens picker; advanced/build/support behind `? More settings` |
| Photo/voice tools | Empty details and secondary clearing controls add noise | Main capture/recognition action stays visible; details, clearing and jumps in help |
| Navigation | Global help and Jump to list many unrelated sections | Contextual shortcuts; Back returns to the actual prior screen |
| Motion/accessibility | Large type can crowd header/footer | Flexible text, scrollable content, finite illustration cue, system reduced-motion support |

Defaults apply only to local presentation and optional guidance. Microphone, camera, network discovery, device approvals, sharing and audio controls retain explicit user actions. Guide completion and photo recognition never establish a verified connection.

Research: [Apple onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding), [Apple layout](https://developer.apple.com/design/human-interface-guidelines/layout), [Android accessible controls](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views), [Android animator preference](https://developer.android.com/reference/android/animation/ValueAnimator#areAnimatorsEnabled()). Use brief contextual instruction, postpone optional choices, retain large targets and stop motion when disabled.

Validation covers the default route, optional home-app override, photo cancellation and confirmation, immediate Back behavior, contextual shortcuts, normal/large text, and reduced motion on native simulators/emulators. Physical pairing and protection remain separate device checks.
