# VIZIO network check and beta critical path

## 0.46 connection trial

1. Open **Devices**, then **Device help**, then **TV photo setup**.
2. Open **Photo help**.
3. Choose **VIZIO V505M-K09 address pictures** if the model matches.
4. Follow the four TV pictures to the IP Address row.
5. Tap **Back to photo setup**.
6. Photograph the IP Address row or choose an existing photo of it.
7. Compare the address shown in the app with the TV screen.
8. Tap **Use address in VIZIO check**.
9. Tap **Check this address** when the phone and TV are on home Wi-Fi.

For the software check, confirm the model and picture order, then use a
synthetic photo to verify the editable address, idle check and Back return.
For the physical trial, record the phone OS and TV firmware, compare the
pictures to the real menus, and record the service reachability result.
Pairing and identity require their own physical evidence.

### Live acceptance for address recovery

Use a VIZIO V505M-K09 and an iPhone or Android phone. Repeat on both phone
platforms. Record the phone model, OS, installed app build and TV firmware.

1. Connect the phone and TV to the same home Wi-Fi.
2. Open **Devices → Device help → VIZIO network check**.
3. Open **Find my TV’s IP address**.
4. Tap **My screen looks different**.
5. Check the model label on the TV.
6. Choose the screen shown on the TV. Compare the highlighted control with
   the real remote or menu.
7. Follow the pictures to the IP Address row. Check that each action leads to
   the menu shown in the next picture.
8. Press **Back** until the recovery choices return. Check that each press
   returns to the previous app screen.
9. Tap **Back to address field**. Check that any value already entered is
   still there.
10. Enter the actual TV address.
11. Tap **Check this address**. Record the outcome. A service reply establishes
    reachability at the time of the check.
12. Repeat the mismatch and exit from **Photo help**. Check that the app
    returns directly to the same photo setup screen.

If the menu differs from all the choices, capture the menu labels privately and
record the firmware. On Android, also use system Back. Record any separately
authorized pairing trial by observing the TV’s approval and confirming that the
intended set responds to the paired controller.

## Decision and scope

The owner wants a working TV/phone beta rather than more setup screens. Their
VIZIO V505M-K09 previously failed to connect from both phones on guest Wi-Fi.
This increment adds the first native, explicitly started network diagnostic on
both platforms. It contacts only a manually entered private IPv4 address over
Wi-Fi, trying TCP 7345 and then 9000 with four seconds per attempt. It sends no
application payload, TV command, pairing request or credential. It performs no
scan, DNS lookup, TLS validation exception, playback or recording.

An answer means only that a service accepted a TCP connection at that instant.
It does not authenticate a VIZIO TV, prove the intended address, pair the app,
select an audio route or activate protection. The Home status and production
execution gates remain unchanged. No reachability result becomes authorization.

## Research and synthesis

Reviewed 2 November 2026 under the standing research charter. Published APIs
and a protocol author's own observations are distinguished from device proof.

