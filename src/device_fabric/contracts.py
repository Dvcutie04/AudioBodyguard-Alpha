class ContractViolation(Exception):
    """Raised when a device fabric contract invariant is violated."""
    pass


class CommitCertificate:
    def __init__(
        self,
        verification_result,
        observed_state_digest: str | None = None,
        *args,
        **kwargs
    ):
        if (
            getattr(verification_result, "status", None) == VerificationStatus.VERIFIED
            and not observed_state_digest
        ):
            raise ContractViolation("Verified commit requires observed state digest")
        self.verification_result = verification_result
        self.observed_state_digest = observed_state_digest


class CapabilityLease:
    def __init__(self, nonce: str | None = None, *args, **kwargs):
        if not nonce:
            raise ContractViolation("Capability lease requires nonce for replay protection")
        self.nonce = nonce
