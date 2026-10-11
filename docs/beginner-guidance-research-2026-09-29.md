# Beginner guidance: research, design and test plan

## Problem and boundary

The owner's first Appetize walkthrough found that the starting action, learning
order and feature availability were confusing. This is direct qualitative
feedback from one user, not a population study. Inspection confirmed that Home
led with technical coverage/readiness information and placed its tutorial entry
after other cards. The existing Home tutorial also skipped Sound and Settings.

Goal: make the first action obvious, explain what this preview actually offers,
and provide an optional five-step route through all pages on both platforms.
Tutorial completion is learning progress only. It cannot satisfy a readiness
check, authorize an adapter, supply output observations or change coverage.

## Evidence matrix (checked 2026-09-29)

| Source | What it establishes | Grade and limits | Design use |
|---|---|---|---|
| Owner's read-only walkthrough and current native source | Starting order and capabilities were unclear; tutorial entry was below status cards | Direct, current, reproducible screen structure; one person's experience, no quantified comprehension result | Move the starting action above technical status; explain availability |
| [Apple, Writing for interfaces, WWDC22](https://developer.apple.com/videos/play/wwdc2022/10037/) | Clear purpose, information hierarchy and anticipating the next question improve interface writing | Primary platform design guidance, published 2022, transcript retrieved; not an AQSS user trial | Plain-language page introductions and five explicit learning steps |
| [W3C, Consistent Help](https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html) | Repeated help belongs in a consistent relative location | Primary accessibility guidance; web criterion applied as a native design heuristic, not certification | Keep Help at the top of every page; beginner tour first in the topic list |
| [Android, Make apps more accessible (Views)](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views) | Text alternatives, meaningful labels, accessible controls and decorative-image handling | Primary, implementation-relevant official guidance; actual TalkBack usability still needs device testing | Labeled numbered buttons, 48dp Android controls and decorative glyphs |
| [W3C, Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html) | Persistent automatic moving/blinking content needs user control under the stated conditions | Primary accessibility guidance; no evidence that blinking improves this app | Use steady numbered markers and manual Next/Back; no repeating blink or auto-advance |
| [Android, ValueAnimator.areAnimatorsEnabled](https://developer.android.com/reference/android/animation/ValueAnimator#areAnimatorsEnabled()) | System animator preference is available to gate animation | Primary API documentation; no measured energy guarantee | Retain only the existing finite 180ms transition when allowed |

Apple's current onboarding HIG URL returned a JavaScript-only page in retrieval;
it is not treated as newly verified evidence. Existing tutorial research remains
in `docs/tutorial-research.md`. No community assertion is being used as a platform
guarantee. These independent pieces support the design; none proves its usability.

## Competing designs and synthesis

- **Mandatory launch wizard:** clear order but blocks exploration and can imply
  real device setup. Rejected for this read-only preview.
- **Continuously blinking numbered buttons:** conspicuous but distracting, adds
  repeated work and does not explain feature availability. Rejected.
- **Selected four-part design:** prominent optional start, availability summary,
  ordered contextual tour, and consistently placed replay/help. This is an AQSS
  composition of established patterns, not a claim of novel intellectual property.

The inferred benefit is lower first-use uncertainty. Measure this in a subsequent
first-use trial: can a novice find the tour without coaching, describe what works
today, finish/exit/replay it, and locate topic help? No improvement percentage or
completion-time result is claimed before that trial.

## Smallest architecture

Extend the existing bounded, presentation-only tutorial contract with one topic:

1. Home: meet the preview; no monitoring or audio changes.
2. Devices: understand requirements; pairing is not available here.
3. Sound: explore descriptions of unavailable controls.
4. Insights: explicitly invented graph and accessible text values.
5. Settings: choose a theme; find planned features and replay/topic help.

Home presents `Available now`, `Preview only` and `Planned` groups, plus numbered
step shortcuts with small native illustrations. The selected tutorial number and
text identify progress; color is supplementary. Back/Next/Close remain under user
control. Done shows a local tour-finished message and replay action, never an
activation or protection message. Jump to also includes Start here.

No service, account, permission, network request, audio recording or tutorial
analytics is added. Theme remains the only durable preference. Tour state is
temporary (Android saves it in instance state for configuration recreation).
No continuous animation, timer or polling is introduced. Native vector glyphs
avoid new image downloads. These are structural bounds, not measured battery,
memory or sub-200ms response claims.

The Android guide reattaches its highlight after an example card is redrawn, so
an interactive chart does not silently lose its contextual target. Theme changes
retain tutorial position. Existing deterministic authority/physical boundaries
and rejecting production factory are unchanged.

## Staged tests and evidence

1. Red: new contract test fails against the original first topic (`home`).
2. Green: generated Swift/Kotlin share the five ordered targets; presentation-only
   validation, all six unknown prerequisites and synthetic labels still pass.
3. Native UI: fresh-launch entry, step order, Back, Close, direct step shortcut,
   interactive example, theme change, Done, replay and origin restoration.
4. Accessibility/lifecycle: large text with reachable Next/Close, existing rotation
   and foreground-return checks; manually inspect screenshot artifacts.
5. Full deterministic regressions, Swift package tests, Android unit/build checks,
   C11 normal/sanitizer tests, simulator/emulator UI checks and iPhoneOS preflight.

Simulator screenshots and green tests establish only the tested presentation
behavior. They do not prove acoustic output, hardware qualification, protection,
VoiceOver/TalkBack usability or comprehension by new users.

Final results are recorded in the pull request and its linked CI runs.
