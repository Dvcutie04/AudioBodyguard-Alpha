# Simpler, picture-led onboarding — October 1, 2026

## Problem, goals and boundary

The owner finds the preview crowded and worries it discourages purchase. This is direct qualitative feedback, not a conversion study. Inspection found 21 welcome features with repeated availability labels, a two-connection summary repeated on every beginner screen, long examples, dense route introductions, and an extra confirmation page. The owner's Roku Settings photo is a visual reference for the menu layout; it is not evidence of a paired device. The personal photo is not a shipped asset.

Both iPhone and Android remain primary targets. Preserve all 39 routes and 345 numbered pictures, including TV, phone and approval steps. Default welcome: three benefits, one short preview notice, both connection stages, and one primary start action. Each beginner explanation has at most 20 words. Keep the complete feature catalog and help accessible on demand. Remove the redundant confirmation page and reduce manual return navigation after a completed pairing picture guide.

INFERENCE IS NOT REALITY. A completed guide is learning progress. It cannot discover hardware, grant permissions, link an account, authorize an adapter, verify a connection, activate protection, or establish audible output. The deterministic policy, cryptographic authority, capability leases, Intent Firewall, Physical Commit, isolated adapters, independent observation and auditable lineage remain required. Production qualification remains closed.

## Primary-source evidence matrix

Sources checked October 1, 2026. Living pages may change; dates below describe the evidence, not a new OS requirement. No community assertion is used as a requirement.

