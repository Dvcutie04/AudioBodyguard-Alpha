# Illustrated TV setup and account approval

Research date: 2026-09-29. Continuation of the foreground voice/photo work in draft PR #31. Applies to both native shells. No production control or handoff barrier is relaxed.

## Delivered scope and evidence limits

The existing selector lists **brands**, not model numbers: Samsung, LG, Sony, TCL, Hisense and Vizio. It also includes another brand, not sure, Google Home, Alexa, both and neither. A claim to cover every model of those brands would be unsupported. This catalog supplies all those choices with guides selected by the model example, operating system or actual menu the user sees.

The shared contract contains **35 guides and 316 sequential screen illustrations**. Exact documented examples are TCL 85QM851G, 98QM851G, 98Q651G, 115QM891G; Sony XR-65X90K; and Hisense 43A6GV. Other paths explicitly identify their menu-family scope. Firmware, country and app version can change the sequence. No exact model is inferred from brand recognition or an IP address.

Every step draws a scalable native mock screen, the focused menu row, a numbered arrow, the device being used and an action pictogram. These are simplified illustrations, not photographs of an actual TV or a simulated live pairing result. They contain no usable QR code or PIN. Pictures reduce dependence on prose; this delivery is not a claim of translation into every language or of cross-language usability validation.

Entry points: Devices → Illustrated setup guides; the main Help menu; each selected TV/assistant card in first-visit step 4; photo setup; Voice requests → Show voice steps; and Voice check → Help. Back/Next/Close remain separate from the scrolling picture and instructions. “My screen looks different” preserves the current step and offers the route’s official sources and another menu choice. Closing returns to the previous app screen or tutorial step.

## Manufacturer evidence matrix

All links below are primary manufacturer/platform documentation, reviewed for this change. They establish published menu paths, not successful pairing on a physical device in this session.

