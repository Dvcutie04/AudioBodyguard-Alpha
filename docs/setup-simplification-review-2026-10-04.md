# Simpler setup and three content reviews — October 4, 2026

Home now presents the supplied head image, one connection status, and the connection guide. Status explanations, planned features, readiness, references and troubleshooting remain behind explicit controls. Repeated coverage cards and the default feature catalogue are removed from Home. No existing useful setup route is deleted.

The supplied purple tribal rose appears in the root Help control, tutorial Exit Home, setup Back to Tutorial/Close, input-tool Close and the native menu dismissal controls. Background-removal derivatives are now packaged as transparent PNGs on both platforms; the original uploads are retained. The head is grayscale while connection evidence is unavailable. Color and a gentle animation require the validated coverage state to be ACTIVE; completing pictures cannot change that state. Animation respects inactive/background state and reduced-motion settings.

## Pass 1 — chronology and primary-source scope

Read all 45 route sequences, checking the TV/phone surface, menu names, highlight and next action. The final catalogue contains 389 numbered illustrations. Added installation pictures before primary SmartThings, ThinQ, Google TV and VIZIO phone pairing. Restored ThinQ's same-network confirmation and Next before choosing the discovered TV. Kept PIN entry and its confirmation as separate pictures. Added the VIZIO account sign-in required by its current Mobile documentation.

New iPhone, Pixel and Galaxy Wi-Fi instructions use separate menu paths. Pixel's Network & internet → Internet is not assigned to every Android phone. iPhone installation pictures say App Store/Get; Android pictures say Google Play/Install. Each short instruction remains at most 30 words.

