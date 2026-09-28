# Branded startup artwork: bounded research and test plan

## Problem and truth boundary

Show the owner's supplied Audio Bodyguard artwork while the read-only native shells start on iOS and Android. Preserve the white background, cyan/magenta-shadowed black title, purple/black tribal rose, and the **Silicon Workforce** credit from the source image. A launch visual reports no physical state. It must not delay an eligible response, suggest active protection, request microphone access, or change the closed handoff and production gates.

The asset copies are byte-for-byte identical to the supplied `IMG_5169.jpeg` (SHA-256 `6d67c4c4cfaa7dcbbaa50fc5e05c0fd574e884b62f2c2a62d58538a728402048`). The user wrote “silicone workforce”; the photograph itself reads “Silicon Workforce,” which this implementation preserves.

## Source and evidence matrix

| Source | Establishes | Authority / recency / reproducibility / bias | AQSS consequence |
| --- | --- | --- | --- |
| [Apple, Specifying your app’s launch screen](https://developer.apple.com/documentation/xcode/specifying-your-apps-launch-screen/) | A launch storyboard can be registered for the app; use UIKit-only static views without code connections. | First-party platform specification; viewed 2026-09-28. Build on a macOS runner verifies this project's configuration. | Static white storyboard and asset catalog image, without a timer or activity simulation. |
| [Apple, TN3118 launch-screen debugging](https://developer.apple.com/documentation/technotes/tn3118-debugging-your-apps-launch-screen) | Static launch imagery should originate from the target's asset catalog as JPG/PNG. | First-party troubleshooting guidance; viewed 2026-09-28. Simulator visual review still needed for viewport differences. | Add the exact JPG to `Assets.xcassets`; use aspect fit so neither title nor footer is cropped. |
| [Android, Splash screens](https://developer.android.com/develop/ui/views/launch/splash-screen) | Android 12+ system splash exposes an icon, opaque background and optional bottom branding image; dismissal is tied to the first app frame. It does not offer an arbitrary full-portrait composition. | First-party platform documentation, updated 2026-09-22. Emulator can reproduce it; OEM launch motion may vary. | White system splash with supplied asset in the icon slot, then complete artwork in the same activity until the first drawn frame. No separate splash activity or fixed loading timer. |
| Owner-supplied `IMG_5169.jpeg` | Exact title, rose, credit, palette and layout intent. | Direct product input; highest authority for requested appearance, not evidence of startup correctness. | Preserve pixels and order. Do not invent logo geometry or an audio status. |

## Synthesis and alternatives

The iOS launch storyboard and Android's starting-window API have different layout abilities. The original AQSS adaptation is to share the **same unmodified image** and display it with aspect fit on white. iOS uses its launch storyboard. Android uses a small purple/black vector rose cue in its mandatory system splash, followed by the complete supplied artwork in the existing activity; the layer fades away over 120 ms after it has drawn and the read-only page has been built. The vector is a visual cue, while the full artwork retains the exact logo. The fade is a transition, not a simulated loading duration. The Android view has a spoken accessibility description and is not reinstated on configuration restoration.

Placing the entire poster into Android's system icon alone would crop its title and credit. A dedicated second splash activity would duplicate the system splash on Android 12+. Stretching the portrait image to fill every device would distort the title and rose. Aspect fit instead permits white margins on taller or wider devices; measuring visibility on representative screen sizes remains empirical debt.

This presentation change uses no polling, sensors, persistence, permission, network or raw audio storage. It adds about 216 KB of JPG to each native build and no new runtime dependency. Startup duration follows platform startup and first render; no launch screen may be treated as proof of audio processing, observation, or protection.

## Staged verification

1. Validate the copied binary digests, asset catalog and storyboard references, Android resource/theme identifiers, and XML syntax.
2. Compile an unsigned iOS Simulator `.app` and Android debug APK in hosted CI; assert the iOS app contains `LaunchScreen.storyboardc` and the Android APK contains the startup asset/theme.
3. Cold-launch on an iOS Simulator and Android emulator. Inspect the full artwork (title, rose, credit) and its transition into Home, including a narrow portrait and a rotated or restored Android configuration.
4. Keep the read-only UI smoke and deterministic software regressions green. Confirm Home still says **Unknown physical state / No output observation** and the rejecting production factory is unchanged.

Simulator launch review is presentation evidence only. A signed iPhone install and physical acoustic observation remain separate gates.