| Brand/system | Sequences and distinguishing evidence | Source and limit |
|---|---|---|
| Samsung | SmartThings discovery; separate TV OK approval and TV-PIN entry; model lookup for 2022+ vs older menus; SmartThings → Google Home/Alexa | [TV pairing](https://www.samsung.com/us/support/answer/ANS10005262/), [assistants](https://www.samsung.com/us/support/answer/ANS10006871/), [model lookup](https://www.samsung.com/ca/support/home-appliances/find-the-model-and-serial-numbers-for-your-samsung-device/). Same Samsung account and compatible model required. |
| LG | ThinQ discovery/PIN; optional Home Board account link; separate webOS 5 and 6+ account paths; four model-information menu versions; Google Home and TV-capable Alexa skill | [ThinQ registration](https://www.lg.com/us/support/help-library/lg-thinq-how-to-register-your-tv-with-lg-thinq--20153095986130), [webOS information](https://www.lg.com/us/support/help-library/lg-tv-check-out-the-lg-content-store-to-see-what-apps-are-available-for-your-smart-tv-CT10000018-20154548998527), [regional account paths](https://www.lg.com/ae/lg-story/helpful-guide/how-to-use-voice-commands-with-lg-thinq), [US Alexa](https://www.lg.com/us/support/smart-thinq-alexa-voice-control). Some models excluded; UAE account guidance does not establish worldwide availability. |
| Sony | Current TV Control with Smart Speakers / Sony’s TV Skill; separate legacy TV Control Setup with Amazon Alexa / Basic skill; QR account activation, TV confirmation, speaker association | [Sony setup](https://www.sony.com/electronics/support/articles/00178939). Source illustrates XR-65X90K. Missing TV setup app means this route is unsupported. |
| TCL | Exact-model Google TV first setup; already-configured Google TV phone remote; distinct Roku and Fire TV variants | [TCL Google TV](https://support.tcl.com/en_US/set-up-your-tcl-google-tv-device-remote), [QM851G manual](https://www.tcl.com/usca/content/dam/tcl/product/home-theater/q-class/documents/85-98QM851G%20V2%20US%20QSG.pdf), [Q651G manual](https://www.tcl.com/usca/content/dam/tcl/product/home-theater/q-class/documents/98Q651G%20US%20QSG.pdf), [QM891G manual](https://www.tcl.com/usca/content/dam/tcl/product/home-theater/q-class/documents/115QM891G%20US%20QSG.pdf). US model examples only. |
| Hisense | 43A6GV VIDAA U5 account → Voice Service → Google Smart Home Service/Amazon Alexa; other OS families selected separately | [43A6GV manual](https://assets.hisense-usa.com/assets/ProductDownloads/472/049fe3952c/43A6GV-user-manual.pdf). No extrapolation to every Hisense platform or country. |
| Vizio | Four-digit mobile pairing, separate six-digit TV-account link, mobile Account partner handoff | [Mobile app](https://www.vizio.com/en/mobile), [TV-account link](https://www.vizio.com/en/vizio-account/link-your-tv). Account handoff labels are descriptive where the source does not document a fixed menu label. |
| Google TV/Home | Phone remote; legacy TV QR/Google Home setup vs faster phone-camera setup; current Add → Device → Add a different way; separate older Settings and + menu paths | [Remote](https://support.google.com/googletv/answer/11136134?hl=en), [first setup](https://support.google.com/googletv/answer/10050221?hl=en), [provider linking](https://support.google.com/googlehome/answer/9159862?hl=en). Existing TVs are not reset to recreate a first-setup illustration. |
| Roku/Alexa | Alexa TV & Video → Roku → account approval → speaker association; Google provider link | [Roku Alexa](https://support.roku.com/en-us/article/control-your-streaming-devices-with-alexa), [Roku Google](https://support.roku.com/en-gb/article/control-your-streaming-devices-with-google). Roku OS 9.1+ and documented regions only. |
| Fire TV/Alexa | Same Amazon account → Alexa More → Settings → TV & Video → Fire TV → device link | [Amazon](https://digprjsurvey.amazon.com/csad/help/node/G7JTYZL789TQJHKV), [TCL](https://support.tcl.com/en_US/set-up-and-configuration-ca/control-amazon-fire-tv-smart-tvs-with-alexa). Actual Fire TV variants only. |

A modern Alexa app can differ from the older Skills menu. Samsung’s current source documents a Message Alexa → Smart Home Skills route; the catalog labels it separately. Menus are not silently mixed into one supposedly universal procedure.

## Authenticated integration research from the prior handoff

Consumer pairing and account approval authorize the selected vendor/assistant flow. They do **not** give AQSS the vendor’s credentials, a device capability lease, output authority, or independent observation.

- [SmartThings Access App setup](https://developer.smartthings.com/docs/service-integrations/app-setup) currently labels Access App registration “COMING SOON” and unavailable. Published [OAuth documentation](https://developer.smartthings.com/docs/service-integrations/oauth) alone is not evidence that an AQSS registration can be deployed today. Do not put a client secret or broad personal token in the phone or pretend to link an unregistered application.
- Google publishes separate [Android permission](https://developers.home.google.com/apis/android/permissions) and [iOS supported-type](https://developers.home.google.com/apis/ios/supported-device-types) documentation. A TV’s presence in the consumer Home app does not establish that AQSS can access that model/type on both platforms. Registration, supported traits, consent, revocation and exact device behavior need qualification.
- [Alexa Smart Home interfaces](https://developer.amazon.com/en-US/docs/alexa/smarthome/rest-api-reference.html) describe an integration’s device capabilities. They are not a general API for AQSS to take control of every TV someone linked through a different company’s skill.

Next executable integration gate: select a supported exact TV/country/account and an available developer registration; implement a **read-only** authenticated enumeration adapter on both phones; validate authorization callback binding, least privilege, denial/cancellation, stale callbacks, revocation, token storage and device identity. Only then qualify specific capabilities under existing authority leases. No credentials or physical TV were supplied in this task. This change therefore implements instructional onboarding, not a fabricated OAuth connection.

Cloud discovery or OAuth completion cannot establish a sub-200 ms protection path. A later hardware trial must measure control/observation latency and standby behavior. Remote-start settings can affect energy use. No power saving, acoustic protection, transcription accuracy or physical pairing success is inferred from guide completion.

## Implementation and verification

- `contracts/setup_guides_v1.json` is the presentation-only source of truth. Its generator emits identical Swift and Kotlin catalogs. Validation bounds steps and text, requires a visible highlight and official HTTPS evidence, rejects unexpected action/authority fields and detects missing group routes.
- Native views draw every picture locally; there is no image download, TV socket, embedded login, credential collection, OCR endpoint use or automatic permission request. Official documentation opens only on the user’s link tap.
- Voice Help clears/stops capture before opening. No guide resumes microphone capture. The voice walkthrough ends with an explicit Open Voice check button; it opens the tool idle. A photo brand can preselect a guide group only; it cannot identify or connect a TV.
- Deterministic coverage test first failed for the missing generator/catalog, then passed. Full local regression result before native CI: 1,797 passed plus 14 subtests.
- Native walkthrough additions cover the TCL/Google selection from first-visit step 4, Samsung TV approval and guide completion, Google/Alexa account screens, the new Voice requests help, return from a menu mismatch, Android recreation/rotation, and large-text control reachability. Native build and screenshot results are recorded in the PR after completion.

Remaining empirical debt: physical-model pairing, app/firmware/country variants, multilingual usability, VoiceOver/TalkBack user trials, denied/expired real provider approvals, and live microphone/OCR accuracy on installed phones. Simulator illustrations do not close these gaps.
