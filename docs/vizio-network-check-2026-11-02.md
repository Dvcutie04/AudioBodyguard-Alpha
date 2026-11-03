# VIZIO network check and beta critical path

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
hostnames, URL syntax, ports, alternate numeric syntax and OCR automation are
not accepted. A different TV brand receives no implied support from this entry.

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
