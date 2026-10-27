# TV picture-direction review — 0.32.3

Reviewed October 26, 2026 (America/Los_Angeles). This phase follows the Samsung
0.32.1 repair and Android output-inventory freshness work in 0.32.2.
Android is build 35, `0.32.3-tv-guide-clarity-live-input`; iPhone/iPad source is
0.32.3 (build 1). Native installation and physical TV qualification are separate.

## Scope and findings

Reviewed the shared catalog's 47 existing routes and 408 illustrations, including
the nine non-Samsung brand choices below and their shared assistant/setup paths.
The revised catalog has 51 routes and 436 illustrations. These are schematic
menu-family pictures. They do not reproduce every model's firmware or establish
physical pairing, TV control, sound protection or N2b–N5 qualification.

| Brand / platform | Review and resulting behavior |
| --- | --- |
| LG | ThinQ network check and separate TV PIN/phone entry retained. No invented fixed PIN length. Optional Link/Skip and the TV-capable Basic/Complete Alexa choices are neutral. LG phone part opens the existing ThinQ TV. webOS model and account-link menu families stay separate. |
| Sony | Google TV remote reads the code on the TV before phone entry and Pair. New/legacy Alexa apps and accounts stay separate. Voice power-on is an optional choice with its standby-power consequence. Phone part checks Google TV. |
| TCL | Platform choice precedes Roku, Google/Android TV or Fire setup. Roku Network/IP and System/model pictures stay separate. Google QR setup has an in-app TV-remote fallback. The named QM851G/Q651G/QM891G examples remain qualified menu-family examples. |
| Hisense | Roku, Google/Android TV, VIDAA and Fire remain distinct. VIDAA assistant steps retain the 43A6GV/U5 manual limitation and actual service/region requirement. Google and Roku phone parts match the chosen platform. |
| VIZIO | Four-digit mobile-remote pairing, six-digit legacy account linking, and newer My Hub/Walmart account setup remain separate. Legacy Account → VIZIO Account → Devices & TVs → Add TV now has one picture per selection, then separate TV-code and phone-entry pictures. Phone part checks VIZIO Mobile. |
| Philips | Google/Android and Roku choices stay separate. The documented Google TV voice-remote route can skip pairing if the user reports it already connected. Normal blinking skips the fallback reset; non-blinking can show it. Pictures show both physical buttons held together. |
| Sharp | Explicitly scoped to Roku TV models; System → About/model is not confused with Network → About/IP. Phone part checks the official Roku app. |
| Roku-branded | Network/IP, System/model, mobile remote, Google Home and Alexa paths remain distinct. Phone part uses the existing Roku app, with pairing help available. |
| Insignia | Roku/Fire choice comes first. Fire phone-QR and TV-remote network options are neutral. Account QR sign-in can advance directly to the final TV check without a redundant manual-code step. |

TV, phone, both-device, physical-remote and neutral-choice pictures now have
explicit catalog metadata. Their identity no longer depends on a hard-coded
step number, so inserting a step cannot silently change a TV picture into a
phone picture. Both native renderers and the offline companion use the metadata.
LG, VIZIO and Google TV have new five-picture checks of their existing official
phone app; Wi-Fi help remains a separate route. Finishing a phone-only route
cannot mark TV setup complete.

The seven-picture Google TV manual fallback starts at the TV QR screen and
shows Down → the actual manual option → network → password → official account
prompts → Home. Google’s current first-setup article supports this route.
Faster phone setup is conditional on the actual TV prompt and current phone
software; the older numeric phone/app minimums were not re-established in the
current source and are no longer presented as a compatibility guarantee.

Changed Google-remote, Google/TCL QR-setup and legacy-VIZIO sequences use versioned bookmarks.
Old numeric progress for those sequences is ignored; unchanged guide progress
still resumes. Android restored Activity/history entries also check the guide
version. Back restores the actual prior Philips/Fire decision after a skip.

## Primary-source review

Sources were opened during this review; manufacturer service availability still
must match the actual model, firmware, country, account and displayed menu.

