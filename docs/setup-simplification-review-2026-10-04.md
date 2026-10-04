# Simpler setup and three content reviews — October 4, 2026

Home now presents the supplied head image, one connection status, and the connection guide. Status explanations, planned features, readiness, references and troubleshooting remain behind explicit controls. Repeated coverage cards and the default feature catalogue are removed from Home. No existing useful setup route is deleted.

The supplied purple tribal rose appears in the root Help control, tutorial Exit Home, setup Back to Tutorial/Close, input-tool Close and the native menu dismissal controls. The original JPEGs are unchanged on both platforms. The head is grayscale while connection evidence is unavailable. Color and a gentle animation require the validated coverage state to be ACTIVE; completing pictures cannot change that state. Animation respects inactive/background state and reduced-motion settings.

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
