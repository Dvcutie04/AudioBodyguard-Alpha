# Photo retry guidance — October 21, 2026

Version 0.14 follows the cleanup/readiness work in 0.12 and 0.13. A completed
OCR request can produce no text, unrelated text, or only ambiguous TV fields.
The existing screens still ask the user to check the details when every field
is unknown. That message gives no useful next step.

## Research and decision

| Primary source | Application |
| --- | --- |
| [ML Kit text recognition on Android](https://developers.google.com/ml-kit/vision/text-recognition/v2/android) | A successful result can contain zero text blocks. Image resolution and focus affect recognition; request completion alone does not establish useful TV details. |
| [Apple recognizing text in images](https://developer.apple.com/documentation/vision/recognizing-text-in-images) | Vision yields recognized observations that the application interprets. Recognition and application-level identification remain separate steps. |

The selected design combines the existing bounded OCR collection, conservative
field parser, and a result message selected from the accepted hints. After a
valid collection is parsed, an absent brand, model and IP hint produces:

“No TV details found. Try a closer photo of the model label or IP address row.”

This is an application interpretation, not a diagnosis of the camera, image
quality or recognition engine. It also covers unrelated or conflicting text.
One supported field is enough to retain the ordinary review message; missing
fields remain unknown. Collection rejection, decode/framework failure, timeout
and real worker cleanup retain their existing messages and ownership rules.

The existing Choose a photo action provides the retry. Automatically retaking
or importing would add an unsolicited operation. New heuristic parsing or a
second recognition pass would change uncertainty and resource use without
evidence that it is needed. No new dependency, timer, image retention, network
request or device-control path is introduced. This increment makes no handset
latency, battery, memory, image-accuracy or physical-connection claim.

## Verification contract

Native tests are published before the production message change. Android uses
the real system photo picker, app decoder and ML Kit. iPhone uses real Photos
imports and Vision. Synthetic images cover a blank photo, readable unrelated
text, a brand-only photo and the existing full label. Dated iPhone fixtures are
selected by their unique imported date rather than a guessed grid position.

Regression checkpoint `188b046f8b5be71a456d606ea4934c20c359a289` changes
native tests, synthetic fixtures and workflow triggers while retaining 0.13's
production behavior. Android run `39714590655`, job `119613561129`, compiled
and then failed the new blank-photo expectation. Its captured native hierarchy
shows “Check these details” alongside three unknown fields after recognition
completed. The failure is the expected result message, not a picker or compiler
failure. Verification artifact `12398667887` preserves that observation.

iPhone run `39714590745`, job `119613561478`, compiled and passed all 81
package tests. Its six-test denied/idle/photo walkthrough reported exactly two
assertion failures: the missing retry message for the blank and unrelated
photos. The dated picker selection, unknown fields, brand-only review,
replacement cancellation, reselection and Clear assertions passed. The
granted-microphone stage was skipped after this expected photo failure.

Both no-detail cases must show the retry message with all three hints unknown.
The brand-only case must retain its supported brand and ordinary review notice.
The iPhone walkthrough replaces a recognized full label with no-detail photos
to reject stale hints, then imports the full label again. Existing replacement
Cancel, reselect and Clear remain required. Android retains its over-limit,
full-image camera, cleanup, delayed-provider, overlap and lifecycle checks.

Synthetic test images and observer code must remain outside the delivered APK.
The original opening poster remains fixed. Exact red/green runs, APK provenance
and final source identity belong to the draft PR. These software checks do not
qualify real-photo accuracy, TV pairing, physical audio or signed iPhone
distribution.
