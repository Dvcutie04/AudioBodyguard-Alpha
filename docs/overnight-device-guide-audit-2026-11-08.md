# Overnight device-picture and cyan-button audit — 8 November 2026

**Scope:** source audit of the exact parent `#119` commit `af09bde093b78a496124843946799f636a4a8e54`, not a physical-device test. See the attached draft head for proposed styling changes. Keep the earlier verified #114 Android and #115 Simulator packages tied to their own revisions.

## Catalog inventory and proof levels

`contracts/setup_guides_v1.json` defines **29 groups**, **52 distinct routes**, **441 distinct illustrated steps**, and **39 cited source entries**. The generated guide catalog renders local annotated **illustrations**, not live device or manufacturer screenshots. A structural read of all 441 steps found **441/441** with a nonempty item list, an in-bounds numbered focus, recognized `tv`/`phone`/`both`/`remote`/`choice` surface, and a route source present in the source catalog. This is a **static consistency check**, not a claim that each illustration matches every model and firmware.

The 29 group choices (including subplatforms and non-TV choices) are:

| Source group and supported family | Catalog route choices | Status/limits |
| --- | ---: | --- |
| Samsung TVs | 10 | Illustrated; SmartThings, model-year menu variations and assistants still need exact-device comparison |
| LG TVs | 13 | Illustrated; ThinQ/webOS account and menu versions need exact-device comparison |
| Sony TVs | 8 | Illustrated Google TV and legacy Alexa alternatives; firmware-specific physical review pending |
| TCL TVs | 14 | Roku / Google / Fire separated; platform must be selected before using pictures |
| Hisense TVs | 12 | Roku / Google / VIDAA / Fire separated; installed platform not inferred from brand |
| VIZIO TVs | 9 | Account/platform alternatives; standalone V505M-K09 network-address route also exists; real firmware comparison pending |
| Philips TVs | 10 | Separate Google and Roku variants; vendor/OS-specific comparison pending |
| Sharp TVs | 6 | Roku-family catalog only; no claim for every Sharp OS |
| Roku-branded TV | 6 | Roku-family catalog only; no claim for every OS version |
| Insignia TVs | 8 | Roku / Fire separated; firmware comparison pending |
| Platform selectors: TCL, Hisense, Philips, Insignia | 10 group variants | Catalog subdivisions, not additional independently validated hardware |
| Other / unsure | 8 / 1 | Identification and fallback, not a model-matched picture claim |
| Google Home / Alexa / both / neither | 14 / 10 / 23 / 6 | Companion-app alternatives, not a verified TV connection |
| Phone Wi-Fi | 3 | iPhone 6 steps; Pixel 7; Galaxy 7. **iPad has no own catalog route.** |
| Voice check | 1 | Illustrative instructions only |

**Completeness boundary:** no evidence establishes all worldwide TV brands/models, every OS variant, or each phone manufacturer's settings. Manufacturer labels such as Motorola, OnePlus, or other Android vendors must use an explicit generic-settings fallback unless independently researched. A group count must not be interpreted as a number of physical devices tested.

## Targeted findings in the baseline

1. **iPad Wi-Fi gap:** The network-check picture sheet's `phoneWiFi` context returns `nil` for `.pad` and displays three plain text steps. The main iOS phone group hardcodes `phone_iphone`; iPad therefore lacks a device-specific six-step illustrated route. The current iPhone route must not be relabeled as an iPad visual without adapting the device frame and checking the actual iPad menus. Apple's current [iPad Wi-Fi guide](https://support.apple.com/guide/ipad/ipad2db29c3a/ipados) and [iPhone/iPad Wi-Fi guidance](https://support.apple.com/en-us/111107) provide source-backed navigation and the blue checkmark; exact rendered guide and native iPad tests are next.
2. **Secondary button consistency:** iOS shared `AppButtonStyle` used a neutral `theme.outline` for secondary buttons; Android shared `InterfaceTheme.style` did likewise. This draft changes only app-owned enabled secondary button borders to the palette's contrast-aware cyan/teal accent, retains the solid cyan primary style, and gives disabled controls a neutral outline and muted label. It does **not** recolor operating-system Share or permission controls or claim an active device connection. Visual review and large-text tests remain required.
3. **Pictures versus screenshots:** The guide UI draws a device frame and highlights `items[focus]` for each step. Catalog shape checks do not establish actual menu-screen fidelity, tap-target contrast in screenshots, or hardware pairing. The independent V505M-K09 address guide's four TV illustrations and optional iPhone fifth picture are already checked in #119; hardware menus remain unverified.
4. **Navigation:** The existing #119 focused iPhone/iPad UI pass confirms its model/address guide Back and preserved field. Other brands need route-by-route native screenshot and Back verification. Do not infer blanket coverage from #119.
5. **Verified packages:** Android 0.50/build 52 stays [#114's exact-head artifact](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42339096744/artifacts/13560688368); iPhone/iPad Simulator 0.50.0/build 5 stays [#115's exact-head artifact](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42344629467/artifacts/13563414930). This draft is not a replacement distribution.

## Next focused verification and implementation gates

- Run the new Python style-source regression and existing contract generator checks. Build Swift/iOS and Android on the draft branch and confirm disabled, pressed, secondary, primary, normal and largest-text controls in retained native screenshots; do not infer a visual pass from unit-test success.
- Build a **distinct iPad** Wi-Fi route from the official Apple guide, render a tablet frame (not an iPhone handset), and exercise six forward/back pictures and return to the exact caller without changing the typed address.
- Use the catalog's 29 group matrix to choose a few high-risk native routes per pass, including TCL's three OS families, Hisense's four, LG, Samsung, Sony, Philips, Sharp, Insignia and Roku. Record screenshot evidence and wrong-menu recovery, not just smoke-check counts.
- Prioritize reproducible defects, including native Share blank-container evidence if it recurs. Preserve exact clipboard bytes and cancellation ownership.
- No live device enrollment, physical TV pairing, protection qualification, signing-secret modification or distribution is in scope.
