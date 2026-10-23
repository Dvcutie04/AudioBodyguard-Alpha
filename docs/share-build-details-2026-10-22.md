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