| Primary source | Finding and limit | Implementation consequence |
| --- | --- | --- |
| [Apple TN3179](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy) and [NWConnection](https://developer.apple.com/documentation/network/nwconnection) | A direct local TCP connection needs local-network privacy handling; Network.framework exposes connection state and cancellation. These do not authenticate the remote service | Add a narrow usage description, use Wi-Fi-only NWConnection, and retain the process owner until the cancelled state is observed. Permission/lifecycle changes never restart a check |
| [Android Socket](https://developer.android.com/reference/java/net/Socket) and [Network.bindSocket](https://developer.android.com/reference/android/net/Network#bindSocket(java.net.Socket)) | A finite connect timeout bounds the blocking call; close can interrupt I/O and can itself throw. Binding selects the network for that socket | One worker, one registered socket, exact byte-form address without DNS, explicit Wi-Fi/non-VPN binding, Stop closes admission/socket, and unresolved cleanup blocks another run |
| [Android local-network permission](https://developer.android.com/privacy-and-security/local-network-permission) | Target SDK 36 uses INTERNET; SDK 37 changes local access permission requirements. Android 16's opt-in restrictions can also affect this check | Retain target 36 and declare INTERNET plus ACCESS_NETWORK_STATE. Do not claim a socket error diagnoses a router or permission. Re-review before a target SDK upgrade |
| [Original SmartCast protocol research](https://github.com/exiva/Vizio_SmartCast_API/blob/master/README.md) | The protocol author documents HTTPS service ports 7345 and 9000 and a certificate-name mismatch. This is independent reverse-engineered research, not a VIZIO-supported SDK or validation of the owner's firmware | Limit this initial probe to two candidate TCP ports. Do not copy insecure TLS examples, send pairing/control requests, or claim model compatibility from an open port |

Alternatives: broad SSDP discovery adds multicast permission, background and
untrusted-advertisement handling; a guessed HTTPS control client would need
reviewed certificate enrollment and authentication first. Choose the smallest
useful combination: explicit host selection, native Wi-Fi-bound transport,
bounded cancellation, and truthful evidence wording. This is an AQSS design
inference, not a measured latency, battery or discovery-success improvement.

Latency: at most two four-second connection attempts on a worker/async native
queue, never on the UI thread. Cancellation completion can still be delayed by
the OS; pending cleanup is not treated as returned. Battery: no warm connection,
periodic timer or automatic retry after a run. Storage: no persistence, host logs,
analytics, shared report or new identifier in this check; the input and visible
result clear on exit/background. INTERNET and ACCESS_NETWORK_STATE are now
explicit in the app's source manifest. The previous PR #94 APK already contained
both permissions after dependency merging: artifact `13193667773`, ZIP SHA-256
`61a0483bf7759a06af30e37e02b7c6fcd5a8c2201f2fcc84724834aa01c2515c`.
This is not the first network capability in the installed Android package.

The existing bundled Google text-recognition dependency is separate from this
TCP probe. [Google's ML Kit privacy statement](https://developers.google.com/ml-kit/terms#privacy)
describes on-device image/text processing and possible service contact and usage
metrics; its [Android disclosure guide](https://developers.google.com/ml-kit/android-data-disclosure)
describes technical data and installation identifiers. These are vendor
statements, not a traffic measurement of our pinned SDK. Do not describe the
whole app as having zero outbound traffic from the probe's no-payload behavior.
SDK disclosures and actual packaged permissions remain part of beta review.

## Interaction

Devices → ? Device help → VIZIO network check. Enter the TV's current network
address, then choose Check this address. Stop and Back remain explicit. Brief
result wording and the unverified identity/pairing/protection boundary remain
visible; details and an app-settings shortcut live in Help. No permission or
network request occurs simply by opening the screen or editing the address.
The Android screen uses the selected theme and insets for system bars, cutouts
and the keyboard; the single Check action uses the existing primary-button style.

Only canonical RFC1918 IPv4 literals are admitted. This intentionally narrow
first version also rejects host octets 0 and 255; it is not a subnet detector
and can exclude valid hosts on unusual subnet layouts. IPv6, public addresses,
hostnames, URL syntax, ports and alternate numeric syntax are not accepted.
The 0.46 photo route uses the same address validation before offering the
reviewed value to the check. A different TV brand receives no implied support
from this entry.

## Verification and next gates

Software checks cover the address boundary, bounded attempt/fallback behavior,
Stop with an entered native call, late success, stale tokens and cleanup failure.
Native UI checks reject a public address before any connection or permission
request, and clear the draft on background/Back. These checks do not contact a
real home endpoint. Hosted native compilation and test results belong to the
exact published revision, and remain pending until recorded there.

The owner must next run this exact build on their actual home Wi-Fi and named
TV. Record an unreachable result as such; do not infer isolation from timeout.
If a service answers, the next implementation is reviewed TV identity and
certificate/authentication enrollment before pairing/control. Then test the
actual pairing, permissions, revoked access, disconnects, app exit and restart.
Any later audio-control or protection trial additionally needs the N2b–N5
output, ownership and independent-observation evidence. These are separate
gates; neither this software nor TestFlight processing completes them.

## Private connection-trial intake

After a manual check on Android or iPhone/iPad, choose **Review test result**.
Use **Share test result** or the selectable preview to keep a private plain-text
copy. On iPhone, if the share panel does not show Copy, return to the review,
touch and hold the report body, and use the system text selection menu. If
selection handles appear, select the full report before copying. The worksheet
review also supports this separate copy path. Native sharing has its own
release checks. [Apple text selection guidance](https://developer.apple.com/documentation/swiftui/view/textselection(_:))

On the engineering computer, run the intake with the expected installed
app labels from the install record or phone's build details. For example, with
the iPhone labels `1.0.0` and `14.1`:

```sh
python3 tools/vizio_trial_intake.py /path/to/private/connection-trial.txt \
  --expected-platform 'iPhone/iPad' --expected-version 1.0.0 --expected-build 14.1
```

Use `Android` for an Android report and supply that installation's version and
build. Keep the report outside the repository in a stable private directory.
Use UTF-8 with consistent LF or CRLF endings. The intake checks the complete
v1 format and rejects altered outcome text, extra fields and build mismatches.
It prints JSON with the original file's byte count and SHA-256, phone-clock
review time, declared outcome and a next observation. It makes no network
requests or changes to the report. If an app label is `Unavailable`, the report
alone cannot attribute the outcome to a specific installation.

The digest identifies the exact text reviewed on the engineering computer.
The sender, installed source and physical observation still need independent
verification. A reported reply can guide an identity and authentication review
after the owner confirms the physical setup. A report with no reply preserves
the unknown cause. A report of unresolved cleanup preserves the instruction to
keep new checks blocked while the app reports that condition.

## Offline identity review

Use the report digest retained from intake as `--report-sha256`. The next
review checks that exact report and build for a reported TCP reply. If an
independently authenticated source supplies the intended peer's certificate
reference, compare its SHA-256 with a separately observed, single DER X.509
certificate. Keep both inputs in a stable private directory outside Git.

```sh
python3 tools/vizio_identity_review.py /path/to/private/connection-trial.txt \
  --expected-platform 'iPhone/iPad' --expected-version 1.0.0 --expected-build 14.1 \
  --report-sha256 "$reviewed_report_sha256" \
  --reference-certificate-sha256 "$independent_certificate_sha256" \
  --observed-certificate /path/to/private/observed-leaf.der
```

Either certificate argument can be omitted to record the missing evidence.
Omit the reference if the only fingerprint came from the same presented
certificate or unauthenticated service. A matching digest identifies equal DER
bytes. The source of the reference, peer possession of the key, certificate
validity, revocation and the actual TV still need separate review. A changed
certificate requires a new independently supported reference and review.

Android 0.50 offers **Read service certificate** after a reply. It reads the
leaf fingerprint on the same address, port and Wi-Fi and ends TLS at the
certificate validation callback. Stop and the four-second deadline keep the
same socket ownership rules. The screen displays the fingerprint for manual
copy and clears it on a new check, address edit or background. For a copied
fingerprint, use `--observed-certificate-sha256` in place of
`--observed-certificate` and retain the corresponding reviewed trial report.

| Result | Exit | Meaning |
| --- | --- | --- |
| `NO_REPORTED_SERVICE_REPLY` | 1 | The report declares an outcome other than a TCP reply |
| `INDEPENDENT_REFERENCE_REQUIRED` | 1 | An independent certificate reference is missing |
| `CERTIFICATE_OBSERVATION_REQUIRED` | 1 | A separate DER certificate observation is missing |
| `CERTIFICATE_REFERENCE_MISMATCH` | 1 | The observed bytes differ from the reference |
| `CERTIFICATE_BYTES_MATCH_UNVERIFIED` | 0 | The digests match and both TV identity and pairing authority are false |
| `CERTIFICATE_FINGERPRINTS_MATCH_UNVERIFIED` | 0 | The supplied fingerprint matches the separate reference and both authority fields are false |
| `INVALID_VIZIO_IDENTITY_REVIEW` | 2 | The inputs are malformed, exceed their bounds, or differ from the reviewed report |

The tool only reads local evidence and prints the comparison state and report
digest. Its fixtures use synthetic certificates. A real enrollment design
still depends on a supported identity source and observations from the intended
phone and TV.
