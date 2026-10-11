# Audio Bodyguard interface design

Research and design: 2026-09-28 UTC.
Base: PR #27, source `f801f01c7ae1056a5c4327a4d84b82c04cef2150`.
The user authorized this interface research with Astra Max active. Scope is
interface recommendations, user/developer criticism and design evidence.

## Goal and constraints

Replace the long prototype screen with a coherent, navigable native interface
on iPhone and Android. The supplied images establish a visual direction:
navy, cyan, violet, layered panels, wave motifs and data views. Their marketing
claims, dB readings, interception totals, ad skipping and universal device
control are not AQSS evidence or approved functionality.

The app must distinguish available navigation/appearance/help from future
audio controls. Missing observations stay unknown. An example chart must be
explicitly synthetic, optional and unable to enter the evidence projector.
No design interaction may authorize an audio action or open a physical gate.

## Evidence matrix

Sources retrieved September 28, 2026. A=authority, R=recency, P=reproducibility,
I=implementation relevance, B=bias, E=evidence strength. These sources do not
establish AQSS usability outcomes or a single universally best interface.

| Source | Finding and grade |
| --- | --- |
| [NN/g mobile navigation study](https://www.nngroup.com/articles/find-navigation-mobile-even-hamburger/) | Visible routes improved discoverability in a 179-participant, six-site study. A: primary usability researchers; R: 2016, older; P: method described; I: medium-high, web to native inference; B: consulting; E: empirical in those tasks, no transferable AQSS percentage. |
| [Android layout/navigation guidance](https://developer.android.com/design/ui/mobile/guides/layout-and-content/layout-and-nav-patterns) | Three to five peer destinations; adapt navigation to available space. A: platform; R: current; P: documented APIs/layouts; I: high; B: vendor; E: strong implementation guidance, not a usability measurement. |
| [NN/g dark mode user research](https://www.nngroup.com/articles/dark-mode-users-issues/) | Test contrast and channel consistency; consider system preference and an override. A: primary researchers; R: 2023; P: described observations; I: high; B: consulting; E: qualitative, not proof dark mode improves all reading. |
| [Reddit design critique](https://www.reddit.com/r/UI_Design/comments/ssa952/) and [navigation discussion](https://www.reddit.com/r/UXDesign/comments/1er4ftt/) | Indexed user/developer comments flag poor dark contrast and changing navigation conventions. A: unverified individuals; R: 2022/2024; P: low; I: discovery only; B: self-selection; E: anecdote. Full-thread fetch failed; no consensus or representative-user claim is made. Corroboration comes from the platform and usability sources above. |
| [NN/g empty states](https://www.nngroup.com/articles/empty-state-interface-design/) | Explain missing data and provide a useful next step or optional example. A: expert primary critique; R: 2021; P: concrete examples; I: high; B: consulting; E: design guidance. |
| [IBM Carbon empty states](https://carbondesignsystem.com/patterns/empty-states-pattern/) | Replace absent data with a concise message; avoid repeating large empty widgets and competing actions. A: design-system maintainers; R: current; P: inspectable patterns; I: high; B: enterprise vendor; E: implementation guidance. |
| [W3C contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Normal text contrast of at least 4.5:1 provides a measurable palette constraint. A: standards body; R: current WCAG 2.2; P: calculable; I: high; B: consensus; E: conformance criterion, not full native accessibility certification. |
| [Apple tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars) and [charting data](https://developer.apple.com/design/human-interface-guidelines/charting-data) | Official pages were JS-only on direct retrieval. Indexed official guidance and existing native APIs inform labeled navigation and chart descriptions; no full-page review is claimed. A: platform; R: current; P: limited retrieval; I: high; B: vendor; E: limited for these pages. |

## Selected synthesis

Five stable pages combine visible navigation, restrained visual hierarchy,
contextual help and honest data states. These mechanisms come from the sources;
their combination with AQSS's physical-truth boundary is our design decision.
Reduced search effort and improved comprehension are hypotheses requiring
user testing. No novel IP or measured improvement is claimed.

| Page | Current usable interface | Future capability shown with its limitation |
| --- | --- | --- |
| Home | Coverage summary, readiness route, quick navigation, tutorial | A listening session requires a qualified path; no start/protected claim. |
| Sound | Options, presets, captions, EQ and undo explanations | Volume, Dialogue/Night, EQ, caption selection and verified undo remain unavailable. |
| Devices | Connection-path explanation, six unknown checks, OS hint, transfer help | Device discovery/authorization and bidirectional handoff need qualified adapters and observation. |
| Insights | Honest empty chart/history state; optional synthetic line chart with text values | Real trends, change history and coverage statistics require qualified observations. |
| Settings | Midnight/Daylight/System appearance, tutorials, privacy and advanced details | Voice proposals, adaptive profiles and background supervision are planned, with clear prerequisites. |

Midnight is the initial appearance to match the user's explicit references;
Daylight and System are available. Appearance is the only new persisted value
(a bounded local enum). Tutorial and example state remain temporary. Icons and
art are native vector paths; no new rendering framework, media download,
recording, telemetry, polling or repeating animation is introduced.

Screenshot review found that a stacked Android tutorial left too little page
content visible in landscape. Wide Android windows therefore place the guide
beside the page, with independently scrollable explanations and a persistent
exit. The runtime check requires the highlighted heading to remain visible
beside or above the guide, including after rotation. This adaptation follows
the layout guidance above; device-level screen-reader testing remains open.

Alternatives: a poster-like all-in-one dashboard obscures priority; a hamburger
only makes discovery harder; realistic fake metrics imply observation; a
custom audio engine is outside this interface increment. The selected design
uses current Views/SwiftUI and shared presentation tokens/content.

## Staged acceptance and remaining measurements

1. Red/green: reject malformed chart samples, unlabeled example data and
   insufficient theme contrast; generate identical content for both apps.
2. Implement themed cards, labeled page navigation, contextual tours, empty
   states, optional example and appearance controls without an adapter import.
3. Run both native walkthroughs: every page, future-feature explanation,
   tutorial across pages, return/rotation, example exit back to unknown,
   theme change, large text and screenshots. Preserve core boundary tests.
4. Run deterministic regressions, native builds and unsigned device preflight.
   Save source/run provenance on the PR.
5. Physical VoiceOver/TalkBack, small-screen usability, localization/RTL,
   minimum-OS matrix, comprehension, battery/memory and interaction timings
   still need measurement. The charter's <200 ms and sub-milliwatt targets
   are not inferred from a visual transition or green simulator test.

All research here concerns presentation. The rejecting production factory,
closed handoff barrier, authorization lineage and unknown physical state remain
mandatory. Future audio/voice/background features need their own research and
device qualification before implementation.
