# Native app audit and improvement plan

Research started 2026-09-27 UTC; implementation continued 2026-09-28 UTC.
Baseline: tutorial PR #26, `22d3d9191139ec03b2581f843567c462d253d0ed`,
including options PR #25. Both were unmerged when this review began.

## Scope and findings

Reviewed every shipping native screen, Options/Advanced section, tutorial,
foreground hint listener, native reference projector, feedback DTO/interface,
manifest/build configuration, UI test and shared content generator. The apps
currently each have one read-only screen with expandable sections. Reviewed
the production factory and endpoint handoff gate as boundary checks; this is
not a fresh security audit of every Python/C subsystem.

| Area | Finding | Selected action / remaining gate |
| --- | --- | --- |
| Coverage / physical truth | Both shells pass no observation and show unknown; foreground OS hints stay separate. | Preserve. No successful tutorial or checklist may upgrade coverage. |
| Supported controls | Six prerequisites are summarized but not individually explained. | Add an expandable six-row readiness checklist and its own replayable tutorial. Rows are unknown descriptions, never switches to assert success. |
| Options / Advanced / navigation | Long nested content requires repeated scrolling to find another area. | Persistent Jump to alongside Help; selecting a destination expands its section and closes an active tour. |
| Accessibility | Swift button frames outside labels may leave smaller hit areas; headings have only visual styling. | Put minimum 44-point areas inside Swift labels, mark headings, describe expansion, restore help focus, retain system text scaling and reduced motion. Android buttons use at least 48 dp. |
| Android Back | Default Back exits with tutorial or menus open. | Consume Back only for open tutorial, then advanced, options, or checklist. Unregister callback at root so system navigation remains available. |
| Android capability projection | Public constructor/copy can set `canActuate=true` despite the read-only contract. | Reject both construction and copying with true. This is a misleading-value defect, not a demonstrated adapter bypass. |
| Captions / presets / EQ / defaults / undo | No qualified native controller or authored caption source. | Retain unavailable explanations. Defer functional controls until authority and result observation exist. |
| History / privacy | No native session record store, raw audio, analytics, or network client is connected. Temporary tutorial/menu state only. | Keep local content and bounded temporary navigation state. No account, tracking, permissions or media capture added. |
| Platform lifecycle | Listeners unregister, epoch guards reject late notifications; gaps stay unknown. | Exercise background/return and rotation in smoke checks; physical interruption and process-death trials remain open. |
| Build / deployment | Unsigned simulation and iPhone preflight exist; signed installation is separate. | Preserve no-cost hosted tests. TestFlight enrollment/signing is not provided by a simulator artifact. |
| Physical boundary | Production factory still rejects; endpoint barrier still returns false. | Preserve and run deterministic regressions. No hardware or acoustic qualification claim. |

## Evidence matrix

Grades cover authority (A), recency (R), reproducibility (P), implementation
relevance (I), bias (B), and evidence strength (E). Retrieved 2026-09-27/28.