| Evidence | Established finding | Grade / limitations | AQSS use |
|---|---|---|---|
| [Apple, Writing for interfaces, WWDC22](https://developer.apple.com/videos/play/wwdc2022/10037/) | Define each screen's purpose, prioritize its essential information, and move other details elsewhere. | Primary design-team guidance, 2022; practical examples, not an AQSS trial. | Short action copy, help on demand, important status still visible. |
| [Apple onboarding HIG](https://developer.apple.com/design/human-interface-guidelines/onboarding) | Indexed official guidance supports brief prerequisite onboarding, safe interaction and skipping/revisiting tutorials. | Primary living guidance. Full page retrieval is JavaScript-only; indexed excerpts corroborate existing local research. No broader claim of a fresh full-page audit. | Keep Exit/replay and actual explorable tools. |
| [Google Material onboarding](https://m1.material.io/growth-communications/onboarding.html) | Benefit-oriented introductions emphasize a small number of important outcomes and a clear initial action. | Primary archived Material 1 guidance, not current Android policy or proof of conversion. Its animation advice is not adopted. | A static three-benefit summary followed by setup; no carousel, timer or compulsory slideshow. |
| [Nielsen Norman Group, Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Separate common tasks from secondary detail; staged disclosure can present sequential tasks one at a time. | Original professional usability guidance, 2006; qualitative and context dependent. | More features / Need help / Details controls; picture steps stay sequential. |
| [Sonos Arc setup](https://support.sonos.com/en-us/article/set-up-your-sonos-arc) | Short prerequisites lead into app-guided hardware setup; feature and troubleshooting details are separate. | Primary current product instructions, commercially interested; evidence is for Sonos, not AQSS compatibility. | Distinct TV/home-device and phone stages, model prerequisites before starting. |
| [Duolingo core-tab redesign](https://blog.duolingo.com/core-tabs-redesign/) | The design team compared coherent typography, hierarchy and spacing through prototypes and phone feedback. | Primary first-party product account, commercially interested; no transferable AQSS engagement gain. | Consistent picture/header/button hierarchy and real screenshot review on both platforms. |
| [Scheibehenne, Greifeneder & Todd, 2010](https://scheibehenne.com/ScheibehenneGreifenederTodd2010.pdf), DOI 10.1086/651235 | A choice-overload meta-analysis found substantial variation and no general average effect across the included conditions. | Peer-reviewed synthesis, author-hosted paper; older, heterogeneous consumer experiments, not phone setup. | Treat this user's crowding report as a design hypothesis; avoid universal “fewer choices sells more” claims. |
| [Android activity results](https://developer.android.com/training/basics/intents/result) | Framework result APIs remain available; Google recommends AndroidX result APIs. Result handling must account for recreation. | Primary implementation guidance, current; availability is not a store-approval finding. | Use the existing framework Activity shell for a small local result, validate route/expected step, preserve pending state. AndroidX migration remains an explicit future option. |

## Synthesis and alternatives

The selected quadrant combines benefit-led hierarchy, progressive disclosure, pictures with bounded local continuation, and a truthful preview boundary. External sources establish individual patterns. Their combination suggests lower reading burden and fewer navigation decisions; it does not prove enthusiasm, retention or sales. AQSS-specific work is the guarded continuation of learning state while physical state stays unverified. No originality, patentability or measured improvement claim is made.

A static welcome plus one-task setup is smaller than a new personalization service. An animated benefit carousel, fake discovery spinner, automatic physical pairing, mandatory account capture, scarcity message, purchase prompt and success confetti are unnecessary for this preview. Local guide completion may advance only the matching connection screen and an explicitly allowed pairing/linking route. Information helpers, voice guides, cancellations, unknown results and stale callbacks do not advance the connection journey. Phone-stage continuation must not skip its picture instructions.

Visible safety/compatibility notes and route applicability remain beside the relevant pictures. Model examples, explanatory examples and source links can be expanded. No reset, consent, account-approval or mismatch warning is removed to make the screen shorter. Real manufacturer-app approvals still occur outside this preview.

## Optimization and truthful states

Latency first: fewer default text rows and local callbacks; preserve stable scroll containers and pinned navigation. Battery next: no polling, radio discovery, telemetry, wake locks, continuous animation or background service. Storage/memory next: bounded catalog, transient disclosure flags and existing local bookmarks; no raw-photo/audio retention. Platform compliance: keep existing foreground permissions, native accessibility and official-app handoff boundaries. Sub-200 ms response, sub-milliwatt operation, reduced battery use and increased sales remain unmeasured goals.

ACTIVE, DEGRADED, PAUSED, RECOVERY_REQUIRED and UNKNOWN_PHYSICAL_STATE remain governed by evidence, not marketing or tutorial progress. This preview has no qualified audio connection and retains unknown physical state / inactive protection. Short labels summarize that fact; technical details remain available. New guide navigation must not mutate authority, coverage, capability, finality or adapter state.

The owner subsequently asked to dismiss the discouraging connection sign, clarifying “claiming connection.” The prominent orange “Not connected · Audio protection is not active” banner was removed from setup, and the phone screen gained a direct picture action.

On October 2, the owner supplied an Appetize screenshot and asked for no disclaimer text at all. The welcome now has one short action sentence, two visible connection steps and a three-benefit card headed “What we're building”; the yellow caveat line, repeated simulation labels and static warning paragraphs are removed from iPhone and Android. Picture instructions, official-app approvals and actual coverage/permission states remain accurate. The change is a presentation decision from owner feedback, not evidence of conversion gains or a connected device. Native walkthroughs check the warning text is absent while coverage still reports Unknown physical state and No output observation.

## Staged roadmap and test plan

1. Red/green: contract for three featured IDs, short explanations, six beginner screens, and allowlisted picture-continuation routes; reject unknown/duplicate routes and authority/status/command fields.
2. Native presentation: one concise preview notice, welcome-only two-stage overview, compact current-stage indicator, optional full catalog/help; show picture entries on both connection screens.
3. Guarded local continuation: test valid matching completion, stale target, unknown/information/voice route, duplicate result, cancelled exit and replay/restore. No connection-success field is introduced.
4. Picture presentation: retain all step actions, numbered highlights, surface labels, applicability and notes; fold secondary intro details; verify mismatch, resume, Back/Next/Close and large text.
5. Integration: iPhone Release XCUITest and Android walkthrough verify collapsed/expanded catalog, short welcome, both picture stages and completed/cancelled continuation. Inspect screenshots; regenerate shared content and run repository regressions and native contract/build checks.
6. Deliver simulator ZIP and Android APK from the exact passing commit. Simulator evidence does not qualify physical devices or establish App Store/Play readiness.

The smallest subsequent usability study asks new iPhone and Android users to identify the next action, distinguish planned controls from preview tools, reach both picture stages, recover a mismatched screen, and accurately report whether the device is verified connected. Measure reading/time, completion/abandonment, wrong actions and mistaken protection claims. Opt-in research can later evaluate engagement or purchase intent; no analytics collection is added here.