| Primary source | Reviewed instruction / qualification |
|---|---|
| [Apple Wi-Fi](https://support.apple.com/en-us/111107) | Settings → Wi-Fi; choose network; password if requested; blue checkmark. |
| [Pixel Wi-Fi](https://support.google.com/pixelphone/answer/2819519?hl=en) | Network & internet → Internet; network; Connected. Some steps need Android 11+. |
| [Galaxy Wi-Fi](https://www.samsung.com/ca/support/mobile-devices/connect-your-samsung-galaxy-to-the-internet/) | Connections → Wi-Fi; network/password/Connect; Canadian model documentation. |
| [Samsung SmartThings pairing](https://www.samsung.com/us/support/answer/ANS10005262/) | Same Wi-Fi and Samsung account; location/device-type discovery; distinct TV OK and PIN variants. |
| [Samsung assistant setup](https://www.samsung.com/us/support/answer/ANS10006871/) | SmartThings authorization; Message Alexa → Smart Home → Smart Home Skills; conditional discovery. |
| [LG ThinQ registration](https://www.lg.com/us/support/help-library/lg-thinq-how-to-register-your-tv-with-lg-thinq--20153095986130) | App installation, Select Device, same-network Next, TV list, PIN/Next and optional Link/Skip. |
| [Google TV remote](https://support.google.com/googletv/answer/11136134?hl=en) | TVs nearby, actual television, displayed code, Pair; checked Android and iPhone tabs. |
| [Google TV initial setup](https://support.google.com/googletv/answer/10050221?hl=en) | Separate older Google Home flow and newer camera flow; actual TV screen selects the path. |
| [Google Home linking](https://support.google.com/googlehome/answer/9159862?hl=en) | Add → Device → Add a different way → available manufacturer service; authorization stays in official app. |
| [VIZIO Mobile](https://www.vizio.com/en/vizio-mobile-app) | Same network, four-digit pairing, required VIZIO account and Account-tab assistant linking. Replaced the obsolete /en/mobile URL. |
| [VIZIO account link](https://www.vizio.com/en/vizio-account/link-your-tv) | Extras → VIZIO Account; Account/Devices & TVs/Add TV; QR or six-digit account code. |

Existing model-specific source qualifications and the other primary references are recorded in [the October 1 route audit](onboarding-picture-audit-2026-10-01.md) and the shared catalogue. They remain required: VIDAA U5 evidence is for 43A6GV; Philips button combinations apply to the listed remote/model family; Roku/Fire/Google menus must match the actual platform. Generic provider options are conditional on the provider being present. A working source link is not proof of hardware compatibility.

## Pass 2 — system choices and cross-references

TCL, Hisense, Philips and Insignia now require an explicit platform choice. Child system groups are omitted from the general brand list and nested under their brand in the offline companion. Google Home/Alexa routes opened from a tutorial are intersected with the chosen TV system's route list. Samsung instructions cannot appear as the recommended Google Home route after selecting TCL Google TV. An empty intersection explains that there is no documented route for that combination.

VIZIO has separate Google Home and Alexa sequences, with the combined route retained under additional options. Phone Wi-Fi pictures do not advance TV pairing or claim a successful connection. Every group that opens Roku TV information includes the Roku phone route so a rotation can restore the handoff.

Back uses the previous location, including its disclosure state, within setup and the previous visited page within the app. Closing setup returns directly to its caller. Exit Home is an explicit shortcut that remembers the exact tutorial step and choices; Back to Tutorial resumes that snapshot. Starting a different tutorial clears the old paused snapshot. Returning to Home through Exit Home preserves the previous app page for page Back.

## Pass 3 — picture order and generated consistency

Checked every final step's screen, instruction, surface, action and highlight against its route, plus all route/source/group references. Native Swift and Kotlin catalogues and the offline HTML are generated from the same JSON. Generator parity, focus bounds, bounded instructions, source allowlist, Roku restoration, phone menu separation, installation and ThinQ confirmation regressions pass. The full local suite passes **1,840 tests and 19 subtests**; shell syntax and diff whitespace checks pass.

Every guide step renders its own numbered schematic. No photographed TV menu from another brand is inserted. Roku uses its documented left-menu/right-panel arrangement; the documented Philips profile menu uses the upper-right position. The supplied head and rose are interface artwork, never instructional TV photos.

These are labelled illustrations, not verified photographs of every model or firmware. Exact hardware/photo fidelity remains unverified without the physical model, country, firmware and official app version. Native build/walkthrough/screenshot evidence is reported separately for the delivered commit in draft PR #32. The preview has no verified physical TV connection or audio protection.

## Final sweep — transparent artwork

The owner supplied IMG_5234.jpeg as the rose-button presentation reference and IMG_5227.jpeg as the isolated head reference. Image-edit mode with a transparent background produced the cutouts; no instructional TV/phone picture was replaced with generated artwork.

| Artwork | Native PNG copies | Alpha inspection |
|---|---|---|
| Purple tribal rose | iOS `TribalRose.imageset/TribalRose.png`; Android `drawable-nodpi/tribal_rose.png` | RGBA, 1202 × 1308; all four corner pixels have alpha 0. |
| Humanoid head | iOS `ConnectionHead.imageset/ConnectionHead.png`; Android `drawable-nodpi/connection_head.png` | RGBA, 1287 × 1222; transparent margin around the head, neck and shoulders; all four corners have alpha 0. |

Both color and grayscale head states render the same PNG. Native saturation filters change color without replacing its alpha channel. The iOS rectangular image mask and outer glow were removed. Both platforms fit the complete rose inside the control instead of cropping its tip or curls. The ordinary button surface remains, as requested in the presentation reference.

The first final native run passed both walkthroughs, but its screenshot review caught an iOS header overflow beside the long Back to Tutorial label. The step counter and introductory label now allow their full vertical height and have layout priority, allowing the return label to wrap when needed. The existing TCL/Google Home walkthrough checks that the two-digit step counter stays inside the screen and does not overlap the return button. Final screenshots and delivered packages are taken from the subsequent successful revision.

Final rose edit prompt: preserve the purple/lilac/black tribal design, proportions and ribbon shapes; clean the alpha matte, white background residue and detached speckles; preserve fine curled strands; leave transparent margins and interior gaps; add no background, frame, text, UI or shadow.

Final head edit prompt: extract the supplied IMG_5227 head, neck and small shoulder silhouette; replace the white background and right border with alpha; preserve the robot face, clear cranium and cyan/blue/pink/violet/warm-yellow lights; add no new facial features, background, halo, shadow or detached speckles; retain transparent margins for both color and grayscale use.

The final instruction sweep again checks all 45 routes / 389 steps against the already-reviewed menu-family scope, chronological highlights and route/source references. Phone menus, conditional assistant choices and native App Store/Google Play labels remain separate. Previous-page history and exact tutorial resume are rechecked by the native walkthroughs for the delivered commit; this does not establish physical hardware compatibility.

## Larger roses and connected Appetize demonstration

The shared rose control now renders at **52 × 68 points/dp**, twice its former 26 × 34 size, on every page and sheet that uses it. Four white silhouette offsets of 0.6 points/dp at 40% opacity create a narrow outline around the transparent artwork. The source PNG, interior transparency and color head asset remain unchanged. Normal and accessibility-sized text retain the same button labels and navigation actions.

A separate `AQSS_CONNECTED_DEMO` compilation mode, restricted to `targetEnvironment(simulator)`, opens directly on Home with the full-color gently animated head, **Connected** beneath it and a small **Appetize demo** label. It does not synthesize observations or change coverage, capabilities, authorization or physical readiness. Expanded status still reports Unknown physical state and No output observation. Starting and finishing guides does not verify a device. Animation remains foreground-only and respects Reduce Motion.

The connected package has its own Simulator bundle identity (`com.aqss.bodyguard.prototype.demo`), display name (Audio Bodyguard Demo) and `CONNECTED_UI_DEMO` metadata marker. Ordinary builds retain the grayscale head and Connection not verified text without ACTIVE evidence. The workflow verifies both ordinary native navigation/layout and the connected demonstration, then produces a separate ARM64 `.app.zip` for each presentation. The dedicated connected test also checks previous-page Back and exact tutorial resume while the real readiness status remains unverified.

The first connected screenshots confirmed the background-free colored head and enlarged outlined rose, and caught a wrapped Help label in the iOS Home header. The short Help label now keeps its full horizontal size, while the brand text can shrink within one line. Longer tutorial return labels still wrap when necessary so the chronological step counter remains visible. Xcode omitted the custom demo metadata from its generated plist; the unsigned Simulator packaging step now inserts and validates the marker explicitly before creating the ZIP.
