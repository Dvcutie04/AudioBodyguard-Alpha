# TV photo label recognition

October 20, 2026. This input-only increment follows the 0.6 sound-window fix.
The user's VIZIO About/Network photographs show **Model Name** and **IPv4 IP
Address**. The prior parser did not recognize those exact labels. This change
accepts those aliases on Android and iPhone while retaining explicit review.
It does not identify an authenticated endpoint, pair the TV or change volume.

## Research and decision

| Primary source refreshed | Consequence |
| --- | --- |
| [ML Kit Android text recognition](https://developers.google.com/ml-kit/vision/text-recognition/v2/android) | Retain bundled Latin recognition and its block/line text. Image quality affects recognition. Extracting a string does not establish its correctness or which physical device it describes. |
| [Apple Vision text request](https://developer.apple.com/documentation/vision/vnrecognizetextrequest) and [top candidates](https://developer.apple.com/documentation/vision/vnrecognizedtextobservation/topcandidates(_:)) | Retain local Vision recognition, language correction disabled and one provisional candidate per observation. Do not treat the candidate as authenticated device information. |
| [Android shared media](https://developer.android.com/training/data-storage/shared/media) | The isolated emulator test may insert its own synthetic image into MediaStore, select it through the actual system picker, and delete that exact URI afterward. No production import hook, broad media permission or user gallery change is added. |

This is a conservative normalization layer over the existing OCR tools, not
new recognition or vendor-pairing technology. The [original voice/photo research](voice-photo-research-2026-09-29.md)
continues to govern the privacy, image-size, line-count and authority boundaries.
The actual source photographs remain private; tests use fictional network
values and no serial, MAC, network name, account or password.

## Parsing behavior

- Recognize Model Name alongside Model, Model Code, Model Number and Model No.
  Recognize IPv4 IP Address alongside the prior IP/IPv4 address forms. Spaces,
  tabs, compact colons and an immediately following value line are supported.
- Require a single distinct model/address value across all recognized aliases.
  Include malformed or public-address labelled rows in that conflict check;
  a readable row must not hide an unreadable or different second candidate.
- Validate the complete model token: 2–40 ASCII letters/digits/dot/underscore/
  hyphen, starting with a letter or digit and containing a digit. Accept only
  canonical private IPv4 syntax, with no URL, port, path, guessed character,
  leading-zero octet or IPv6 conversion.
- Gateway, DNS, TV name and unlabelled addresses do not become model/IP hints.
  Repeated identical values may agree. Missing, overlong or conflicting input
  remains unknown. Retain the 8,192-byte OCR-text bound; Android also checks
  character count before allocating a UTF-8 copy.

These checks cover only the text presented to the parser. OCR can omit an
entire conflicting row, change a character or lose a label/value association.
The user must review the result on the TV. No fuzzy correction, network probe,
automatic connection, output adapter or protection evidence is introduced.

## Verification plan and scope

Five new public-behavior cases per platform exercise VIZIO-style labels,
indented split labels/CRLF, agreeing/conflicting aliases, unreadable extra rows,
misleading labels and the UTF-8 bound. The tests-only source is
`3cc87434641de0987c6fa8681f56e8ce8f127517`; its
[red CI run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39528874989)
is preserved separately from corrected source.

The additional native Vision test reads a **synthetic 1600×900 PNG** through
the host's Vision framework and then through the same hint parser. The Android
test selects that PNG through the real picker and bundled ML Kit, observes the
model/private IP on the review screen, then checks Clear, picker cancellation,
return navigation and an unverified connection. The PNG is a test resource
only; it is not included in the shipped APK or iPhone app. Its SHA-256 is
`2f55775447c5d28841737a25713ae83a76b37bb6d614fa33007621ce92853f31`.
It was rendered from plain test text with DejaVu Sans using Pillow; it is not
a photograph or a representation of VIZIO's actual screen layout.

Exact native/Simulator/emulator results, any observed failures, source revision
and APK identity belong to the draft PR after completion. Synthetic-image OCR
does not qualify a real photograph, camera, glare, orientation or real-device
accuracy. Physical microphone/output, installed-phone energy/timing and N2b–N5
remain pending. Candidate Android 0.7 retains prior sound checks, recaps and the
approved Silicon Workforce opening poster.

The first corrected-parser revision `7cefc54` passed native package tests and
the six focused iPhone UI cases. Its Android observer stopped before selecting
the image because it expected `content insert` to print a URI. The retained
insert output is empty. [AOSP Content.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/cmds/content/src/com/android/commands/content/Content.java)
shows that insertion discards the returned URI; only query prints rows. The
observer now requires one exact pending filename/path row, constructs its
item URI from the observed ID, verifies a byte-for-byte readback after writing,
and observes publication before opening the picker. This changes test setup,
not app parsing, picker behavior or the expected OCR/UI result.
