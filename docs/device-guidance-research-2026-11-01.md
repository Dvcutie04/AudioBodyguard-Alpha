# Device-matched setup review — 1 November 2026

## Problem and measurable goals

The owner reports that options make it easy to get lost and prefers the iPhone's typography and picture-led flow. This is direct feedback from one person, not evidence of preferences across all customers. Review found that both connection stages present a picture action and a separate Next action which bypasses those pictures. The selected TV is not consistently visible while reading, model scope is hidden in help, and phone illustrations sometimes retain generic phone labels.

Apply the standing AQSS Research and Synthesis Charter before code. Target both native platforms: one primary action per connection stage, visible device context, accurate phone labels and store controls, a recoverable mismatch path, and preserved Back/resume behavior. Keep optional skipping available in Help. Do not infer connection, protection, exact TV model, consent or physical output from navigation or OCR.

Native screenshot review also found that large text replaced the Exit label with artwork alone. At accessibility text sizes, compact Exit/Setup/Close controls now use visible words; the original white-background artwork remains in the normal layout. Setup returns to the setup journey, while Back moves to the previous picture. A native interaction check caught the ambiguity when both controls initially said Back. Full accessibility names and minimum targets are retained.

The largest iPhone text setting exposed another layout cost: the long Illustrated setup header wrapped beside the visible Close label, leaving less than half the screen for choices. Its accessibility-size header now says Setup, with the full accessibility name retained. The native test requires at least half the screen for the choice list. Its scroll helper also requires a usable visible tap area and taps that area's center, avoiding repeated overscroll past tall rows.

## Evidence matrix

Sources retrieved 1 November 2026 Pacific time. Living documents describe published behavior, not installed-device verification.

| Source | Established evidence | Quality and limits | Implementation decision |
| --- | --- | --- | --- |
| Owner's screenshots and feedback | Crowded choices and inconsistent Android presentation interfere with this person's setup | Direct qualitative observation, one participant; no conversion or population estimate | Remove competing default navigation; retain the user's preferred readable visual hierarchy |
| [Apple onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding) and [writing](https://developer.apple.com/design/human-interface-guidelines/writing) | Contextual instruction, brief interactive onboarding, postponed customization, reasonable defaults and clear action labels | Official design guidance, living pages; recommendations, not an AQSS usability trial | One picture action; optional actions in clearly labeled Help |
| [W3C clear steps](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o1p04-clear-steps/) and [step instructions](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o4p07-step-instructions/) | Current location, important choices and concise adjacent illustrations help people orient themselves and correct mistakes | Primary cognitive-accessibility working-group guidance, 2021/2022; supplemental rather than a new WCAG conformance requirement | Visible selected TV/phone, route scope before starting, immediate mismatch recovery inside Help |
| [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Common tasks belong on the primary surface; secondary controls need clear names and shallow disclosure | Original practitioner guidance, 2006; no reproducible AQSS effect size | Keep one help level for skipping and recovery, avoiding a second competing Next |
| [Mayer, Hegarty et al., 2005](https://pubmed.ncbi.nlm.nih.gov/16393035/) | Four experiments compared static annotated diagrams/text with narrated animations; static groups did better on four of eight comparisons and did not differ on the others | Primary experimental paper abstract; students and mechanical/science lessons, not TV setup; cannot establish a universal animation preference | Retain persistent arrows/numbered targets and existing brief reduced-motion-aware cues; do not add decorative loops or time-controlled steps |
| [Apple Wi-Fi](https://support.apple.com/en-us/111107), [Pixel Wi-Fi](https://support.google.com/pixelphone/answer/2819519?hl=en), [Samsung Galaxy connections](https://www.samsung.com/us/support/answer/ANS10002546/) | Published phone menu families differ | Primary device vendors; firmware, country and accessibility settings can differ | Keep iPhone, Pixel and Galaxy routes distinct; do not label other Android phones as Pixel |
| [Google TV iPhone](https://support.google.com/googletv/answer/11136134?co=GENIE.Platform%3DiOS&hl=en) and [Android](https://support.google.com/googletv/answer/11136134?co=GENIE.Platform%3DAndroid&hl=en) | Both current documents now say TVs nearby at bottom right, device selection, TV code, Pair | Primary platform guidance, refreshed together; older app builds can differ | Share labels where the source agrees; do not invent an iPhone/Android difference. Distinguish actual store buttons and phone frames |
| [Roku network troubleshooting](https://support.roku.com/en-us/article/connect-your-phone-to-a-roku-tv-system-or-streaming-player) and [Google Home isolation](https://support.google.com/googlehome/answer/7300406?hl=en) | Same-network discovery can still be blocked by network isolation; Roku documents iPhone Local Network permission | Official product troubleshooting; not proof that every router or TV behaves identically | Preserve model-specific references and truthful recovery; no automatic router/account/permission changes |
| [Android accessible Views](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views) | Controls need adequate targets and useful accessibility descriptions | Official implementation guidance, updated October 2026; native UI testing still needed | Keep at least 48 dp Android targets, wrapping text and meaningful picture descriptions |

Source prestige is not proof. Community failure claims are not used as requirements; the owner's observed confusion and actual native source provide the field evidence here. Exact unsupported models remain unmatched instead of receiving another brand's picture sequence.

## Synthesis and alternatives

1. A long universal wizard minimizes implementation but mixes firmware and phone menus: reject.
2. Ask for every model, phone type, home app and preference before starting: accurate only if users know all answers, and increases choice burden: reject as the default.
3. Selected-device context + existing documented route families + native phone presentation + one-action navigation/recoverable Help: select this four-part synthesis.

The sources establish instruction and menu principles. Combining them into this particular flow is an AQSS design inference. The original AQSS work is the shared presentation transformation and native navigation arrangement; it introduces no new connection authority. Population preference, reduced abandonment, enjoyment and physical-model accuracy remain empirical debt.

Latency: transform only the current bounded step locally. Battery: no discovery, polling, new timers or continuous animation. Memory/storage: reuse the bounded catalog and existing bookmarks; no photos, networks or new user data are retained. These structural choices follow the charter's priority order but do not establish measured energy savings or the <200 ms physical-response target.

## Staged verification and remaining work

Write narrow tests first for phone label transformation, retained target/action/note/picture surface, immutable original catalog, and correct store controls. Then verify the native single-action flow, deliberate help skipping, selected-device context, model scope, Back/resume, normal/largest text and reduced motion. Run existing guide/catalog and deterministic regressions, native contracts and native UI checks.

Before claiming real-world accuracy for a new exact TV/firmware/phone combination, compare each illustrated target with that actual device and record mismatches. A later small novice trial should record completion without assistance, wrong turns, backtracking, perceived ease and confidence. Do not report improvements in those measures until observed. This review does not alter the source or verification of the pending TestFlight run.
