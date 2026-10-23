# Share installed build details

October 22, 2026. Scope: version 0.18, stacked on the completed 0.17 build.

Phone testers can already inspect their installed version and build. This
increment lets them hand the same small preview to their phone's native share
sheet with an explicit Share build details action inside Build details.
Cancel returns to that preview; Back still returns to ordinary Settings.

The entire payload is four lines: Audio Bodyguard, Platform, Version, Build.
Android identifies its platform as Android; the shared Apple app identifies
its platform as iPhone/iPad. Version and build come from the installed
package/main bundle, retaining the existing Unavailable fallback. The preview
and shared string use the same metadata snapshot. The reporting instruction
is outside the shared payload.

There is no log collection, permission query/request, audio, recognized text,
photo hint, IP/model identifier, account, device identifier, timestamp,
connection/protection claim, clipboard write, local report file, background
work, network client or new dependency in this feature. The full Private
support report remains planned.

## Research and design decision

Research preceded production edits. Primary sources:

| Source | Finding and consequence |
| --- | --- |
| [Android sharing guide](https://developer.android.com/develop/ui/compose/sharing/send?hl=en) | ACTION_SEND with text/plain and EXTRA_TEXT is the text handoff; createChooser requests the system Sharesheet. No file URI, binary stream, receiver preselection or grant flag is needed here. |
| [Apple UIActivityViewController](https://developer.apple.com/documentation/uikit/uiactivityviewcontroller) | The controller takes explicit activity items and offers system activities. Use one String. Present modally on iPhone and anchor a popover on iPad. |
| [Apple completion handler](https://developer.apple.com/documentation/uikit/uiactivityviewcontroller/completionwithitemshandler) | Dismissal/completion is a UI result; it cannot establish delivery or recipient retention. Reset presentation state without claiming that a report was sent. |
| [Apple popover source view](https://developer.apple.com/documentation/uikit/uipopoverpresentationcontroller/sourceview) | Anchor the iPad popover to the visible Share control. Test the shipped tablet device family as well as iPhone. |
| [Apple SwiftUI controller bridge](https://developer.apple.com/documentation/swiftui/uiviewcontrollerrepresentable) | A small UIKit presenter can participate in the existing SwiftUI help sheet while preserving the iOS 15 deployment target. |
| [Apple WWDC22 sharing](https://developer.apple.com/videos/play/wwdc2022/10095/) | ShareLink adoption starts with iOS 16; keeping one UIKit path avoids an extra availability-dependent behavior for the app's iOS 15 minimum. |

The native sheet may offer Copy or messaging services. Those activities are
chosen by the user; their retention is outside AQSS control. AQSS does not
select a person, transmit to a service itself, copy automatically, promise
delivery, or claim to retract shared text. A custom upload/report service
would need a separate privacy, consent and data-retention design.

The small native handoff preserves the charter's priorities: no polling,
sensor work, persistent report storage or added library. Work occurs only
after a tap. No latency, battery, memory or physical-safety measurement is
claimed by this design choice.

## Native red-first checks

Add tests while production remains exactly 0.17. Android must first read
actual installed metadata, reach Build details and fail at the missing Share
build details tap target. iPhone must reach the same screen and fail its
explicit missing-action sentinel. No fabricated share result is acceptable.

After the intended red results, test the actual system share sheet:

- Android: cancel with Back, reopen, select a separate test-only receiver,
  compare the received ACTION_SEND text with the four-line preview and the
  independently queried installed version/build, reject stream/URI/extra
  intent data, and return through Build details and Settings. Check that
  microphone app-ops are not running. The receiver never ships in the APK.
- iPhone and iPad: cancel the native sheet without changing the isolated
  Simulator pasteboard, reopen, select the real system Copy activity, compare
  the resulting clipboard text exactly with the preview and compiled
  Info.plist metadata, and return through Settings to unverified Home.
  Pasteboard access exists only in the UI-test runner, which clears its
  synthetic clipboard fixture. The application never accesses it.
- Preserve the complete native permission/input/photo/lifecycle regressions,
  core suites, opening artwork, closed production factory and physical gates.

The draft PR will record exact red reasons, final source/tree, native cases
and immutable artifact identity. Native share/copy checks in isolated
Simulators/emulators are separate from actual handset compatibility,
recipient delivery, signed iPhone distribution and N2b-N5 qualification.


## Red results and implementation

Red-only source 64d6b060a9f9d49a02c43c15610d4be38b86f572, tree
14dfc53b6e0a5d4c312124b67f552f5632de51c2, kept both production apps and
their version metadata at 0.17.

- Android run 39875622079, job 120160388751 compiled, passed lint, queried
  actual installed metadata, opened Build details and failed exactly at
  Missing tap target: Share build details.
- iPhone run 39875622155, job 120160389931 compiled, used expected metadata
  from the compiled app Info.plist and failed Missing Share build details
  action plus its AQSSBuildShare Code=2 sentinel. All six prior cases in that
  first UI group passed, including installed metadata and native photo
  selection. The separate speech-Settings job passed.
- The same run's iPad job 120160389205 compiled and failed the same missing
  Share action/sentinel after reaching Build details on the actual Simulator.

Production edits began only after all three expected native red reasons were
confirmed. Android adds text-only ACTION_SEND through createChooser to its
existing information dialog. Its ordinary help dialogs retain their existing
behavior. iPhone/iPad reuses the existing Settings explanation sheet, with an
optional immutable share string and a small UIKit presenter anchored to the
visible Share button. A coordinator suppresses repeat presentation and resets
the control after cancellation/completion. Only the UI-test runner reads or
writes its synthetic pasteboard.

The Android live-input version is 0.18-share-build-details-live-input, code
18. The default Apple release is 0.18.0, first build 1; runtime metadata lookup
still honors future signing/distribution overrides. Final source identity,
native results, screenshots and APK verification are recorded in draft PR #50
before delivery; none of these software checks qualifies physical output.

The first implementation source fbd8e4019b3ed94deab1f7139a758e52b745275e
passed core CI and the unsigned archive. Its iPad share job 120164157482 in
run 39876772412 opened the real native popover, whose captured accessibility
hierarchy showed Copy as a Cell with a nested StaticText. The initial test
incorrectly queried Buttons, so it failed before cancellation or clipboard
comparison. The observer now taps the observed Copy cell. The exact payload,
native cancel/reopen, enabled Share control, Settings return and clipboard
assertions are retained. Application code is unchanged by this test correction.


Android's first implementation run 39876772314, job 120164156545, showed the
exact four-field text in the native Sharesheet and preserved the preview on
cancel, but its receiver record was unavailable. The initial receiver lived
inside the UI observer's own package. [Android's instrumentation contract](https://developer.android.com/reference/android/content/Context#startInstrumentation(android.content.ComponentName,%20java.lang.String,%20android.os.Bundle))
says starting instrumentation kills/restarts its target application.
HierarchyProbe targets its own observer package, so re-observing that receiver
could interrupt the very Activity being checked. This explains why returning
to the underlying Build details view was not sufficient handoff evidence.

The receiver now lives in a separate test-only APK/package, with no dependency
from the delivered application. It writes the actual Intent record before
displaying a native receiver checkpoint. The observer requires that checkpoint,
the exact received text and receiver package, reads and retains the raw record,
checks text/MIME/stream/URI boundaries, and explicitly returns to Build
details. No retry or weaker payload assertion replaces receipt evidence.
Both observer and receiver package markers are rejected by CI and the final
APK validator if found in delivered DEX files. Application feature code
remains unchanged from fbd8e4019b3ed94deab1f7139a758e52b745275e.

The next run (source 58ffbb32e8c44eec86f22bc5923dbe7c0d9f2ccc) proved
Android's separate receiver opened with the exact four-line text. Its captured
hierarchy exposed the themed button as RETURN TO BUILD DETAILS, while the
test required the mixed-case label. The test-only receiver now disables
automatic capitalization for that button; payload and package checks remain
exact. On iPad, the native share popover opened, but a normalized app-edge
cancel tap did not dismiss it. The captured window is inset from that edge.
[Apple's coordinate API](https://developer.apple.com/documentation/xcuiautomation/xcuielement/coordinate%28withnormalizedoffset%3A%29)
uses the queried element's frame; [popover presentation](https://developer.apple.com/documentation/uikit/uimodalpresentationstyle/popover)
supports dismissal by tapping outside it. The revised observer finds the
visible Build details preview, requires its tap point to be outside the
actual native popover frame, and taps there. It fails immediately if cancel
does not close the sheet, retaining the hierarchy and a failure screenshot.
Neither correction changes the application feature or relaxes cancel,
reopen, exact handoff, enabled-control or Settings-return assertions.
