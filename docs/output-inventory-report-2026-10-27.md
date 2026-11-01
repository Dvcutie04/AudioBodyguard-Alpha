# Reviewed phone-output inventory report — 0.33

October 27, 2026 (America/Los_Angeles). The owner is testing 0.32.3 and requested
completion of the next roadmap increment. The next engineering gate remains
N2b inventory before a playback adapter. This step makes the already researched
Android inventory useful as a reviewable, private observation record.

## Research and decision before implementation

This builds on the approved [two-phone inventory research](phone-output-research-2026-10-24.md)
and the existing reviewed-text sharing mechanism used by build/support reports.
It adds no audio API, playback adapter, capture path or physical experiment.
Current API guidance was refreshed from primary Android documentation:

- [Sharesheet text sharing](https://developer.android.com/develop/ui/compose/sharing/send?hl=en)
  documents ACTION_SEND, text/plain, EXTRA_TEXT and createChooser. Use a system
  chooser after explicit review; supply no recipient, subject, stream or URI.
- [AudioManager getDevices](https://developer.android.com/reference/android/media/AudioManager#getDevices(int))
  returns currently connected devices matching the flags. Retain the existing
  output-only query and its limits; it is not an active playback-route reading.
- [Activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle?hl=en)
  distinguishes pause/resume, focus and process recreation. Sharing must not
  turn a returning screen into an automatic inventory read or playback start.

| Candidate | Latency / battery / memory | Decision |
| --- | --- | --- |
| Automatic collection or upload | More wakeups/network work; wider retained data and recipient assumptions | Reject. Neither is needed to collect this inventory. |
| Reread on Share | Small foreground read, but changes the payload after review | Reject. The reviewed snapshot must be the shared snapshot. |
| Dated immutable snapshot, explicit Review and native Share | Existing synchronous manual query; bounded text; no polling or app-written file | Select. Reuses the established inventory and sharing patterns. |
| Playback/route probe to fill unknown fields | New owner, focus, output and measurement obligations | Defer until the actual inventory and exact backend review are complete. |

These are design comparisons, not measured latency, battery or handset results.
No performance claim follows from emulator timing or test counts.

## Contract

Sound → Output inventory → Refresh outputs → Review output report.
Review is disabled before a successful read and after the current list clears.
The report freezes the app/build details, bounded phone manufacturer/model and
Android version/API, phone-clock UTC capture time, change-notice availability,
and the displayed available-output advertisements. Repeated kinds stay separate.
Device/capability truncation and Android's empty-array arbitrary-support meaning
remain visible. Selected route and negotiated format remain Unknown; independent
capture/calibration are not recorded, and physical output/protection is unverified.

The report queries no audio-device IDs, addresses, product names or serial-number
API. It contains no network/TV details, recordings, words, photos, recaps, log
dump or recipient.
The existing native caller supplies fixed output-kind and encoding labels.
The report factory accepts the fixed four-line installed-build envelope, bounded
single-line advertisement fields, and a bounded capture clock. Malformed or
oversized inputs cannot become a share payload. Text is capped at 24 Ki
characters and 48 KiB UTF-8. This bounds presentation/Intent data; framework
array allocation retains the limitations documented in the original research.

Opening Review reads no framework data and opens no share target. The preview
is an explicitly dated historical snapshot, with a fixed notice above Share
that outputs may have changed even when the report body is scrolled. A change notification still withdraws the live inventory and
its Review action. It cannot rewrite a report already under review. Sharing
uses precisely the displayed immutable string, clears the live snapshot before
leaving, and requires a separate native target choice. Cancel or return preserves
the same preview; Back returns directly to Output inventory and any cleared live
list requires explicit Refresh. No chooser callback is a delivery receipt.
The app writes no report file or persistent preference. Process recreation
starts with no report; an explicitly selected recipient/clipboard can retain
what the user chooses to share.

Android is the first inventory/report implementation because its test APK is
already installable. iPhone source stays 0.32.3 with its existing flows; both
mobile products remain primary targets. Signed iPhone delivery and a separately
reviewed iOS output acquisition path remain dependencies.

## Verification obligations

Use test-first Kotlin cases for the exact report envelope, empty/truncated
capabilities, immutable capture, unknown physical fields, metadata normalization
and rejection of malformed/oversized inputs. The native Android test must first
fail on 0.32.3's absent Review control, then exercise disabled-before-read,
preview without sharing, native Cancel/receiver round trips, exact Intent text,
no extra URI/stream payload, callback invalidation, Back, lifecycle/process
clearing, large text and unchanged microphone permission. Synthetic callbacks also test that withdrawing the live list disables new
Review while preserving the already labelled historical copy. Test observers
and the receiver remain outside the delivered APK. Retain source identity, screenshots,
receipts, unit/lint results and signed-APK byte identity in CI.

The draft PR records actual red/green results and artifact identities. A software
report can supply some phone observations for the [private N2b record](n2b-inventory-preparation-2026-10-24.md).
It does not fill the complete host/backend, route, negotiated format, capture,
ownership, work, continuity or consent inventory, authenticate its device,
qualify physical output, activate protection or advance N2b–N5.

The tests-only baseline is `19f3b67d5035253cc7538ffc16f6dff751964784`.
Native UI run 40512820172 reached the actual old inventory and failed because
Review output report was absent. Its Kotlin test compile separately rejected
the missing report API. Those failures precede the new native report flow;
final green runs and APK identity belong to the implementation PR.