- [LG ThinQ TV registration](https://www.lg.com/us/support/help-library/lg-thinq-how-to-register-your-tv-with-lg-thinq--20153095986130): registration order, same network, actual TV PIN and optional Link/Skip. It does not specify a fixed PIN length.
- [LG voice/account menu families](https://www.lg.com/ae/lg-story/helpful-guide/how-to-use-voice-commands-with-lg-thinq), [Alexa](https://www.lg.com/us/support/smart-thinq-alexa-voice-control), and [Google speaker linking](https://www.lg.com/us/support/smart-thinq-google-assistant-voice-control): provider accounts and TV-capable skills are conditional; region-specific menu paths are qualified. These pages do not guarantee every current TV supports every assistant.
- [LG affected social-login notice](https://www.lg.com/sa_en/support/announcement/Notice-of-Discontinuation-of-Certain-Social-Account-Login-Services/): affected Amazon social sign-in users may need the linked LG email account and assistant reconnection. This is not a statement that all Google Home or Alexa linking ended. [Model software notes](https://www.lg.com/levant_en/support/product/lg-OLED55C26LA.AMF) separately mention built-in Google Assistant ending; external-speaker linking is not treated as that feature.
- [Sony Alexa setup](https://www.sony.com/electronics/support/articles/00178939): distinguish TV Control with Smart Speakers and the legacy TV Control Setup with Amazon Alexa, their skills/accounts, optional Remote start and subsequent Alexa device selection.
- [Google TV phone remote (Android)](https://support.google.com/googletv/answer/11136134?hl=en) and [iOS](https://support.google.com/googletv/answer/11136134?co=GENIE.Platform%3DiOS&hl=en): choose the TV, enter the code displayed on it, then Pair.
- [Google TV first setup](https://support.google.com/googletv/answer/10050221?hl=en) and [TCL first setup](https://support.tcl.com/en_US/set-up-your-tcl-google-tv-device-remote): match the actual QR setup method; manual setup remains an alternative. [TCL Roku information](https://support.tcl.com/en_US/62989-tcl-roku-tv/where-to-find-the-system-information-of-your-tcl-roku-tv) supports Home → Settings → System → About.
- [Roku manufacturer support](https://support.roku.com/en-us/article/get-manufacturer-support-for-your-roku-tv), [mobile app](https://support.roku.com/article/article/install-the-mobile-app), [Alexa](https://support.roku.com/article/control-your-streaming-devices-with-alexa), and [Google](https://support.roku.com/en-gb/article/control-your-streaming-devices-with-google): brand alone is insufficient; platform, software and regional availability matter. No network-control setting is silently changed.
- [Hisense 43A6GV manual](https://assets.hisense-usa.com/assets/ProductDownloads/472/049fe3952c/43A6GV-user-manual.pdf), voice-service sections: retain VIDAA account, TV service choice, matching TV name and official assistant account approval, scoped to the documented menus.
- [VIZIO Mobile](https://www.vizio.com/en/mobile), [legacy account linking](https://www.vizio.com/en/vizio-account/link-your-tv), and [newer Walmart account](https://www.vizio.com/en/overview-account): separate four-digit remote pairing, six-digit account linking and My Hub QR account flow.
- [Philips remote troubleshooting](https://www.usa.philips.com/c-f/XC000020869/how-do-i-troubleshoot-the-remote-control-for-my-philips-google-tv): check existing connected remote first; Google Voice + VOL− for 3–5 seconds; OPTIONS + VOL− reset only if it does not blink; select the named remote and check Connected. Documented model examples remain in the guide.
- [Amazon Fire TV setup](https://digprjsurvey.amazon.com/csad/help/node/GFH3K8GVLXYTBZ63) and [Alexa linking](https://digprjsurvey.amazon.com/csad/help/node/G7JTYZL789TQJHKV): initial setup, account approval and later Alexa linking are separate tasks.

## Verification and evidence limits

The new Python regressions first reproduced combined TV/phone code steps,
missing brand phone companions, mandatory-looking LG Link, combined VIZIO menus,
step-number-dependent pictures and the missing manual fallback. Contract tests
also reject malformed picture metadata and cross-brand phone handoffs.
Swift/Kotlin regressions cover phone-only learning and versioned progress.

Tests-only source `44f92b46ad9ecd124f5e0515c7ed15831d47024c` was run before the
native Philips navigation implementation. [Android UI run 40433562826](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40433562826)
reached Philips picture 5 and failed because “Remote already connected” was
missing. The initial iPhone sequence also encountered a saved bookmark, so its
missing-picture assertion is not counted as an isolated product regression.
The corrected iPhone test explicitly restarts through the real guide UI.
An earlier Android attempt used a misspelled runner option and is tooling-only.

The focused native workflow exercises Philips skip/reset/Back, Google TV and
VIZIO code surfaces, neutral LG choices, Roku Network/System separation,
Hisense platform scope, Fire QR completion, manual Google TV setup, matching
phone companions, resume and large text. It retains Android screenshots and
hierarchies and iPhone/iPad XCTest screenshots/results with exact source identity.
Full Python/C/Swift/Kotlin checks and the Android live-input/lint lane remain
required. The draft PR records final run results and installer identity against
identified candidate sources. A test-only correction opens More TV brands before
selecting Vizio in the new phone-handoff test; it does not change either app.
The PR distinguishes APK-build source from the corrected UI-harness source
and records product-tree equality. This document does not imply those runs passed.

No emulator or simulator result is physical TV testing. User testing of the
installed candidate is still required before any model-specific pairing claim.
