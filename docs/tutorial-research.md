# AQSS contextual tutorial research and staged plan

Research date: 2026-09-27. Scope: the current read-only iPhone and Android
shells, including the Options and Advanced options work in PR #25.

## Problem, constraints, and measurement

People need help finding a control, understanding an unavailable option, and
returning to help later. A long first-launch tour is insufficient. Tutorials
must describe the actual screen and keep examples distinct from observations.
The only permitted effects are local navigation, section expansion, scrolling,
highlighting, and tutorial progress. No tutorial step is an audio request,
authorization, saved profile, observation, or change to physical state.

Goals: a stable Help button; a direct route to each relevant topic; short
steps with Back, Next, Close and replay; no automatic advancement; no repeating
animation; no network calls or raw media assets; no permission requests.
The <200 ms charter target remains a measured future sensor-to-eligible-response
goal. A 180 ms decorative transition is not evidence of that latency target.

## Source/evidence matrix

Grades describe authority (A), recency (R), reproducibility (P), implementation
relevance (I), bias (B), and evidentiary strength (E). Official documentation
establishes APIs/guidance; it does not establish AQSS usability outcomes.

| Source and finding | Grade and limitation |
| --- | --- |
| [Apple Onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding): teach in context and use interactivity. [TipKit](https://developer.apple.com/documentation/tipkit/) offers contextual tips; its APIs require iOS 17, while this app targets iOS 15. | A high; R current docs checked today; P API behavior testable; I high; B platform vendor; E strong API/guidance, not comparative AQSS evidence. |
| [W3C Consistent Help](https://www.w3.org/WAI/WCAG22/Understanding/consistent-help) and [WCAG2ICT](https://www.w3.org/TR/wcag2ict-22/): repeated help mechanisms should have consistent placement; the guidance extends to software. | A high; R WCAG 2.2 guidance; P layout and focus can be inspected; I high; B standards consensus; E normative/guidance, not a certification of this app. |
| [W3C Animation from Interactions](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html), [Apple Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityReduceMotion), [Android ValueAnimator](https://developer.android.com/reference/android/animation/ValueAnimator#areAnimatorsEnabled()): make nonessential motion optional and respect OS settings. | A high; R current API docs checked today; P deterministic flags plus device testing; I high; B standards/platform; E strong implementation basis. |
| Kelleher and Pausch, CHI 2005, [Stencils-based tutorials](https://www.cs.cmu.edu/~caitlin/kelleherCHI05.pdf), [author research summary](https://www.cs.cmu.edu/~caitlin/research.htm): contextual in-app guidance improved completion in the studied Alice task; mastery quiz performance was similar. | A peer-reviewed author-hosted study; R old; P published method, not replicated here; I medium (desktop programming); B authors evaluate own system; E supports a hypothesis, no transferable percentage gain claimed for AQSS. |
| Grossman and Fitzmaurice, CHI 2010, [ToolClips](https://www.research.autodesk.com/publications/toolclips-an-investigation-of-contextual-video-assistance-for-functionality-understanding/): contextual examples can fit into a primary task. | A primary research; R old; P published study, not replicated; I medium; B vendor researchers; E supports contextual examples, not mandatory video or animation. |

## Synthesis and alternatives

Selected combination: (1) consistent Help entry, (2) user-selected short topic
tours, (3) actual view highlighting with explanation and example, (4) accessible
manual progression with reduced-motion behavior. A single content contract
supplies both platforms. This is AQSS integration work, not a claim of novel IP.

Inference: combining these mechanisms should improve discoverability and let
people recover their place without accepting misleading simulated success.
The magnitude of that improvement is unproven. Source studies concern other
applications. A usability study must measure finding Help, understanding
Unknown/Unavailable, independent task completion, and successful replay.

| Alternative | Decision |
| --- | --- |
| Mandatory auto-advancing introduction | Reject: interrupts task, hard to revisit a specific area, timing barrier. |
| Video library | Defer: storage/bandwidth cost and need for captions/versioning; text examples and local UI transitions suffice now. |
| TipKit only | Defer: iOS 17 minimum and no Android counterpart for this iOS 15/Android Views app. |
| Custom blocking spotlight overlay | Reject: can obscure the target or trap focus; use an outline on the actual view and a separate tutorial panel. |
| Local topic tours | Select: no recurring work, timers, radio use, raw media or durable progress records. |

## Roadmap and tests

1. Define a bounded, presentation-only tutorial contract: named targets,
   supported screen areas, short nonempty text and labeled examples. Reject
   unknown fields/targets so a command cannot enter as a tutorial action.
2. Generate the same immutable content for Swift and Kotlin. Add persistent
   Help, section-specific entry points, manual Back/Next/Close/Done, a target
   outline, and bounded transitions honoring OS motion preferences.
3. Restore pre-tutorial section state on exit; closing/reopening starts the
   selected topic at step one. Keep all audio options unavailable and physical
   state unknown. Recheck generator parity and repository regressions.
4. In both hosted simulators, open Help, choose a topic, step forward/back,
   close, reopen another topic, verify highlighting and truthful labels.
5. Physical-device gates remain: VoiceOver/TalkBack focus, largest text sizes,
   reduced motion, small screens, rotation, lifecycle, and user comprehension.
   Measure startup/memory/battery and interaction latency before claiming gains.

No software tour or successful simulation test establishes actual audio output
or protection. The physical actuation and handoff gates remain prerequisites
for future functional tutorials that propose device changes.
