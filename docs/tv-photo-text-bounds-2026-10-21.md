# TV photo text collection limits

October 21, 2026. Candidate 0.8 follows the 0.7 VIZIO-label increment.
Both native photo paths previously kept only the first 100 recognized rows
before parsing. That could hide a later conflicting label. The iPhone path
also silently omitted an observation when no top text candidate existed.

## Research and decision

| Primary source refreshed | Consequence |
| --- | --- |
| [ML Kit result extraction and image guidelines](https://developers.google.com/ml-kit/vision/text-recognition/v2/android) | Process its block/line results lazily. Reject an oversized result instead of presenting a truncated prefix. A closer, focused image can help recognition; it does not guarantee accuracy. |
| [Apple Vision text observations](https://developer.apple.com/documentation/vision/recognizing-text-in-images) and [top candidates](https://developer.apple.com/documentation/vision/vnrecognizedtextobservation/topcandidates(_:)) | A request returns observations and a candidate array may contain fewer items than requested. Preserve a missing candidate as a failed review rather than dropping that observation. |

The 100-row and 8,192-byte limits are AQSS presentation policy, not limits
promised by either SDK. Keep the bundled Android recognizer, local iPhone
Vision request, explicit photo selection and 2,048-pixel bitmap bound. No new
network service, permission, persistent photo/text store or output API is added.

## Input boundary

`boundedTVPhotoText` collects at most 100 recognized rows and 8,192 UTF-8 bytes,
including inserted newline separators. Overflow, a missing or blank candidate,
or an embedded line separator rejects the whole collection. It never returns
a shortened prefix. Empty observation collections remain empty. Iteration
stops at the first rejection, including the 101st row, without examining the
rest of the result. The parser independently applies the same text and line
budget to direct callers; CRLF counts as one separator. LF, CR, vertical tab,
form feed, NEL, line separator and paragraph separator count as line breaks.

The native views use this collector before constructing hints. Rejected
collections keep brand/model/IP unknown and ask for a closer photo of the model
or IP address row. Valid bounded input retains explicit review and the existing
unverified connection. No confidence threshold or guessed replacement is added.

This closes omission introduced by our own collector. It cannot detect text
that the recognition SDK never reported, a confidently wrong character, or a
photograph of another device. It does not establish completeness of the image,
authenticated TV identity, pairing, connectivity or authority to control output.

## Verification and limits

The tests-only source 4e46da71e902f4598f9a2905b037d7220c159623 adds one
over-100-row behavior to each native package. Its
[red run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39621433487)
is separate from corrected source.
Further checks cover the exact row/UTF-8 boundaries, separator overhead,
missing/blank/multiline candidates, hidden conflicts and early termination.
The existing native Vision synthetic-image test must use the same collector.
The Android walkthrough selects both the ordinary synthetic image and a
text-heavy image through the system picker and bundled ML Kit, checks review
or rejection respectively, clears/cancels, and leaves connection unverified.
The additional 2,048-square grayscale PNG contains 135 fictional rows in
three separated columns and 2,953 authored UTF-8 bytes. Its SHA-256 is
4817b4d8cba2b418d6a3bb22f43f6b5b5bbfa8ff75c62c3faeb5f1fac479dd5a.
It was rendered from exact test text with Pillow and DejaVu Sans Mono. The
native Vision test must observe a genuinely over-budget result before
asserting rejection. Both PNGs are test resources excluded from shipped apps.

The first dense limit fixture in source 277be36159e56169181ac49492b238a712027bd7
did not meet that precondition: Vision returned 94 observations and 944 UTF-8
bytes instead of the 10,367 authored bytes. The native test failed at its
actual-overflow assertion in runs 39623571969 and 39623572004. Replace that
fixture with larger, separated rows; retain the same 100-row/8,192-byte policy
and actual-overflow assertion. This is a test-image correction, not a claim
that OCR reports every row in an arbitrary photo.

Exact source identities, failed and passing native/CI jobs, APK signature and
byte identity belong to the completed draft PR. Tests of supplied recognizer
rows are deterministic software checks, not real-photo coverage or measured
phone accuracy. SDK memory/time, installed-phone resource budgets, microphone
and physical output, signed iPhone installation and N2b–N5 remain pending.

The collector limits additional application-owned text work; it does not limit
the recognition SDK's internal allocations or execution time. No performance
target is claimed without handset measurement. Apple signing setup proceeds
separately from this input-only build.
