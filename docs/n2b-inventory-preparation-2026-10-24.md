# N2b inventory preparation — October 24, 2026

The next physical engineering gate remains the inventory of an actual owned
output path. The existing [qualification record](n2b-lab-qualification-record.md)
defines that inventory and the later trials. The owner has now confirmed two
phones as the available setup. The earlier account identifies Android and
iPhone; an actual mobile output resource and independent capture setup remain
unselected. The next research package reviews an owned mobile path under the
existing charter. Older TV connector and phone-input observations do not fill
those fields.

This increment adds a private JSON inventory template and a local checker for
the eight existing inventory rows. It implements the existing protocol without
adding a backend or OS audio API. The mobile app remains at 0.31, with its
existing 0.25 app flow. There is no new installer for this preparation step.

## Fill a private record from observations

Copy [n2b-inventory.template.json](n2b-inventory.template.json) into a private
working directory outside the public repository. Set `revision` to the exact
40-character lowercase source SHA used for this inventory, and `observed_on`
to the actual observation date in `YYYY-MM-DD` form. Keep `qualified` and
`production_ready` explicitly false.

Each section has a `status`, `details` and `evidence_refs` list. Leave its
status `unknown` when unobserved; use `unavailable` when the relevant equipment
or evidence is absent. Both keep the inventory incomplete. Use `reported`
only after recording the actual observations, with a useful description and
at least one evidence reference. A filled description does not establish
that every requested property is correct or sufficient; the reviewer must
check the content against the qualification record.

| Section | Contents required by the existing protocol |
| --- | --- |
| `host` | Lab owner, OS/kernel/build, compiler, backend library and driver versions |
| `output_route` | Output make/model/firmware, exact physical route, mixer and named native resource |
| `format` | Negotiated input/output format, channels, sample rate, periods/buffers, write mode and conversions/plugins |
| `capture` | Separate capture interface, loopback/acoustic path, calibration and capture-clock provenance |
| `ownership` | Exclusive owner process, start/stop, process identity and authoritative admission/hold cut |
| `work` | Background jobs, callbacks, ramps, queued descendants, native buffers and inherited route ownership |
| `continuity` | Monotonic clock epochs, bounded trace storage, crash recovery and tamper/rollback protection |
| `consent` | Capture consent, safe test volume and secure test environment |

The owner has supplied the initial availability answer: two phones, with no
computer in the reported setup. The next inventory needs their current OS
builds, the proposed owned output route and the other phone's possible capture
configuration. Use existing equipment; no purchase or particular customer
accessory is assumed.
Leave negotiation and implementation observations unknown until they can be
observed. Record a constraint rather than inventing a compatible configuration.

## Bind references to local evidence bytes

Keep stable, redacted evidence files in an explicitly chosen private directory.
Each object in the record's `evidence` list has an `id`, relative `path`, and
lowercase `sha256`. Section `evidence_refs` name those IDs. One file can support
several sections. Every registered file must be referenced. The checker reads
only those files; it does not run commands embedded in a record, discover
devices, contact a server, record audio or attempt playback.

For example, an evidence entry has this shape; replace the digest placeholder
with the SHA-256 of the actual retained file:

```json
{"id":"host-os","path":"redacted/host-os.txt","sha256":"<64 lowercase hexadecimal characters>"}
```

Run from the repository root, supplying actual paths and the source revision:

```sh
python3 tools/n2b_inventory_record.py /path/to/private/inventory.json --evidence-root=/path/to/private/evidence --expected-revision=<exact-40-character-SHA>
```

The record is bounded to 128 KiB, each evidence file to 1 MiB, and the evidence
list to 32 entries. Files must be ordinary regular files beneath the chosen
root; absolute paths, traversal components, symlink children, duplicate IDs or
paths, unresolved references and mismatched hashes cannot complete the check.
Keep the directory stable while checking it. This is a local consistency check,
not a concurrency, authenticity or tamper-resistance mechanism. Do not place
raw recordings, credentials or unredacted personal/system data in a public PR.
The command prints field-level problems without printing descriptions or paths.

| Result | Exit code | Meaning |
| --- | ---: | --- |
| `INCOMPLETE_INVENTORY` | 1 | Observations, references or local evidence are missing; this is the expected result for the template |
| `INVALID_INVENTORY` | 2 | The record is malformed, contradictory, out of bounds, contains a prohibited claim, or does not match its evidence hashes |
| `INVENTORY_RECORDED_UNVERIFIED` | 0 | All eight sections are reported, references resolve and local file hashes match; their content and hardware remain unverified |

Unknown JSON fields and duplicate keys are rejected. Expected-revision checking
compares the supplied strings; it does not authenticate a Git source or prove
that hardware ran it. Hash matching establishes byte consistency only. A
successful result is never adapter authorization, independent acquisition,
calibration, physical qualification or successor readiness. N2b–N5 stay pending.

## Verification and next dependency

Synthetic tests cover reported versus unknown/unavailable observations, missing
and changed evidence, source/date identity, malformed structures and JSON,
path containment, symlink rejection, read bounds and the unverified result.
They contain no real hardware observations. Source-bound execution results
belong to the draft PR for this increment.

Next, refresh the exact owned-mobile backend and acquisition questions, then
complete and review the actual phone/output/capture inventory. The roadmap
requires the owner's switch to 6 Astra Max and confirmation before that new
substantive research. A new OS/driver adapter and independent physical
measurements follow separately. Signed iPhone distribution still needs the
owner's Apple setup.
