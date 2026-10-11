# First internal TestFlight build

This release lane prepares the ordinary read-only Audio Bodyguard app for
testing setup, navigation, input permissions and accessibility. It does not
qualify audio protection or TV control. A signed upload is not a successful
phone trial, and Apple's processing must finish before a build can be installed.

The [pre-beta audit](pre-beta-audit-2026-10-11.md) records the initial repairs.
The [TestFlight preparation workflow](../.github/workflows/testflight-beta.yml)
reuses the complete core checks, native walkthroughs and unsigned iPhone
preflight at one exact source SHA. Software preparation runs automatically
after a main update; signing and upload run only when manually requested with
upload enabled.

## Owner setup, once

1. Confirm the paid Apple Developer membership is active and App Store Connect
   is accessible. The purchase confirmation alone does not establish activation.
   If Apple presents a new binding agreement, the Account Holder must review
   and accept it themselves.
2. Register an ordinary iOS App ID and create the App Store Connect app record:
   name **Audio Bodyguard**, primary language English (U.S.), your registered
   bundle ID, and a private SKU such as `audiobodyguard-ios-preview`. Keep the
   registered bundle ID stable. The source default is
   `com.aqss.bodyguard.prototype`; use it only if it is registered to your team.
   The workflow can build with the actual registered ID without renaming the
   simulator prototypes.
3. Create a **team** App Store Connect API key with the signing permissions
   needed for your team, including Certificates, Identifiers & Profiles and
   cloud-managed distribution signing. This is a security-sensitive owner
   action; inspect its scope before granting it. Individual keys have a
   different authentication contract and do not fit this workflow. If the key
   cannot sign, the job stops; it does not expand permissions automatically.
4. In this repository's GitHub Settings → Environments, configure
   `testflight-internal`. Restrict deployment branches to **main** and add the
   owner as a required reviewer if available for the repository. Set the
   following environment values through GitHub's own forms. Do not paste
   passwords, verification codes or private keys into chat.

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `APPLE_TEAM_ID` | Your 10-character Apple team ID |
| Variable | `IOS_BUNDLE_ID` | The registered ordinary app bundle ID |
| Secret | `ASC_KEY_ID` | The team API key ID |
| Secret | `ASC_ISSUER_ID` | The team key's Issuer ID |
| Secret | `ASC_PRIVATE_KEY_P8_BASE64` | One-line base64 of the downloaded `.p8` file |

On iPhone a-Shell, if the downloaded key is in Documents, this single physical
line writes a local base64 file without printing its contents. Replace the
placeholder filename with the actual filename; preserve the original key
securely. Copy the file's contents only into the named GitHub secret form.

```sh
python3 -c 'import base64,pathlib; p=pathlib.Path("AuthKey_YOURKEYID.p8"); q=p.with_suffix(".p8.b64"); assert not q.exists(); q.write_bytes(base64.b64encode(p.read_bytes()))'
```

## Automated preparation and upload

After the reviewed candidate is merged, open GitHub Actions → **Audio Bodyguard
internal TestFlight preparation** → Run workflow. Choose branch **main**, enter
the exact 40-character source SHA and version `0.1.0` (or the app version you
are preparing).

Start with **upload off**. This reruns the Python/C/Swift/Android checks, the
iOS/Android walkthroughs and the iPhone archive preflight against the selected
commit. A `beta-candidate.json` artifact records software checks only.

When Apple setup is complete, run with **upload on**. Checks run again on the
same SHA before the signed job can start. The workflow:

- refuses non-main workflow runs and source commits outside main's history;
- checks the signing checkout's commit and tree against the tested identity;
- assigns build number `run_number.run_attempt`, so retries use a new number;
- archives the physical-device app with the connected appearance demo excluded;
- uses Xcode automatic provisioning and cloud signing with the configured key;
- requests an internal-only export and checks the IPA's signature, embedded profile,
  platform, bundle/version/build identity and required privacy manifest;
- validates with Apple, uploads and records the exact signed IPA SHA-256;
- retains only non-secret provenance and deletes temporary keys, profiles,
  keychain, IPA and archive. Signed packages are not public Actions artifacts.

The script's metadata inspection alone reports `PACKAGE_METADATA_ONLY` and
`NOT_UPLOADED`. Only a successful signature check, Apple validation and upload
allow the workflow to record
`SIGNED_IPA_UPLOAD_ACCEPTED_PROCESSING_UNVERIFIED`. Neither result verifies
processing, installation or physical protection. Missing signing setup or
signing permissions produces a failed job with no upload.

The release automation is staged for this repository. Its Linux package tests
are reproducible; a real signed execution requires the owner's Apple setup and
must be checked from the resulting workflow. It is not a claim that a signed
upload has already worked.

## Install and test before broader invitations

In App Store Connect, wait for the uploaded build to finish processing and
confirm that Apple labels it **Internal** before adding it to a group. The
export setting alone does not prove Apple's processed build classification.
Review and answer any export-compliance questions for the actual native app. Create
an internal group for the owner, add the processed build and enter **What to
Test** using [the beta testing notes](#what-to-test). Add the owner as the
initial tester, then accept the TestFlight invitation on the iPhone. Developer
membership payment does not generate the app's invitation or redeem code.

Before adding a build to a group, check whether automatic distribution is
enabled: adding a build can notify existing group members. Do not add wider
testers until the owner completes the
[physical-phone trial](p1-installed-device-trial.md). Fill a private copy of
`p1-testflight-trial.template.json` using actual installed build and trace
values. Complete the separate beginner, voice/photo, denial and lifecycle
checks in that protocol. Unperformed cases stay unperformed.

An internal-only build cannot be used for external beta testing or the App
Store. For later external testing, prepare a separate ordinary distribution
build, complete the required TestFlight beta review and select the intended
testers; do not grant strangers App Store Connect roles merely to use the
internal lane.

## What to Test

Audio Bodyguard setup preview: follow the numbered phone/TV directions; try
Help, Back, Exit Home and resume; report mismatched screens, unclear pictures,
clipping, lag and wrong turns. Try large text and VoiceOver. Optional Voice
check and TV photo setup require permission and user confirmation. Deny a
permission, cancel a tool, background the app and reopen it. Home should remain
Connection not verified; Status details should explain the preview and lack
of output observation. Audio control and protection are not active in this
build. Do not include passwords, raw recordings or private TV/network details
in feedback.

## Official references

- [Apple membership confirmation](https://developer.apple.com/help/account/membership/program-enrollment/)
- [Create an App Store Connect app record](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app)
- [API keys and authentication](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests)
- [Cloud-managed signing certificates](https://developer.apple.com/help/account/certificates/cloud-managed-certificates/)
- [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds)
- [Internal testing](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers)
- [External testing](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers/)
