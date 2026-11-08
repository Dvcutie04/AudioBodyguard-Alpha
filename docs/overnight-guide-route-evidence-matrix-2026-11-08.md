# Every catalog route: source and verification evidence (8 November 2026)

**Recorded source:** [draft #120](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/120), application head `36fbe663fff3ec2496ea16e4edcd82f296004bc5`, tree `635773910ccb4782c672840dc4a4319e5c5d7eb3`. This matrix is an inventory of the repository's **existing** choices, not a claim to support every TV or phone sold worldwide. Generated from `contracts/setup_guides_v1.json` at this commit, with additional inspection of the source links noted below. This is a **documentation-only follow-up**; it does not change app binaries, signed artifacts, or trust behavior.

## What is verified and what is not

- **S — catalog structure:** 29 groups, 53 unique routes, 447 total illustrated steps, 40 source entries. Every route belongs to the declared catalog, and all 447 focus indices target a nonempty row; route-to-source references resolve. The repository's Python guide tests additionally check short instructions, diagram action labels and native-catalog generation. This means the *diagram data are internally consistent*, not that menus match every TV firmware.
- **N — sampled native software UI:** At the application source above, [Android/iPhone/iPad guide run 42474135080](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42474135080) passed all three platform jobs. Native screenshots were sampled (eight Android, seven iPhone, seven iPad) from the [Android](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42474135080/artifacts/13615090807), [iPhone](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42474135080/artifacts/13615585955) and [iPad](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42474135080/artifacts/13615248066) evidence archives. Selected TCL/Philips/Roku, Hisense/VIDAA, LG, VIZIO, Google TV, phone Wi-Fi, address guides and large-text paths showed white Daylight surfaces, cyan primary and outlined secondary buttons, correct sampled device frames and usable Back/Next. A sampled native screenshot does **not** extend N verification to every step of every route.
- **C — current software checks:** [core CI 42474135053](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42474135053) passed Python (2,263 tests plus 40 subtests), Swift, Android and C11; [unsigned iOS preflight 42474140373](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42474140373) passed. These are app/contract and build checks, not real TV certificates.
- **H — hardware/firmware proof:** **None**. No phone-to-TV live pairing, independent TV identity, manufacturer-firmware screenshot match, or physical audio protection has been established. A guide's final step is not an Audio Bodyguard connection. The app uses its own explanatory diagrams, not OEM screenshots.

## All 29 selectable catalog groups

| Group ID | User-facing brand/platform | Route choices | Primary (initially visible) | Optional phone companion |
|---|---|---:|---|---|
| `samsung` | Samsung | 10 | samsung_ok | `samsung_phone` |
| `lg` | LG | 13 | lg_pair | `lg_phone` |
| `sony` | Sony | 8 | google_remote | `google_phone` |
| `tcl` | TCL | 14 | roku_network, google_remote | — |
| `hisense` | Hisense | 12 | roku_network, google_remote, vidaa_google | — |
| `vizio` | Vizio | 9 | vizio_pair, vizio_walmart | `vizio_phone` |
| `other` | Another brand | 8 | identify | — |
| `unsure` | Not sure / no TV | 1 | identify | — |
| `google` | Google Home | 14 | google_samsung, google_lg, google_roku | — |
| `alexa` | Amazon Alexa | 10 | samsung_alexa, lg_alexa, roku_alexa | — |
| `both` | Google Home + Alexa | 23 | google_samsung, samsung_alexa, google_roku | — |
| `neither` | Neither / not sure | 6 | identify | — |
| `voice` | Voice check | 1 | voice | — |
| `tcl_roku` | TCL • Roku TV | 6 | roku_network | `roku_phone` |
| `tcl_google` | TCL • Google TV / Android TV | 9 | google_remote | `google_phone` |
| `tcl_fire` | TCL • Fire TV | 3 | fire_setup | — |
| `philips` | Philips | 10 | philips_voice_remote, google_remote | — |
| `sharp` | Sharp — Roku TV models | 6 | roku_model | `roku_phone` |
| `roku` | Roku-branded TV | 6 | roku_network | `roku_phone` |
| `insignia` | Insignia — match Roku TV or Fire TV | 8 | roku_network, fire_setup | — |
| `phone` | Phone Wi-Fi setup | 4 | phone_iphone, phone_pixel, phone_galaxy | — |
| `hisense_roku` | Hisense • Roku TV | 6 | roku_network | `roku_phone` |
| `hisense_google` | Hisense • Google TV / Android TV | 6 | google_remote | `google_phone` |
| `hisense_vidaa` | Hisense • VIDAA (43A6GV / U5 documented) | 4 | vidaa_google | — |
| `hisense_fire` | Hisense • Fire TV | 3 | fire_setup | — |
| `philips_google` | Philips • Google TV / Android TV | 6 | google_remote | `google_phone` |
| `philips_roku` | Philips • Roku TV | 6 | roku_network | `roku_phone` |
| `insignia_roku` | Insignia • Roku TV | 6 | roku_network | `roku_phone` |
| `insignia_fire` | Insignia • Fire TV | 3 | fire_setup | — |

Top-level TV brands include Samsung, LG, Sony, TCL, Hisense, VIZIO, Philips, Sharp, Roku-branded, and Insignia, plus `other` and `unsure`. TCL, Hisense, Philips and Insignia have platform-specific branches; these are not additional physical devices. Android phone-specific Wi-Fi routes are Pixel and Galaxy; Apple phone routes are iPhone and iPad. Other Android manufacturers must be treated as generic settings / unsupported illustrations unless separately sourced. Google Home and Alexa are *optional external app flows*, not automatic device authorization.

## All 53 distinct routes

Every entry below has **S** status; no entry has **H** status. “Catalog checked; physical pending” deliberately avoids inflating native sampled coverage into a per-route claim.

| Route ID | User-facing purpose | Pictures | Official source IDs in the catalog | Evidence level |
|---|---|---:|---|---|
| `samsung_model_new` | Samsung — find model (2022 and newer) | 5 | `samsung_model` | Catalog checked; physical pending |
| `samsung_model_old` | Samsung — find model (2021 and older) | 5 | `samsung_model` | Catalog checked; physical pending |
| `samsung_ok` | Samsung — connect with SmartThings | 17 | `samsung_pair` | Catalog checked; physical pending |
| `samsung_pin` | Samsung — TV shows a PIN | 18 | `samsung_pair` | Catalog checked; physical pending |
| `samsung_phone` | 2. Check Samsung on your phone | 5 | `samsung_pair` | Catalog checked; physical pending |
| `lg_model_new` | LG — model information (webOS 23+) | 5 | `lg_model` | Catalog checked; physical pending |
| `lg_model_mid` | LG — model information (webOS 6.0 / 22) | 7 | `lg_model` | Catalog checked; physical pending |
| `lg_model_2020` | LG — model information (webOS 5.0 (2020)) | 5 | `lg_model` | Catalog checked; physical pending |
| `lg_model_old` | LG — model information (webOS 4.5 and older) | 6 | `lg_model` | Catalog checked; physical pending |
| `lg_pair` | LG — pair with ThinQ | 13 | `lg_pair`, `lg_login_change` | Catalog checked; physical pending |
| `google_remote` | Google TV / Android TV — pair a phone remote | 9 | `google_remote`, `google_remote_ios` | Catalog checked; physical pending |
| `google_setup` | Google TV — first setup with Google Home | 13 | `google_setup`, `tcl_setup` | Catalog checked; physical pending |
| `tcl_models` | TCL QM851G / Q651G / QM891G — first setup | 13 | `tcl_qm851`, `tcl_q651`, `tcl_qm891`, `google_setup` | Catalog checked; physical pending |
| `google_fast` | Google TV — faster phone setup | 7 | `google_setup` | Catalog checked; physical pending |
| `google_samsung` | SmartThings → Google Home (Add device menus) | 9 | `google_link`, `samsung_assist` | Catalog checked; physical pending |
| `google_lg` | LG ThinQ → Google Home (Add device menus) | 9 | `google_link`, `lg_assist`, `lg_login_change`, `lg_google` | Catalog checked; physical pending |
| `google_roku` | Roku → Google Home (Add device menus) | 9 | `google_link`, `roku_google` | Catalog checked; physical pending |
| `google_vidaa` | VIDAA Voice → Google Home (Add device menus) | 9 | `google_link`, `vidaa` | Catalog checked; physical pending |
| `google_vizio` | VIZIO → Google Home (Add device menus) | 9 | `google_link`, `vizio_pair` | Catalog checked; physical pending |
| `google_legacy` | Google Home — Settings / Works with Google | 7 | `roku_google`, `samsung_assist` | Catalog checked; physical pending |
| `samsung_alexa` | Samsung / SmartThings → Alexa | 9 | `samsung_assist` | Catalog checked; physical pending |
| `lg_alexa` | LG ThinQ → Alexa (Skills menu) | 8 | `lg_alexa`, `lg_assist`, `lg_login_change` | Catalog checked; physical pending |
| `sony_new` | Sony — TV Control with Smart Speakers | 20 | `sony_alexa` | Catalog checked; physical pending |
| `sony_legacy` | Sony — TV Control Setup with Amazon Alexa | 11 | `sony_alexa` | Catalog checked; physical pending |
| `roku_alexa` | Roku TV → Alexa | 10 | `roku_alexa` | Catalog checked; physical pending |
| `vidaa_google` | Hisense 43A6GV / VIDAA U5 → Google Home | 16 | `vidaa`, `google_link` | Catalog checked; physical pending |
| `vidaa_alexa` | Hisense 43A6GV / VIDAA U5 → Alexa | 14 | `vidaa` | Catalog checked; physical pending |
| `vizio_v505m_k09_address` | Find my TV’s IP address | 5 | `vizio_v505m_k09_manual` | Catalog checked; physical pending |
| `vizio_pair` | Vizio — pair the phone (4-digit code) | 9 | `vizio_pair` | Catalog checked; physical pending |
| `vizio_walmart` | VIZIO newer TV — My Hub account, then phone | 14 | `vizio_new_account`, `vizio_pair` | Catalog checked; physical pending |
| `vizio_account` | Vizio — link the TV account (6-digit code) | 11 | `vizio_account` | Catalog checked; physical pending |
| `vizio_assist` | Vizio → Google Home or Alexa | 6 | `vizio_pair`, `vizio_new_account`, `google_link`, `vizio_alexa` | Catalog checked; physical pending |
| `fire_alexa` | Fire TV → Alexa | 8 | `fire_alexa`, `tcl_fire` | Catalog checked; physical pending |
| `identify` | Find the right model or a different screen | 5 | `samsung_model`, `lg_model`, `tcl_setup`, `roku_alexa`, `vizio_account` | Catalog checked; physical pending |
| `voice` | Voice check — what to do next | 9 | `voice` | Catalog checked; physical pending |
| `lg_account5` | LG webOS 5.0 — link the TV account | 5 | `lg_assist` | Catalog checked; physical pending |
| `lg_account6` | LG webOS 6.0+ — link the ThinQ account | 6 | `lg_assist` | Catalog checked; physical pending |
| `google_legacy_add` | Google Home — + / Set up device menus | 8 | `roku_google`, `samsung_assist` | Catalog checked; physical pending |
| `roku_network` | Find my IP address (Roku TV) | 5 | `roku_network_manual`, `roku_brands` | Catalog checked; physical pending |
| `roku_model` | Find my exact model (Roku TV) | 5 | `tcl_roku_model`, `roku_brands` | Catalog checked; physical pending |
| `philips_voice_remote` | Philips Google TV — pair the voice remote | 10 | `philips_remote` | Catalog checked; physical pending |
| `fire_setup` | Fire TV Smart TV — first setup and Amazon approval | 8 | `fire_setup` | Catalog checked; physical pending |
| `roku_phone` | 2. Connect to your phone (Roku) | 5 | `roku_mobile` | Catalog checked; physical pending |
| `phone_iphone` | iPhone — connect to your home Wi-Fi | 6 | `iphone_wifi` | Catalog checked; physical pending |
| `phone_ipad` | iPad — connect to your home Wi-Fi | 6 | `ipad_wifi` | Catalog checked; physical pending |
| `phone_pixel` | Google Pixel — connect to your home Wi-Fi | 7 | `pixel_wifi` | Catalog checked; physical pending |
| `phone_galaxy` | Samsung Galaxy — connect to your home Wi-Fi | 7 | `galaxy_wifi` | Catalog checked; physical pending |
| `vizio_google` | VIZIO → Google Home | 6 | `vizio_pair`, `vizio_google`, `google_link` | Catalog checked; physical pending |
| `vizio_alexa` | VIZIO → Amazon Alexa | 6 | `vizio_pair`, `vizio_alexa` | Catalog checked; physical pending |
| `lg_phone` | 2. Check LG ThinQ on your phone | 5 | `lg_pair`, `lg_login_change` | Catalog checked; physical pending |
| `vizio_phone` | 2. Check VIZIO Mobile on your phone | 5 | `vizio_pair` | Catalog checked; physical pending |
| `google_phone` | 2. Check Google TV on your phone | 5 | `google_remote`, `google_remote_ios` | Catalog checked; physical pending |
| `google_manual` | Google TV — finish setup with the TV remote | 7 | `google_setup`, `tcl_setup` | Catalog checked; physical pending |

## Independently cross-checked current manufacturer guidance

1. **LG model information (four routes):** LG's [official 2025 article](https://www.lg.com/us/support/help-library/lg-tv-check-out-the-lg-content-store-to-see-what-apps-are-available-for-your-smart-tv--20154548998527) includes actual TV Information menu paths by webOS version despite the article's general Content Store headline. Routes `lg_model_new`, `lg_model_mid`, `lg_model_2020`, and `lg_model_old` were compared step-by-step to the documented paths: 2023+ Support; 2021–22 General → Devices → TV Management; 2020 Support; 2014–19 General → About this TV. All four match that published *generic* menu sequence. LG warns that region, language and firmware can change the display; physical comparison remains necessary.
2. **Apple iPad and iPhone Wi-Fi:** Apple's [iPad Settings guide](https://support.apple.com/guide/ipad/ipad2db29c3a/ipados) and [September 14, 2026 iPhone/iPad guidance](https://support.apple.com/en-us/111107) show Settings → Wi-Fi, select network, optional password, blue checkmark and Wi-Fi icon. Six-step `phone_ipad` and `phone_iphone` paths reflect this. The iPad simulator displays a tablet illustration, the iPhone simulator a phone illustration. This only establishes Wi-Fi association, not that the TV is reachable; a guest network can isolate devices.
3. **Samsung Galaxy Wi-Fi:** [Samsung Canada's February 10, 2026 guidance](https://www.samsung.com/ca/support/mobile-devices/connect-your-samsung-galaxy-to-the-internet/) confirms Settings → Connections → Wi-Fi → choose network → Connect → connected status, matching `phone_galaxy`. The source expressly limits its screenshots to Canadian devices and warns of model/OS variation.
4. **Google TV remote:** Google's [Android](https://support.google.com/googletv/answer/11136134?hl=en) and [iPhone/iPad](https://support.google.com/googletv/answer/11136134?co=GENIE.Platform%3DiOS&hl=en) guides confirm the “TVs nearby”, device selection, TV-displayed code and Pair sequence used in `google_remote`. TV control within Google TV is not evidence of Audio Bodyguard enrollment.
5. **New compatibility question for the next small build:** Google's [current first-setup documentation](https://support.google.com/googletv/answer/10050221?hl=en) states faster QR-based onboarding requires **Android 9+** or **iOS 17+**, and on iPhone an up-to-date Google TV app if already installed. The `google_fast` route currently warns in its *hidden step note* to check official phone requirements but does **not** state those minimums in the visible step instructions. Prioritize making that eligibility/fallback clear to users, with regression tests, before suggesting faster setup broadly; only supported TV models show the faster option.

## Next source-accurate checks (not yet completed)

- Compare the rendered diagram for every one of the 447 steps, not only the sampled 22 native screenshots, against the *exact* TV/phone model, platform version and installed firmware. Record source screenshots or model/version-specific evidence separately; never pass an invented image off as a real menu.
- Extend native sampled tests to underrepresented Samsung variants, Sony legacy/new Alexa, Fire TV branches and alternate VIDAA account pathways, with Back, Resume, large text, wrong-screen recovery and correct source/OS labels.
- Keep one-step setup and optional [?] details; verify secondary buttons stay cyan-outlined, disabled controls neutral, and real connection indicators based on verified physical state only.
- Keep existing #116 native Share Copy/Cancel exact-byte and exit-60 tests, #118 certificate cancellation/timeout and #117 zero-application-byte peer lab isolated. Do not claim these suites were rerun on #120.
- Hardware-only follow-up: record actual phone OS, TV full model/firmware, network segment, real displayed address, the physical Wi-Fi/certificate behavior and independent trust evidence before approving pairing or protection.

**Package provenance:** retained [Android 0.50/build 52 (#114)](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42339096744/artifacts/13560688368) and [iPhone/iPad Simulator 0.50.0/build 5 (#115)](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42344629467/artifacts/13563414930). Neither is rebuilt, signed, distributed, or superseded by this report.
