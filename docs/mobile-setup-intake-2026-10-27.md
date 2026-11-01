# Private mobile setup report intake

October 27, 2026. This implements the existing eight-row N2b inventory protocol
while the actual phone report is unavailable. It adds a local engineering tool,
not a phone feature, audio adapter or new installer. Android's delivered build
remains 0.37/build 40; iPhone/iPad source remains 0.38.0/build 1.

## From reviewed text to an incomplete draft

The [mobile intake tool](../tools/mobile_setup_intake.py) reads the exact UTF-8
text shared from **Review setup report**. It supports standalone Android and
iPhone/iPad worksheets, Android worksheets with an inventory or quiet-check
attachment, and iPhone/iPad worksheets with session details. It requires the
operator's exact expected platform, version and build, plus a declared source
revision. It does not infer a Git revision from a version label.

The tool validates the ordered worksheet fields, native note escaping and
160-UTF-16-unit limits, explicit uncertainty statements, dates and attachment
envelope/build matching. Attachment metadata and worker traces remain opaque:
their contents are not independently validated, interpreted as measurements or
promoted into inventory facts. A matching label is not sender authentication
or proof that particular source code ran. Forged text can still match a format.

The whole input is bounded to 64 KiB plus one optional final LF. Native limits
also apply to each recognized report type: standalone 4,096 UTF-16 units /
8,192 UTF-8 bytes; Android inventory combination 32,768 / 65,536; Android quiet
combination 49,152 / 49,152; iPhone combination 16,384 / 32,768. Attachments retain
their own smaller bounds. UTF-16 limits count supplementary characters twice.
Only LF line endings are accepted; BOMs, unsafe controls, alternate escaping,
ambiguous extra report envelopes and unsupported versions are rejected. One
editor-added final LF is accepted and remains part of the source hash.

Notes review time and attachment capture time remain separate untrusted
phone-clock labels. Neither becomes an observation date, native timestamp,
ordering guarantee, clock mapping or latency calculation.

## Private engineering workflow

Save the actual shared text in a stable private directory outside this public
repository. Select a new output directory under an existing private parent.
Run one command, replacing all paths and expected labels with the actual
reviewed build's values:

```sh
python3 tools/mobile_setup_intake.py /private/phone-report.txt --output-dir=/private/new-review --expected-platform=Android --expected-version=0.37-quiet-setup-live-input --expected-build=40 --source-revision=cfeb12b3f91c681c953d10ec559195935532363f
```

For the inspected iPhone/iPad source, the expected labels are `iPhone/iPad`,
`0.38.0`, build `1`; its declared source is the exact reviewed iOS commit.
This CLI is an engineering aid. The owner only needs to share the report;
no computer purchase or terminal use on their phone is assumed.

Successful intake creates a private directory (mode 0700) containing files
(mode 0600):

| File | Meaning |
| --- | --- |
| `phone-report.txt` | Exact original input bytes, including an optional final LF |
| `intake.json` | Report labels, separate phone-clock dates, decoded notes, attachment envelope/hash and explicit unverified status |
| `inventory.json` | Existing N2b schema, all eight section statuses `unknown`, declared revision, unknown observation date and a reference to the source file's SHA-256 |

The inventory includes quoted notes as proposals and review prompts, never
as completed observations. No note, port kind or framework return count can
automatically complete a row. `qualified` and `production_ready` remain false.
The original bytes bind to the existing inventory checker's local hash check:

```sh
python3 tools/n2b_inventory_record.py /private/new-review/inventory.json --evidence-root=/private/new-review --expected-revision=cfeb12b3f91c681c953d10ec559195935532363f
```

Its expected result is `INCOMPLETE_INVENTORY`, exit 1. The operator still needs
to review and fill the exact host, route, format, acquisition, ownership,
outstanding work, continuity and consent requirements in the
[qualification record](n2b-lab-qualification-record.md). Hash matching establishes
byte consistency, not authenticity or physical qualification.

Input must be an ordinary regular file; a final-component symlink, directory
or FIFO is rejected before reading. Use stable private directories: this is
not a concurrent filesystem or hostile-directory transaction protocol. The
tool validates and serializes before creating output, rejects existing output
paths, and removes only its own newly written files on a write failure. It
does not overwrite an existing review. Normal and failure output use fixed
status text without printing report contents, notes or private paths.

| Exit | Status | Result |
| --- | --- | --- |
| 0 | `PHONE_REPORT_RECORDED_UNVERIFIED` | Private draft created; inventory remains incomplete |
| 2 | `INVALID_PHONE_REPORT` | File, expected identity or supported report envelope failed; no output created |
| 3 | `PHONE_INTAKE_NOT_SAVED` | New output could not be saved; existing work is preserved |

## Verification and remaining work

Tests-first and final source-bound receipts belong to the draft PR. Tests
cover all five supported worksheet combinations, wrong/cross-build input,
uncertainty changes, duplicate fields/envelopes, quoted Unknown versus an
unanswered note, escapes and Unicode bounds, independent clocks, exact source
hashes, private file modes, missing/symlink/FIFO/oversized input, no overwrite,
write-failure cleanup and integration with the existing inventory checker.
Synthetic text is explicitly labelled as such and supplies no owner facts.

The tool was also exercised against the already inspected Android 0.37
normal/large quiet-setup artifacts and iPhone/iPad 0.38 combined-copy artifacts.
Those are emulator/Simulator observations, not the owner's arrangement.
No real phone report, recording, backend API or physical measurement was added.
N2b–N5 and signed iPhone distribution remain pending.
