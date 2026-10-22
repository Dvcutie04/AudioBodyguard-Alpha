# Sound-check permission settings — October 21, 2026

Version 0.15 improves the dedicated Live sound check after microphone
permission is denied. The current message asks users to find the app in phone
Settings themselves. A visible “Open app settings” action will take them to
the operating system's page for this application.

## Research and selected design

| Primary source | Application |
| --- | --- |
| [Android application details settings](https://developer.android.com/reference/android/provider/Settings#ACTION_APPLICATION_DETAILS_SETTINGS) | Launch the public action with this app's package URI. The API produces no permission result and can have no matching Activity, so handle launch failure. |
| [Apple openSettingsURLString](https://developer.apple.com/documentation/uikit/uiapplication/opensettingsurlstring) | Use the public app-specific Settings link and handle an unsuccessful URL opening. |

The design combines an explicit navigation action, a fresh native permission
query when the screen returns, and the existing explicit Start gate. Opening
Settings does not authorize capture. Returning with access granted does not
acquire a microphone lease, create a recorder or begin a meter run. The user
must press Start again, and the normal permission, foreground and ownership
checks still run at that point.

Permission guidance remains active from an attempted permission request until
the next granted Start. While guidance is active, resume refreshes the denied
shortcut and status from actual OS permission. This also covers permission
callbacks invalidated when a consent dialog or another app interrupts the
screen. An old URL-opening completion cannot overwrite a newer attempt or
resume. Cleanup failure remains blocking and keeps its warning.

The shortcut appears with permission guidance, preserving the ordinary idle
and running layouts. A failed Settings launch gives a manual fallback. No
private Settings URL, background polling, dependency, new permission, network
request or persisted data is introduced. Additional work is limited to a
permission query on resume while guidance is active and an explicit Settings
launch. This is a design policy, not a measured handset performance result.

The increment covers the dedicated meter on Android and iPhone. Voice and
camera flows retain their existing behavior. No Settings action can clear a
microphone cleanup block or change the physical-control boundary.

## Verification contract

Regression checkpoint `3e2cf3cf2a72e1df2f58de55ac2270f5525e8314` adds native
tests and workflow triggers before the production shortcut or version change.
The tests must fail on 0.14's missing shortcut after real permission denial.

Android run `39718399433`, job `119625928365`, compiled and then failed with
`Missing tap target: Open app settings` after the denied/empty-recap checks.
iPhone run `39718399511`, job `119625928689`, compiled and passed its package
tests, then reported the missing Settings shortcut in the denied meter test.
The six-test UI stage had two failure records for that one behavior: the
explicit missing-control assertion and its thrown sentinel error. The other
five UI tests passed; the granted-input stage was skipped after this expected
failure. These are runtime observations before any production change.

Android opens the actual Settings application, requires this app's name and
Permissions row, and records the foreground Settings route and sound-check
return history. Android 16 redirects the public details intent to its internal
SPA Activity, so the observed app page establishes the destination rather than
requiring the original intent to survive that redirect. A return
with access denied must remain off. Another visit grants the real permission
while Settings is foreground; returning must still show Start and no input,
with no running microphone app-op. Only a subsequent deliberate Start may
produce samples. Denied attempts must leave recaps empty.

iPhone opens the actual app-specific Settings page, returns while still denied,
then uses the real microphone switch to grant access. It must remain idle after
returning, including an OS-induced relaunch. The test restores denied access
for the remaining denied-permission tests. Permission-switch values are
observed before continuing; grid coordinates and guessed control positions
are not used. Screenshots of the app's denied and granted return states are
kept as CI evidence.

Existing sound, voice, photo, camera, timeout, ownership, cleanup, recap and
physical-control contract tests remain required. Exact red/green run results,
source identity, APK version/hash and visual review belong to the draft PR.
Simulator/emulator permission behavior is separate from handset audio accuracy,
TV pairing, continuous protection or signed iPhone distribution.
