# AQSS endpoint native boundary v1: synthetic conformance traces

**Status:** Test-only contract for `AQSS/owned-pcm-gain-lab/v1`. A fixture result of `eligible: true` means only that the synthetic trace satisfies this reference oracle. It is not a native retirement certificate, an acoustic observation, an authorization, or a production readiness decision. `EndpointHandoffBarrier.is_ready()` and the production execution guard remain closed.

## Fixture format

`endpoint_native_boundary_v1.json` has `schema_version: 1`, `capability: test_only_trace_conformance`, a `baseline`, and named `cases`. For each case, deep-copy the baseline, then update only the immediate fields of each named section with `case.changes[section]`. Arrays such as `native.work` are replaced as whole values. Compare the result with `case.eligible`. A missing, unknown, or malformed field must not acquire a positive meaning from a default in a real backend.

The `claim`, `activation`, and `submission` sections bind the resource, request, successor controller/token, runtime, stream, route/epoch, and continuity identity. The reference oracle requires exact equality at activation and submission. A real executor must recheck those facts where the native submission is enforced; cached callbacks and a prior activation check are insufficient.

The `native` section names admission/publication closure, producer registry completeness, cut closure, qualified backend/route enforcement, retained and closed generations, registered old work, output disposition, and the actual route. Every retained generation must be closed. Every registered work item at or below the retired generation must be settled. `app_queue_empty` is deliberately ignored: it cannot retire a scheduled descendant or a buffered native frame. `completed` and `discarded` are only synthetic accepted dispositions; an actual backend must separately qualify the meaning and physical boundary of either operation. `partial` and `unknown` block.

The `protection` and `times` sections require protection at both checks and a certificate lifetime that still covers submission. A real implementation must bind the clock domain, current protection evidence, pending successor, protected continuity, and separately authorized native evidence issuer. The fixture boolean flags cannot prove any of those facts.

## Qualification boundary

This v1 fixture describes one owned resource. It does not establish shared-handle conflict-domain isolation, complete discovery of unregistered native work, route atomicity during delayed OS notification, downstream acoustic settlement, independent physical observation, cross-process persistence, or rollback-resistant continuity. Those cases stay unsupported until an actual backend and its declared operating envelope are measured and reviewed. A successful synthetic case cannot be passed to the endpoint barrier or used to remove its production guard. iPhone/iOS and Android require independent native build, lifecycle, output, and physical qualification against the same intended contract.
