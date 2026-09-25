# Continue in a-Shell from a separate verified checkout

The GitHub repository is public. Cloning it for these checks requires no personal
access token. This creates a new folder alongside the existing phone checkout;
it does not merge or overwrite unexported phone work. Keep the original checkout
until any phone-only differences have been reviewed.

Run each command as one physical line. Start in a-Shell's Documents directory:

```sh
cd ~/Documents
```

Use the folder name below only if it does not already exist. If it exists from an
earlier attempt, inspect it or use a new name; do not delete it to retry.

```sh
lg2 clone https://github.com/Dvcutie04/AudioBodyguard-Alpha.git AQSS_Verified_20260925
```

Continue only when cloning succeeds:

```sh
cd AQSS_Verified_20260925
```

Record the actual checked-out revision. Compare it with the latest master
handoff and its GitHub Actions result, because main may advance after this guide:

```sh
lg2 rev-parse HEAD
```

Use the phone's existing Python environment; do not replace its dependencies as
part of this transfer:

```sh
python3 tools/generate_native_feedback_contracts.py --check
```

```sh
PYTHONPATH=. python3 -m pytest -q --tb=short
```

At this checkpoint the expected software evidence is `NATIVE_CONTRACTS_CURRENT`
and 1,641 Python tests. Report the actual output, including any error or warning;
hosted success is not confirmation of phone execution. If imports differ on the
phone, inspect that difference before installing or replacing anything.

The 26 scripted C cases run separately in hosted CI, normally and with memory/UB
instrumentation. The Python command does not compile them. Swift and Android CI
checks are synthetic contract tests, not installed applications or physical
qualification. Production readiness remains unavailable.

Subsequent a-Shell work should use the new folder after its checks pass. A later
three-way comparison can carry over any additional phone-only edits from the
original directory. Do not use a hard reset, broad cleanup, or a blanket add from
the old Documents repository to accomplish this transfer.
