# Sequential first-visit guide — 29 September 2026

## Problem and scope
The owner tested the simulator preview and could not identify what to do first or what the app actually supports. The old tutorial left all pages and choices visible behind its instructions. This is direct user feedback, not a general usability study.

Goal: one current task, one chronological path, no later-page controls during the guide; an always-reachable exit reveals every app destination and expanded option group. TV and smart-home choices tailor explanations only. No connection, account linking, permission request, or adapter call is implemented here. Physical state stays UNKNOWN_PHYSICAL_STATE.

## Evidence matrix
All links reviewed 29 September 2026. Primary platform documents establish API requirements, not AQSS compatibility or store approval.

| Evidence | Authority / recency / limitations | Design consequence |
| --- | --- | --- |
| [Apple onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding) | Primary, living guidance; qualitative recommendation, no measured benefit for AQSS | Keep guidance optional and easy to leave; do not require completing a tour to explore. |
| [Apple layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Primary, living guidance; developer perspective | Progressive disclosure: present one task and remove competing page navigation during the guide. |
| [W3C text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) and [non-text contrast](https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html) | Primary accessibility criteria, reproducible numerical checks; web guidance applied as a native design benchmark | Cyan fill with dark text, contrasting outline in light mode; selection uses a checkmark and accessible state, not color alone. |
| [W3C non-text content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content) | Primary accessibility criterion | TV, speaker and house illustrations always accompany readable names; images are not the only label. |
| [Google Cast discovery](https://developers.google.com/cast/docs/discovery) and [iOS permission/discovery](https://developers.google.com/cast/docs/ios_sender/permissions_and_discovery) | Primary SDK documentation, implementation relevant; establishes Cast requirements only | A TV brand alone does not prove compatibility. Cast requires suitable devices, network access and a real integration. No pretend discovery spinner or successful pairing. |
| [Alexa account linking](https://developer.amazon.com/en-US/docs/alexa/smarthome/set-up-account-linking-tutorial.html) | Primary developer tutorial, May 2026; vendor ecosystem scope | Explain checking the manufacturer's compatible skill and account linking in Alexa. Selecting Alexa here grants no authority. |
| [Google Home permissions](https://developers.home.google.com/apis/android/permissions) and [supported device types](https://developers.home.google.com/apis/android/supported-device-types) | Primary developer documentation, 2026; support depends on type/traits and permissions | Explain model-specific support and permission. Do not imply every Google Home device can control TV audio. |
| Owner's preview feedback | Direct evidence for this user; not a population-level study | Remove numbered shortcuts to later steps, competing menus and dense overlay text. Use concrete TV, dialogue and loud-advert examples. |

## Synthesis and alternatives
A minimal combination of progressive disclosure, native labeled illustrations, and deterministic local guide state fits this revision. An overlay tour was rejected because it preserves the distraction the user reported. A live pairing wizard is not yet defensible: the app has no qualified device integration. A broad device-integration subsystem would require its own research and authority/observation gates.

External sources establish the guidance principles and vendor requirements. Their combination suggests (an inference, not proven outcome) that a dedicated guide with temporary brand/home choices will make the next action easier to identify. AQSS-specific work is the fail-closed presentation state machine and truthful tailored connection checklist; no novelty or patentability claim is made. Usability improvement remains to be confirmed by another user walkthrough.

Sequence: introduction → TV brand → home app → tailored preparation → connection truth → concrete feature example → full app. Choice steps require a valid selection; “Not sure” and “Neither” remain legitimate answers. Back is bounded. Exit is available at every step. Finishing records only that the tutorial was dismissed; it never records a connected device or protection success.

Optimization: no polling, radios, raw audio, network calls, wake locks or continuous animation. One local dismissal flag plus existing appearance preference; device choices are temporary. No battery or latency gain is claimed without measurement. Launch artwork remains unchanged and is not delayed for the tutorial.

## Stage gates and tests
1. Red: replace the old five-page contract test with chronological connection steps and reject ambiguous/command-bearing choices.
2. Green: shared bounded text/choices; deterministic native selection/advance/back/restore models; no authority or adapter dependencies.
3. Native UI: clean first launch, later controls absent, choice gating, tailored Samsung/Alexa example, back, exit and replay, all pages after exit, persisted dismissal, contextual help, largest text, theme contrast.
4. Android: fresh-install walkthrough, configuration rotation while choosing, dismissal/relaunch, synthetic chart and all existing unavailable states.
5. Regression: Python suite and generated-content checks; Swift and Kotlin unit tests; native C11/sanitizer gates; simulator UI runs. Inspect actual screenshots from both platforms.
6. Package the exact tested iOS Simulator build, including startup artwork, for Appetize. This evidence covers simulator UI behavior only.

## Remaining research
Real connection requires exact model/protocol compatibility, authorized discovery and account linking, deterministic policy, capability leases, adapter isolation and independent physical observation. Cloud screenshots and tutorial completion cannot satisfy these gates. A new-user study should measure time to first correct action, mistaken “connected” interpretations and exit discoverability; no targets are asserted as achieved yet.
