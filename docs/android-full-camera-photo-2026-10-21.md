# Android full camera-photo input — October 21, 2026

## Defect and scope

The 0.9 Android camera path read `Intent.extras["data"]`, the camera's small
thumbnail. TV model/IP rows can lose detail before recognition begins. Candidate
0.10 instead reserves a unique app-private file and supplies its content URI in
`MediaStore.EXTRA_OUTPUT` and a one-item ClipData with temporary read/write flags.
A successful camera result can have null data: only the reserved output file is
read. An empty/unreadable output never falls back to a thumbnail or returned URI.

The existing content-URI decoder applies its 2048-pixel target before ML
Kit, retaining ImageDecoder orientation on API 28+ and the existing sampled
BitmapFactory/EXIF path on API 26–27. This is full-image *input*, not unlimited
resolution processing or a new accuracy/performance qualification.

The FileProvider is not exported. Its only path is `cacheDir/tv-camera/`, with a
variant-specific authority; no cache root, files root, external storage path,
prefix grant or persistable permission is exposed. The exact URI grant is
revoked when the camera returns. The temporary file is removed after decode,
Cancel, failed launch, Clear, replacement or Activity destruction. If a process
ends without cleanup, the next camera capture removes abandoned files in this
dedicated directory before making a new one. This sweep happens once per
process so it cannot sweep a live capture owned by another Activity. Failures
to remove an abandoned file prevent the new capture. Cleanup logs a failure
without claiming that an open external descriptor or OS work was canceled.

The photo-selection owner still rejects obsolete imports/results. Recreation
starts empty and does not resume the old camera request. Gallery originals are
not deleted; camera output is not published to MediaStore. No broad camera or
storage permission is added. The screen explains the temporary camera copy.
iPhone already imports its original camera image; its production code is
unchanged in this Android increment.

## Primary-source research

Reviewed October 21, 2026 before changing the capture/URI boundary:

- [Android MediaStore ACTION_IMAGE_CAPTURE](https://developer.android.com/reference/android/provider/MediaStore#ACTION_IMAGE_CAPTURE)
  distinguishes the small returned Bitmap from the full image written to
  EXTRA_OUTPUT, including ClipData compatibility and the CAMERA-permission
  condition when that permission is declared. This app delegates to the camera
  and does not add CAMERA permission.
- [Android secure file-sharing setup](https://developer.android.com/training/secure-file-sharing/setup-sharing)
  documents non-exported, grant-enabled FileProvider and a narrow cache path.
- [Android FileProvider](https://developer.android.com/reference/androidx/core/content/FileProvider)
  documents content URIs and temporary intent grants. The app declares its own
  FileProvider subclass and explicitly pins AndroidX core 1.13.1.
- [Android file-provider directory risks](https://developer.android.com/privacy-and-security/risks/file-providers)
  warns against broad root paths and excessive grants. Only this capture's URI
  receives read/write flags; no prefix/persistable access is requested.
- [Android ActivityMonitor](https://developer.android.com/reference/android/app/Instrumentation.ActivityMonitor#onStartActivity(android.content.Intent))
  provides a test-only interception point. The shipping APK has no camera
  fixture, instrumentation component or recognition-result injection.

## Verification contract

Tests-only commit `dee825ff072f46aa9aafd5dfbae3aab21855d92d` adds an instrumented
camera-output regression to the separate test-observer APK. It failed in
[Android run 39652574116](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39652574116),
job `119404430879`, at “Camera must supply EXTRA_OUTPUT; a thumbnail is not a
full photo.” Its evidence artifact `12368974523` has ZIP SHA-256
`ea9b5ec38cc0f4f3efd616258d1be4f736efdc67feccae8472a05ba417c8d5df`.
Compilation and the prior gallery checks completed before this behavioral failure.
The monitor captures
the real outgoing camera intent and writes the existing synthetic 1600×900 PNG
into its EXTRA_OUTPUT URI, returning success with **null** result data. The
unmodified image decoder and bundled ML Kit must recognize VIZIO, V505M-K09 and
10.20.30.40, while the UI still says nothing is connected.

The retained cases also require unique output URIs; single-item ClipData;
temporary, non-prefix grants; removal after successful decode, written-but-canceled
capture, empty-output success with a misleading thumbnail, unavailable camera,
and closing before the posted result arrives. A seeded abandoned file must be
removed before the first capture while unrelated cache data remains intact.
Provider metadata must be non-exported and grant-enabled. Existing real-system
gallery picker, recognition limits, replacement cancellation, microphone,
recap and foreground/time-limit checks remain required.

The monitor replaces the *external camera response* only. These tests establish
the app's intent/file/decoder/result behavior and configured flags; they do not
exercise a handset camera app, lens, Android's cross-process grant enforcement,
or user photographs. Native UI and core CI results, failed attempts and exact
APK/signing identity belong in the draft PR. No test count proves optical
accuracy, calibrated acoustics or physical output containment.

The first implementation `749e76c8d31136c6afe44176afb15174ea80333d`
passed main CI and [Android run 39653782287](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39653782287),
including all five camera scenarios. Artifact `12370674645` retained native view
assertions showing unknown hints after Cancel, but its two camera PNGs had the
same SHA-256 `9217a2b0e29c45b70e8ae0498ed859fc68ef74357f74c43a1c01c778ebc5f180`:
the screen recorder captured the prior rendered frame. That PNG is not visual
proof of the canceled state. Preserve it and correct the test recorder before
calling the visual evidence complete; production camera code is unchanged.

The corrected API-36 test recorder explicitly invalidates the app Window,
requires a hardware frame-commit callback and successful PixelCopy, then records
that submitted app buffer. It fails on a missing frame/copy or identical camera
review/Cancel PNGs. [Android ViewTreeObserver](https://developer.android.com/reference/android/view/ViewTreeObserver#registerFrameCommitCallback(java.lang.Runnable))
documents frame submission and its use with PixelCopy for reliable UI captures;
[Android PixelCopy](https://developer.android.com/reference/android/view/PixelCopy)
reads the most recently queued source buffer and reports completion status.
These are rendered app-window pixels, not a physical-display observation.

## Remaining gates

Test Take a TV photo on the user's Android camera, confirm a clear model row is
read, then cancel another capture and check that all hints remain unknown.
Real capture and OS work cancellation, hard memory/latency bounds, iPhone signed
distribution, TV pairing/control and N2b–N5 remain unqualified. Factory and
handoff readiness remain closed. Apple API-key support is a separate pending
distribution issue.
