# Branded startup artwork: bounded research and test plan

## Android visibility correction — October 18, 2026

David reported that the installed Android live-input app did not visibly show
the expected opening poster. The original implementation removed the artwork
after one drawn frame and a 120 ms fade. That transition could satisfy the
first-frame implementation while failing the user's readable-branding goal.

Android now uses the exact newly supplied `IMG_5372.jpeg`, including Audio
Bodyguard and Silicon Workforce, without editing the image. Its SHA-256 is
`8f15b1e42a9cf067a7458973edbe43aa9a975b82f728d5ccc47d180bcb50307c`.
The existing iOS artwork retains the September source described below.

The in-app opening layer is visible for 1,500 ms after its first drawn frame;
a tap dismisses it immediately. Backgrounding dismisses it and removes its
callback. Restoring an Activity skips the opening layer. Hidden Home/tutorial
controls do not receive input while the artwork covers them. The title and
credit respect system-bar and display-cutout insets; all source regions retain
their aspect ratio. The layer reports no loading progress, connection,
microphone activity or protection. This short product branding interval is an
explicit correction to September's no-minimum-duration decision.

[Android's splash documentation](https://developer.android.com/develop/ui/views/launch/splash-screen)
was rechecked October 18: the system splash remains an icon/background window
with constrained optional branding, dismissed around the app's first frame.
The complete poster therefore remains inside the existing Activity. No new
Activity, library, permission, sensor or network call is added.

The live-input build is version code 3, `0.3-opening-artwork-live-input`, with
the existing `.liveinput` application ID. CI debug signatures are ephemeral;
if this build has a different signing certificate from an installed test APK,
Android requires uninstalling that old test app before installing the new one.
Only appearance/tutorial preferences are retained by this test app; raw audio
is never saved. A matching application ID alone does not prove update
compatibility.

Verification requires an actual emulator screenshot during the opening,
another after it, Android compilation/lint and the existing microphone
lifecycle checks. This is presentation verification, not acoustic or protection
qualification.

## Problem and truth boundary

Show the owner's supplied Audio Bodyguard artwork while the read-only native shells start on iOS and Android. Preserve the white background, cyan/magenta-shadowed black title, purple/black tribal rose, and the **Silicon Workforce** credit from the source image. A launch visual reports no physical state. It must not delay an eligible response, suggest active protection, request microphone access, or change the closed handoff and production gates.

At the September checkpoint both asset copies were byte-for-byte identical to the supplied `IMG_5169.jpeg` (SHA-256 `6d67c4c4cfaa7dcbbaa50fc5e05c0fd574e884b62f2c2a62d58538a728402048`). The user wrote “silicone workforce”; the photograph itself reads “Silicon Workforce,” which this implementation preserves. Android's October correction above supersedes its source and timing; the remaining September design history is retained below.

## Source and evidence matrix

| Source | Establishes | Authority / recency / reproducibility / bias | AQSS consequence |
| --- | --- | --- | --- |
| [Apple, Specifying your app’s launch screen](https://developer.apple.com/documentation/xcode/specifying-your-apps-launch-screen/) | A launch storyboard can be registered for the app; use UIKit-only static views without code connections. | First-party platform specification; viewed 2026-09-28. Build on a macOS runner verifies this project's configuration. | Static white storyboard and asset catalog image, without a timer or activity simulation. |
| [Apple, TN3118 launch-screen debugging](https://developer.apple.com/documentation/technotes/tn3118-debugging-your-apps-launch-screen) | Static launch imagery should originate from the target's asset catalog as JPG/PNG. | First-party troubleshooting guidance; viewed 2026-09-28. Simulator visual review still needed for viewport differences. | Add the exact JPG to `Assets.xcassets`; clip three proportionally scaled views of the same image for the requested arrangement. |
| [Android, Splash screens](https://developer.android.com/develop/ui/views/launch/splash-screen) | Android 12+ system splash exposes an icon, opaque background and optional bottom branding image; dismissal is tied to the first app frame. It does not offer an arbitrary full-portrait composition. | First-party platform documentation, updated 2026-09-22. Emulator can reproduce it; OEM launch motion may vary. | White system splash with a small rose cue in the icon slot, then full artwork in the same activity until the first drawn frame. No separate splash activity or fixed loading timer. |
| Owner-supplied `IMG_5169.jpeg` | Exact title, rose, credit, palette and layout intent. | Direct product input; highest authority for requested appearance, not evidence of startup correctness. | Preserve pixels and order. Do not invent logo geometry or an audio status. |

## Synthesis and alternatives

The iOS launch storyboard and Android's starting-window API have different layout abilities. The original AQSS adaptation is to share the **same unmodified image** and position three exact source regions on white: title at the top, rose in the middle, credit at the bottom. The image's width is bounded by both screen width and available height, so no region needs stretching or horizontal clipping. iOS composes three clipped image views in its static launch storyboard. Android uses a small purple/black vector rose cue in its mandatory system splash, followed by the supplied artwork composed in three regions in the existing activity; the layer fades away over 120 ms after it has drawn and the read-only page has been built. The vector is a visual cue, while the artwork retains the exact logo. The fade is a transition, not a simulated loading duration. The Android view has a spoken accessibility description and is not reinstated on configuration restoration.

Placing the entire poster into Android's system icon alone would crop its title and credit. A dedicated second splash activity would duplicate the system splash on Android 12+. Stretching the portrait image to fill every device would distort the title and rose. A single centered aspect-fit image would leave the footer too far above the bottom on tall phones, so the three display regions are positioned separately from the same asset. Measuring visibility on representative screen sizes remains empirical debt.

This presentation change uses no polling, sensors, persistence, permission, network or raw audio storage. It adds about 216 KB of JPG to each native build and no new runtime dependency. Startup duration follows platform startup and first render; no launch screen may be treated as proof of audio processing, observation, or protection.

## Staged verification

1. Validate the copied binary digests, asset catalog and storyboard references, Android resource/theme identifiers, and XML syntax.
2. Compile an unsigned iOS Simulator `.app` and Android debug APK in hosted CI; assert the iOS app contains `LaunchScreen.storyboardc` and the Android APK contains the startup asset/theme.
3. Cold-launch on an iOS Simulator and Android emulator. Inspect the full artwork (title, rose, credit) and its transition into Home, including a narrow portrait and a rotated or restored Android configuration.
4. Keep the read-only UI smoke and deterministic software regressions green. Confirm Home still says **Unknown physical state / No output observation** and the rejecting production factory is unchanged.

Simulator launch review is presentation evidence only. A signed iPhone install and physical acoustic observation remain separate gates.
