# Audio Bodyguard pre-beta repository audit

Reviewed 2026-10-11 UTC. Starting revision:
`fb7b259eae30ac7597c1b29f270b7215aa6a9e4a`, branch
`codex/clear-connection-flow-2026-10-07`.

## Release decision

The repaired source passes the available local checks. It is a candidate for a
**read-only interface and connection-guide beta**, subject to the native build,
signing and physical-phone gates below. This review does not qualify protective
audio operation, actual TV control or continuous monitoring.

The production endpoint factory still refuses execution and
`EndpointHandoffBarrier.is_ready()` still refuses readiness. Picture completion,
OS hints, recognized speech and photo suggestions cannot open these gates.

The changes in this audit are local. They have not been published to GitHub or
delivered through TestFlight by this review.

## Scope and evidence

The starting tree contained 588 tracked files, including 447 Python files.
Review covered the active repository inventory, Python tests and invariants,
native setup/navigation and input-tool lifecycles, shared content generators,
packaging configuration, CI workflows, scripted C lab and current documentation.
Structural checks parsed Python, JSON, XML, privacy/property lists and workflow
YAML. This was a repository-wide audit using targeted source review and automated
checks, not a formal proof or a line-by-line certification of every file.

## Confirmed defects repaired

| Finding | Change and evidence |
| --- | --- |
| iOS lacked a required-reason API privacy manifest. | Added `native/ios-app/PrivacyInfo.xcprivacy`, declared app-private UserDefaults (`CA92.1`) and elapsed-time measurement (`35F9.1`), and included it in the app Resources phase. The unsigned device workflow now checks the manifest inside the archive and records its SHA-256. A regression reproduced the missing file before the repair. Actual archive packaging still needs fresh macOS CI. |
| Legacy proposal helpers reported successful dispatch without any transport or physical receipt. | The formatter and TV stub now report `NOT_EXECUTED`; the queue no longer records an unexecuted proposal as an action. Seven regression cases reproduced false success/action logging before the repair. Existing production fences remain unchanged. |
| The offline picture guide had drifted from the shared catalog. | Regenerated the HTML. Its exporter now supports a non-writing `--check`, works directly without `PYTHONPATH`, and rejects stale or missing output. CI checks tutorial, setup and offline-picture parity. Three regression cases cover these boundaries. |
| Google Home setup omitted Devices and highlighted an older menu label. | Corrected the legacy path to **Devices → Add → Google Nest or partner device**, with a version-difference explanation. Updated generated Swift/Kotlin content, HTML and the existing iOS walkthrough. The source-backed menu-order regression failed before the repair. The separate faster camera setup route remains available. |
| Legacy webhook failures could return the secret-bearing request URL. | Replaced raw exception text with a fixed error message. Two synthetic HTTP/connection failures reproduced credential disclosure before the repair; no live webhook or credential was used. |
| Privacy and device-trial instructions described an older interface. | Corrected saved guide-progress and optional microphone/photo-tool descriptions. The physical-device protocol now explains opening Home → Status details and recording the actual preview explanation. The checker and manual Android hierarchy label agree with current wording; existing trial field names and rejection rules remain intact. Added separate beginner and input-permission trial instructions. |

## Verification results

| Check | Result and limit |
| --- | --- |
| Full Python suite | **1,867 passed and 19 subtests passed**, no skips or failures; Python 3.12.14. Starting baseline: 1,853 tests and 19 subtests. |
| Baseline coverage | **84.55%** of measured Python statements in `src` and `audio_engine` (8,454/9,999). This is baseline coverage, not native or physical coverage. |
| C11 owned-output lab | All **45 cases** passed normally and with AddressSanitizer/UBSan. Runs were sequential. LeakSanitizer was disabled because the environment's tracing prevents it from running; leak detection was not verified. Scripted backends do not prove playback behavior. |
| Generated content | All five checks pass: feedback contracts, interface content, tutorials, setup guides and offline pictures. The final catalog has **46 routes and 403 numbered pictures**. |
| Structure and hygiene | Python/JSON/XML/plist/workflow parsing, Xcode object-reference/resource checks, shell syntax, relative Markdown links and `git diff --check` pass. |
| Python dependency audit | `pip check` passes. `pip-audit -r requirements.txt` reports **zero known vulnerabilities** across 20 resolved packages. This covers the Linux resolution, not all permitted package versions, native SDKs or Android dependencies. |
| Static security scan | Bandit completed without parsing errors: **0 high, 23 medium, 4,594 low** findings across 38,861 lines. Findings are retained and triaged below; this is not a claim of vulnerability-free software. |
| Common credential patterns | No matches in the reviewed current tree for the selected private-key/access-token patterns. This does not audit every possible secret format or erase Git history. |