| Evidence | Grade and what it establishes |
| --- | --- |
| [Android accessible controls](https://developer.android.com/guide/topics/ui/accessibility/apps): recommended 48 dp touch areas, contrast and useful labels. [Accessibility principles](https://developer.android.com/guide/topics/ui/accessibility/principles): headings and pane semantics aid navigation. | A high; R current official docs; P emulator/manual checks possible; I high; B platform vendor; E API/guidance, not proof of usability. Views-specific guidance is linked from these pages. |
| [Android predictive Back](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture): register/disable callbacks according to UI state; root interception suppresses system animations. | A high; R updated Sept 2026; P API 33+ emulator reproducible; I high; B vendor; E strong API behavior. Pre-33 needs fallback. |
| [Apple accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility), [SwiftUI focus](https://developer.apple.com/documentation/swiftui/accessibilityfocusstate), [designing for games](https://developer.apple.com/design/human-interface-guidelines/designing-for-games): focus semantics and touch sizing (44 points in Apple's cross-platform guidance). | A high; R current API, older design guidance; P simulator plus VoiceOver device checks; I high; B vendor; E implementation guidance. HIG accessibility page body was JS-only in retrieval; do not treat that fetch as a full text audit. |
| [W3C headings](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html), [focus order](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html), [consistent help](https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html) and [WCAG2ICT](https://www.w3.org/TR/wcag2ict-22/). | A standards body; R current guidance; P semantic/layout checks; I high when adapted to native; B consensus; E design constraints, not app certification. |
| [Kotlin data classes](https://kotlinlang.org/docs/data-classes.html): generated copy calls the primary constructor with supplied fields. Local code exposes a true actuation field. | A primary language docs plus inspected source; R current; P narrow negative unit test; I direct; B language vendor; E directly falsifiable defect. |
| [Apple background strategies](https://developer.apple.com/documentation/BackgroundTasks/choosing-background-strategies-for-your-app), [WWDC25 background execution](https://developer.apple.com/videos/play/wwdc2025/227/), [Android background service limits](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start). | A primary platform; R current including newer continuation tasks; P device trials required; I high for supervisor backlog; B vendor; E rejects assumptions of arbitrary continuous background monitoring. |
| CHI 2005 Stencils and CHI 2010 ToolClips, primary author sources in [tutorial research](tutorial-research.md). | A peer-reviewed; R old; P published methods, not replicated here; I medium (other tasks/platforms); B authors studying own designs; E motivates contextual explanations, does not predict an AQSS gain. |

Community Back-navigation reports were discovery clues only; decisions above
use official behavior and our reproducible tests. Broader silicon/quantum,
radio and cryptographic mechanisms do not solve this presentation problem.

## Synthesis and measurable goals

Selected small architecture combines four mechanisms: persistent navigation,
explanatory readiness, contextual tutorials, and accessibility semantics.
The source-backed pieces establish supported APIs and recommended patterns.
The inference is that direct navigation and individually explained missing
checks reduce searching and misunderstanding. AQSS's integration keeps every
example and UI action separate from evidence and actuation; no IP novelty is
claimed. Empirical debt includes task completion, comprehension, actual
VoiceOver/TalkBack focus, small displays, energy, memory and interaction timing.

Compared with a new multi-screen navigation framework, this reuses native
Views/SwiftUI and bounded compiled text. Compared with an AI assistant, it adds
no inference calls, token storage, radio traffic, sensor wakeups or accounts.
No new polling loop, wake lock, durable event history or raw audio is needed.
These are code properties, not measured battery or latency gains. The charter's
<200 ms sensor-to-eligible-response and sub-milliwatt targets remain unmeasured;
a 180 ms decorative transition is unrelated to physical response latency.

## Staged tests and roadmap

1. Red: demonstrate the Kotlin constructor/copy contract defect with a test
   expecting rejection of `canActuate=true`, against the unchanged model.
2. Green: enforce read-only construction; preserve shared native fixtures and
   false actuation even when every prerequisite is available for review.
3. Implement local navigation/readiness and accessibility changes. Reuse the
   bounded tutorial contract and regenerate both platforms; no authority or
   physical adapter dependency enters the new UI code.
4. Hosted Android/iOS flows must reach checklist and privacy through Jump to,
   keep unknown state, reopen contextual help, and exit it. Android Back must
   dismiss nested UI before leaving; rotation/return must preserve truthful
   state. Large-text checks must keep Help and navigation usable.
5. Run full Python/native/C deterministic regressions and unsigned iPhone
   preflight. Retain screenshots and failures with run/commit provenance.

## Further features and required research

| Next feature | Smallest next research / acceptance gate |
| --- | --- |
| Background Protection Supervisor | Map Apple/Android suspension, permission loss, route loss, restart and expired evidence to truthful UNKNOWN/DEGRADED/PAUSED/RECOVERY_REQUIRED. ACTIVE needs fresh authorized independent observation. Measure real OS event timing and battery; no fabricated audio background mode. |
| Qualified device setup | Inventory an available owned endpoint, driver, route, format and independent measurement path under N2b/N3 before implementing an adapter. Keep discovery distinct from authorization. |
| Usable captions / controls / verified undo | Research exact supported endpoint capabilities, permissions and accessible media APIs, then test rejection without adapter calls and lineage-preserving observed results. |
| Accessible theme / localization | Inventory semantic colors and every string, test contrast with real OS modes, pseudo-localize and test RTL/large text before adding language/theme controls. |
| Exportable support report | Define an allowlist and consent preview; exclude raw audio, identifiers, tokens, and unverified physical claims. Research clipboard/share retention before export. |

This review does not qualify real-device audio, protection, background
availability, store acceptance, or cryptographic proof of physical isolation.

## Validation record

Pending implementation and hosted runs; replace this entry with observed
commit/run outcomes before marking the review ready.
