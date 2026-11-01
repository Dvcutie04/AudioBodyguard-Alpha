# iPhone and iPad combined setup report

October 27, 2026. This continues directly from the verified iOS 0.37 output-details
phase under the owner's instruction to start the next available phase without
routine confirmation. iPhone/iPad source is 0.38.0/build 1; Android's delivered
0.36 APK is unchanged by this increment.

## Explicit handoff

Sound → Output details → Refresh details → Review output details → Add setup
notes carries that exact typed snapshot into the existing optional worksheet.
The handoff is an in-memory value within the same presentation owner. It does
not query the session again, serialize a handle, open audio I/O or automatically
fill any proposed arrangement. A second queued tap cannot open another draft.

The snapshot's original capture time and text remain separate from the later
notes-review time. Both are unauthenticated phone-clock dates; neither is an
audio timestamp, age guarantee or clock mapping. The installed build envelopes
must match byte for byte, including canonically equivalent Unicode spellings.

Reports without output details preserve the original v1 envelope and 4,096
UTF-16 / 8,192 UTF-8 bounds. An explicitly included snapshot uses v2, a separate
historical-snapshot section and 16,384 UTF-16 / 32,768 UTF-8 bounds. The original
typed snapshot is copied verbatim once. Route, format, independent capture,
calibration, consent and physical protection remain unknown or not collected.

## Draft and review behavior

- Clear notes keeps the included snapshot.
- Remove output details keeps all notes.
- Back from review returns to the same draft; Back from the form closes that
  draft and returns to its immediate output-details parent.
- The reviewed combined report survives rotation and backgrounding unchanged.
  The parent's live snapshot may clear independently. A worksheet copy is
  historical and never turns stale metadata into fresh playback authority.
- Closing the worksheet or parent, or starting a new process, discards the
  draft and its included snapshot. The ordinary standalone worksheet starts
  without an attachment.
- Share is explicit. Native Copy must equal the actual reviewed preview, with
  the original snapshot checked separately against its pre-handoff preview.

The largest accessibility text size uses a short Share title with the full
accessible label. No source recording, port identifiers or raw system logs
are included. Existing optional notes retain their 160-unit per-field limit,
control-character normalization and quoting.

## Validation boundary

Tests-first failures and final source-bound Foundation, iPhone/iPad Simulator,
clipboard and unsigned-device-archive receipts belong to the draft PR. Native
tests include the original standalone worksheet's lifecycle and large-text
regression. This is implementation of the existing reviewed metadata/notes
contract; no new audio backend or research approval is introduced. Simulator
observations and unsigned archives are not phone reports or installable iPhone
releases. Signed distribution, actual setup review and N2b–N5 remain pending.
