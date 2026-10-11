# Repository-wide adverse findings review — September 30, 2026

Scope baseline: development tree matching remote revision e29e3bd6090efd401e53952b2611d36bf4e1fda8 (558 tracked files, including 441 Python files). Inventory and structural searches span the repository; automated Python analysis covers every tracked Python file. Manual review concentrates on authority, canonical inputs, replay/persistence, physical truth, credentials, native lifecycle/permissions, web boundaries, workflow supply chain and picture navigation. This is not a line-by-line formal proof of all 558 files or a scientific validation of every research model.

## Confirmed repairs

| Finding | Impact and repair | Evidence |
|---|---|---|
| High: credential-like IBM API key in research client | Removed literal; read IBM_CLOUD_API_KEY at call time; missing key fails before network; bounded timeout; removed token-prefix logging. No attempt made to determine whether the old key is active. **Owner must revoke/rotate if valid: Git history still contains it.** | Missing-key test reproduced a network attempt before repair, then passed with zero network calls. No credential bytes reproduced in this report. |
| Medium: legacy proposal gateway claimed EXECUTED without a physical adapter | Returns AUTHENTICATED_PROPOSAL instead. It has no production/native callers in the searched tree and no physical verification authority. | Regression first reproduced false execution label, then passed. |
| Medium: malformed attestation crashes / nonfinite signed confidence accepted | Exact payload shape, bounded text, exact positive integer sequence/time, bounded finite confidence and signature syntax; invalid data rejects rather than raises. | Reproduced malformed and NaN cases, then passed. |
| Medium: interlock consumed unauthenticated sequence | Authenticate before replay/interlock decisions; denied inputs cannot poison replay membership. High-water sequence plus bounded last-sequence membership replaces accumulating set. | Forged input previously prevented a subsequent valid proposal; repaired test passes. Process-local replay is still not a durable production fence. |
| Usability: new-brand routes absent | Added Philips, Sharp, Roku-branded TV and Insignia choices; 39 evidenced routes / 344 numbered pictures. Added Philips remote and Fire TV initial account approval, with explicit OS/model qualifications. | New-brand catalog regression failed first, passed after expansion; native walkthroughs exercise new Philips route. |

The production factory still raises `production endpoint execution boundary is required`; EndpointHandoffBarrier.is_ready remains closed. No repair opens an actuation path or turns proposal authentication into physical authorization.

## Automated results and triage

- Baseline tracked-Python Bandit analysis: 441 files, 38,047 lines, no parse failures; 0 high and 18 medium findings, plus low-severity assertions/debug patterns. This count is tool output, **not** the severity of all confirmed findings above. The credential literal was found by manual review and identifier-aware AST search.
- Ten SQL-concatenation warnings use a constant column list and parameterized values in physical_recovery_store; no caller-controlled SQL fragment was established.
- Two urlopen warnings concern fixed HTTPS research/webhook endpoints. The IBM client was repaired separately for its actual credential/timeout problem. Webhook error-message redaction and redirect restrictions merit a dedicated deployment review before use with secrets.
- Six ElementTree warnings parse CI-generated UI hierarchy evidence; these tools are not hostile-client XML endpoints. Treat downloaded evidence as untrusted if the scope changes.
- pip-audit resolved requirements for this Linux review environment and reported no known vulnerabilities. This is a dated resolution, not coverage of every version permitted by broad ranges, iOS distributions, Gradle/ML Kit dependencies or unreported vulnerabilities.
- Full regression after repairs: 1,808 tests and 14 subtests passed. Catalog generators and diff/shell syntax checks passed. Final native build/walkthrough and artifact evidence is recorded in PR #32.

## Remaining adverse findings / qualification debt

| Priority | Finding | Required next step |
|---|---|---|
| High owner action | Potential exposed IBM credential remains in historical commits and earlier distributed copies. | Revoke/rotate at IBM if it was valid. Do not merely delete local text. Do not rewrite shared history without a coordinated plan. |
| High before production | Physical containment, native endpoint execution, independent acoustic observation and installed-device recovery remain unqualified. | Keep gates closed; qualify both phone platforms with an independent observer and auditable finality. |
| High performance uncertainty | Previous hosted Android Roku trace reported 51/53 janky frames, median 73 ms, p95 200 ms, software-rendered GPU anomalies. | Installed-device profiling is required. Removed unnecessary choice/redraw paths do not prove the user's jitter is fully solved. |
| Medium research boundary | Legacy mean-frequency/loudness voice enrollment is not secure speaker authentication; HMAC “public_verifier” in reference code shares signing material; TVDriver is a simulated logging stub. | Do not expose these as enrolled identity, asymmetric public verification or real dispatch. Existing P-256 endpoint trust is a separate mechanism. |
| Medium development-service exposure | Local feedback HTTP utility has profile scoping, not full authentication/TLS/CSRF/time-budget protection for hostile network clients. | Keep trusted-local scope; dedicated deployment threat model before remote exposure. |
| Medium supply chain | Python requirements are broad and Actions use version tags rather than immutable SHAs; no complete Android dependency advisory scan performed. | Reproducible platform-aware locks/SBOM and pinned action review, tested independently. No blanket version upgrade claimed here. |
| Medium UI fidelity | Brand-only evidence does not determine every model, firmware, region or language. Photo 2 exposes no model/software value. | Obtain System > About/model evidence. Illustrations remain explicitly labeled; never treat a brand choice or completed tutorial as connection evidence. |
| Medium usability/privacy | Actual VoiceOver/TalkBack, recognition consent/revocation on installed hardware and multilingual task success are not qualified by simulator taps. | Human assistive-technology and target-device tests; no hidden microphone/automatic pairing promises. |

No secret was contacted, no customer device was scanned, no remote service was published, and no production barrier was relaxed. The audit does not assert that no other bug can exist.