Reproduce the content and Python checks using the [README](../README.md).
The sanitizer run in this environment used:

```sh
ASAN_OPTIONS=detect_leaks=0 AQSS_LAB_SANITIZE=1 sh native/lab/owned_output/run_tests.sh
```

### Security and maintenance follow-ups

The 23 medium Bandit results comprise ten SQL-construction warnings in
`physical_recovery_store.py`, two urllib warnings in the optional IBM and
webhook clients, and eleven XML-parser warnings in Android evidence tooling
and tests. Reviewed SQL column lists are controlled by the implementation and
values use parameters; no caller-controlled SQL injection was demonstrated.
The XML paths consume local/CI evidence, and the clients start at fixed HTTPS
services. These findings are not exercised by the native read-only beta. Any
future externally supplied XML or deployed network use requires its own review,
including redirect behavior and credential handling.

The IBM client now requires an environment key, but an older literal remains in
Git history. This audit has no evidence that the historical key was revoked.
The owner must revoke it if it is still active. No historical secret value is
reproduced here.

`src/research_loop/README.md` retains non-UTF-8 bytes from the documented phone
export. It is archival documentation, not native runtime code; normalization
would need an explicit provenance update.

## Gates before beta invitations

1. **Publish the reviewed source and run fresh native CI.** At review time,
   GitHub main was `b57ee4d2d7cb2b3406306a93025329aca77cbd6a`.
   [PR #32](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/32) was still a
   draft at `1ec46e23d9e6ab3ece5b949aab9b95a6e6158950`; even the starting local
   revision was ahead of it. Successful remote [core CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/37537993558),
   [simulator walkthroughs](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/37537993572)
   and [unsigned iPhone preflight](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/37537993473)
   apply to that older PR head, not these repairs. Xcode, Swift and the Android
   build toolchain were unavailable locally. Updated native content, UI tests
   and privacy packaging must pass on the exact release revision.
2. **Produce the signed iPhone build.** Confirm Apple Developer team activation,
   signing and App Store Connect access, then archive and upload the ordinary
   device build. Record its source SHA, bundle ID, version/build number, signed
   IPA SHA-256 and TestFlight build identity. No current signed IPA or completed
   TestFlight processing was established here. The Appetize simulator ZIP and
   unsigned device-preflight ZIP cannot substitute for a TestFlight upload.
3. **Run the actual phone trial before inviting the wider beta group.** Follow
   the [installed-device protocol](p1-installed-device-trial.md), including
   large text/screen-reader behavior, restart and background/resume. Separately
   test microphone/speech/camera denial, cancellation, interruptions, unavailable
   on-device recognition, unclear photos and exact tutorial resume. Record
   observed misses and failures instead of inferring success from CI.
4. **Verify beginner usability and the beta promise.** Have an unassisted
   junior-high-level beginner complete the setup for a named real TV/phone
   combination and find Help when a screen differs. Images are instructional
   diagrams, not verified photographs of every firmware version. Selected
   vendor instructions were checked against current primary sources; all 35
   sources and every physical screen were not revalidated. Limit this beta's
   claims to the reviewed read-only interface and official-app setup guidance.

Functional protective audio testing remains a separate qualification effort:
the existing N2b hardware/observer record is unfilled, and endpoint, physical
observation, handoff and containment gates remain unresolved.

## Primary sources checked for the repairs

- [Apple: describing use of required-reason APIs](https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api)
- [Apple: approved reasons for APIs](https://developer.apple.com/documentation/bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitypereasons)
- [Google: set up your Google TV device](https://support.google.com/googletv/answer/10050221?hl=en)
- [Samsung: connect a Samsung TV to SmartThings](https://www.samsung.com/us/support/answer/ANS10005262/)
- [LG: register a TV with LG ThinQ](https://www.lg.com/us/support/help-library/lg-thinq-how-to-register-your-tv-with-lg-thinq--20153095986130)
- [Vizio: account setup](https://www.vizio.com/en/overview-account)
