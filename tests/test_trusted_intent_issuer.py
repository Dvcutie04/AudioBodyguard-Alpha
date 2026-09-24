from src.control.crypto_identity import KeyPair
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent
from src.extensions.normalization import NormalizedCandidate
from src.control.intent_issuer import TrustedIntentIssuer


def test_trusted_intent_issuer_binds_candidate_lease_and_signature():
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    issuer=TrustedIntentIssuer(key,protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_1",transaction_id="txn_1",nonce="intent_nonce_1",created_at=110.0,expires_at=120.0)
    assert isinstance(intent,SignedActionIntent)
    assert intent.device_id==candidate.target_id
    assert intent.operation==candidate.operation
    assert intent.parameters==dict(candidate.parameters)
    assert intent.issuer_id==key.key_id
    assert intent.capability_lease_digest==lease.payload_digest
    assert intent.policy_digest=="policy_digest_1"
    assert intent.protocol_version=="AQSS-1"
    assert intent.signature
    assert key.public_verifier.verify(intent.canonical_bytes,intent.signature)


def test_trusted_intent_issuer_rejects_candidate_lease_device_mismatch():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_2",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    issuer=TrustedIntentIssuer(key,protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_2",transaction_id="txn_2",nonce="intent_nonce_2",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_foreign_lease_before_signing():
    import pytest
    lease_key=KeyPair.generate("foreign_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_foreign",issuer_id=lease_key.key_id)
    lease_signature=lease_key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        def sign(self,data):
            raise AssertionError("signing must not occur for foreign lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_3",transaction_id="txn_3",nonce="intent_nonce_3",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_protocol_mismatch_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-0",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_protocol",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("signing must not occur for protocol mismatch")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_4",transaction_id="txn_4",nonce="intent_nonce_4",created_at=110.0,expires_at=120.0)


import pytest

@pytest.mark.parametrize("created_at,expires_at",[(90.0,120.0),(110.0,210.0)])
def test_trusted_intent_issuer_rejects_intent_outside_lease_window_before_signing(created_at,expires_at):
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_window",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("signing must not occur outside lease validity window")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_window",transaction_id="txn_window",nonce="intent_nonce_window",created_at=created_at,expires_at=expires_at)


def test_trusted_intent_issuer_rejects_invalid_lease_signature_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_bad_sig",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for invalid lease signature")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_bad_lease_sig",transaction_id="txn_bad_lease_sig",nonce="intent_nonce_bad_lease_sig",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_empty_policy_digest_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_policy",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur without policy provenance")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="",intent_id="intent_empty_policy",transaction_id="txn_empty_policy",nonce="intent_nonce_empty_policy",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_empty_transaction_id_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_txn",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur without transaction provenance")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_empty_txn",transaction_id="",nonce="intent_nonce_empty_txn",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_empty_intent_id_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_intent_id",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur without intent identity")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="",transaction_id="txn_empty_intent_id",nonce="intent_nonce_empty_intent_id",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_empty_nonce_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_intent_nonce",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur without replay nonce")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_empty_nonce",transaction_id="txn_empty_nonce",nonce="",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_empty_operation_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_empty_operation",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="",parameters={})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur without an operation")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_empty_operation",transaction_id="txn_empty_operation",nonce="intent_nonce_empty_operation",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_empty_extension_id_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_empty_extension",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur without extension identity")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_empty_extension",transaction_id="txn_empty_extension",nonce="intent_nonce_empty_extension",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_nonpositive_validity_window_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_bad_time_shape",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with a nonpositive validity window")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_bad_time_shape",transaction_id="txn_bad_time_shape",nonce="intent_nonce_bad_time_shape",created_at=120.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_reversed_validity_window_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_reversed_time",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with a reversed validity window")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_reversed_time",transaction_id="txn_reversed_time",nonce="intent_nonce_reversed_time",created_at=130.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_whitespace_extension_id_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_whitespace_extension",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="   ",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with whitespace-only extension identity")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_whitespace_extension",transaction_id="txn_whitespace_extension",nonce="intent_nonce_whitespace_extension",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_whitespace_operation_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_whitespace_operation",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="   ",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with whitespace-only operation")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_whitespace_operation",transaction_id="txn_whitespace_operation",nonce="intent_nonce_whitespace_operation",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_whitespace_policy_digest_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_whitespace_policy_digest",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with whitespace-only policy digest")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="   ",intent_id="intent_whitespace_policy_digest",transaction_id="txn_whitespace_policy_digest",nonce="intent_nonce_whitespace_policy_digest",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_whitespace_transaction_id_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_whitespace_transaction",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with whitespace-only transaction id")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_whitespace_transaction",transaction_id="   ",nonce="intent_nonce_whitespace_transaction",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_whitespace_intent_id_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_whitespace_intent",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with whitespace-only intent id")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="   ",transaction_id="transaction_whitespace_intent",nonce="intent_nonce_whitespace_intent",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_whitespace_nonce_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_whitespace_intent_nonce",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with whitespace-only nonce")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_whitespace_nonce",transaction_id="transaction_whitespace_nonce",nonce="   ",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_nan_created_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_nan_created_at",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with NaN created_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_nan_created_at",transaction_id="transaction_nan_created_at",nonce="intent_nonce_nan_created_at",created_at=float("nan"),expires_at=120.0)


def test_trusted_intent_issuer_rejects_nan_expires_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_nan_expires_at",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with NaN expires_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_nan_expires_at",transaction_id="transaction_nan_expires_at",nonce="intent_nonce_nan_expires_at",created_at=110.0,expires_at=float("nan"))


def test_trusted_intent_issuer_rejects_positive_infinity_created_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_positive_infinity_created_at",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with positive-infinity created_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_positive_infinity_created_at",transaction_id="transaction_positive_infinity_created_at",nonce="intent_nonce_positive_infinity_created_at",created_at=float("inf"),expires_at=120.0)


def test_trusted_intent_issuer_rejects_positive_infinity_expires_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_positive_infinity_expires_at",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with positive-infinity expires_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_positive_infinity_expires_at",transaction_id="transaction_positive_infinity_expires_at",nonce="intent_nonce_positive_infinity_expires_at",created_at=110.0,expires_at=float("inf"))


def test_trusted_intent_issuer_rejects_negative_infinity_created_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_negative_infinity_created_at",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with negative-infinity created_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_negative_infinity_created_at",transaction_id="transaction_negative_infinity_created_at",nonce="intent_nonce_negative_infinity_created_at",created_at=float("-inf"),expires_at=120.0)


def test_trusted_intent_issuer_rejects_negative_infinity_expires_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_negative_infinity_expires_at",issuer_id=key.key_id)
    lease_signature=key.sign(SignedCapabilityLease(**lease_data,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with negative-infinity expires_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_negative_infinity_expires_at",transaction_id="transaction_negative_infinity_expires_at",nonce="intent_nonce_negative_infinity_expires_at",created_at=110.0,expires_at=float("-inf"))


def test_trusted_intent_issuer_rejects_nan_lease_issued_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=float("nan"),expires_at=200.0,nonce="lease_nonce_nan_issued_at",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with NaN lease issued_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_nan_lease_issued_at",transaction_id="transaction_nan_lease_issued_at",nonce="intent_nonce_nan_lease_issued_at",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_nan_lease_expires_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=float("nan"),nonce="lease_nonce_nan_expires_at",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with NaN lease expires_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_nan_lease_expires_at",transaction_id="transaction_nan_lease_expires_at",nonce="intent_nonce_nan_lease_expires_at",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_positive_infinity_lease_issued_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=float("inf"),expires_at=200.0,nonce="lease_nonce_positive_infinity_issued_at",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with positive-infinity lease issued_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_positive_infinity_lease_issued_at",transaction_id="transaction_positive_infinity_lease_issued_at",nonce="intent_nonce_positive_infinity_lease_issued_at",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_positive_infinity_lease_expires_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=float("inf"),nonce="lease_nonce_positive_infinity_expires_at",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with positive-infinity lease expires_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_positive_infinity_lease_expires_at",transaction_id="transaction_positive_infinity_lease_expires_at",nonce="intent_nonce_positive_infinity_lease_expires_at",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_negative_infinity_lease_issued_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=float("-inf"),expires_at=200.0,nonce="lease_nonce_negative_infinity_issued_at",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with negative-infinity lease issued_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_negative_infinity_lease_issued_at",transaction_id="transaction_negative_infinity_lease_issued_at",nonce="intent_nonce_negative_infinity_lease_issued_at",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_negative_infinity_lease_expires_at_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=float("-inf"),nonce="lease_nonce_negative_infinity_expires_at",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with negative-infinity lease expires_at")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_negative_infinity_lease_expires_at",transaction_id="transaction_negative_infinity_lease_expires_at",nonce="intent_nonce_negative_infinity_lease_expires_at",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_zero_duration_lease_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=100.0,nonce="lease_nonce_zero_duration",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with zero-duration capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_zero_duration_lease",transaction_id="transaction_zero_duration_lease",nonce="intent_nonce_zero_duration_lease",created_at=100.0,expires_at=101.0)


def test_trusted_intent_issuer_rejects_reversed_lease_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease_data=dict(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=101.0,expires_at=100.0,nonce="lease_nonce_reversed",issuer_id=key.key_id)
    unsigned_lease=SignedCapabilityLease(**lease_data,signature="")
    lease_signature=key.sign(unsigned_lease.canonical_bytes)
    lease=SignedCapabilityLease(**lease_data,signature=lease_signature)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur with reversed capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_reversed_lease",transaction_id="transaction_reversed_lease",nonce="intent_nonce_reversed_lease",created_at=100.0,expires_at=101.0)


def test_trusted_intent_issuer_authenticates_forged_lease_before_device_semantics():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_WRONG",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_forged_device_mismatch",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return False
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=RecordingVerifier()
        def sign(self,data):
            raise AssertionError("intent signing must not occur for forged capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_forged_device_mismatch",transaction_id="transaction_forged_device_mismatch",nonce="intent_nonce_forged_device_mismatch",created_at=110.0,expires_at=120.0)
    assert len(calls)==1


def test_trusted_intent_issuer_authenticates_forged_lease_before_protocol_semantics():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-WRONG",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_forged_protocol_mismatch",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return False
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=RecordingVerifier()
        def sign(self,data):
            raise AssertionError("intent signing must not occur for forged capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_forged_protocol_mismatch",transaction_id="transaction_forged_protocol_mismatch",nonce="intent_nonce_forged_protocol_mismatch",created_at=110.0,expires_at=120.0)
    assert len(calls)==1


def test_trusted_intent_issuer_authenticates_forged_lease_before_temporal_semantics():
    import math
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=float("nan"),expires_at=200.0,nonce="lease_nonce_forged_temporal",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return False
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=RecordingVerifier()
        def sign(self,data):
            raise AssertionError("intent signing must not occur for forged capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_forged_temporal",transaction_id="transaction_forged_temporal",nonce="intent_nonce_forged_temporal",created_at=110.0,expires_at=120.0)
    assert len(calls)==1


def test_trusted_intent_issuer_authenticates_forged_lease_before_expires_at_semantics():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=float("nan"),nonce="lease_nonce_forged_expires_at",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return False
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=RecordingVerifier()
        def sign(self,data):
            raise AssertionError("intent signing must not occur for forged capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_forged_expires_at",transaction_id="transaction_forged_expires_at",nonce="intent_nonce_forged_expires_at",created_at=110.0,expires_at=120.0)
    assert len(calls)==1


def test_trusted_intent_issuer_authenticates_forged_lease_before_reversed_interval_semantics():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=200.0,expires_at=100.0,nonce="lease_nonce_forged_reversed_interval",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return False
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=RecordingVerifier()
        def sign(self,data):
            raise AssertionError("intent signing must not occur for forged capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_forged_reversed_interval",transaction_id="transaction_forged_reversed_interval",nonce="intent_nonce_forged_reversed_interval",created_at=110.0,expires_at=120.0)
    assert len(calls)==1


def test_trusted_intent_issuer_authenticates_forged_lease_before_zero_duration_interval_semantics():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=100.0,nonce="lease_nonce_forged_zero_duration",issuer_id=key.key_id,signature="forged_signature")
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return False
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=RecordingVerifier()
        def sign(self,data):
            raise AssertionError("intent signing must not occur for forged capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_forged_zero_duration",transaction_id="transaction_forged_zero_duration",nonce="intent_nonce_forged_zero_duration",created_at=100.0,expires_at=101.0)
    assert len(calls)==1


def test_trusted_intent_issuer_rejects_reversed_signed_lease_as_invalid_authority_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=200.0,expires_at=100.0,nonce="lease_nonce_reversed_authority",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for reversed capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease validity window is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_reversed_authority",transaction_id="transaction_reversed_authority",nonce="intent_nonce_reversed_authority",created_at=110.0,expires_at=120.0)


def test_trusted_intent_issuer_rejects_zero_duration_signed_lease_as_invalid_authority_before_signing():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=100.0,nonce="lease_nonce_zero_duration_authority",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id="aqss_policy_authority"
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for zero-duration capability lease")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease validity window is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_zero_duration_authority",transaction_id="transaction_zero_duration_authority",nonce="intent_nonce_zero_duration_authority",created_at=100.0,expires_at=101.0)


def test_trusted_intent_issuer_verifies_valid_lease_exactly_once_before_signing():
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_verify_once",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return key.public_verifier.verify(data,signature)
    class RecordingSigner:
        key_id=key.key_id
        public_verifier=RecordingVerifier()
        def sign(self,data):
            return key.sign(data)
    issuer=TrustedIntentIssuer(RecordingSigner(),protocol_version="AQSS-1")
    result=issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_verify_once",transaction_id="transaction_verify_once",nonce="intent_nonce_verify_once",created_at=110.0,expires_at=120.0)
    assert result.intent_id=="intent_verify_once"
    assert len(calls)==1


def test_trusted_intent_issuer_verifies_exact_lease_bytes_and_signature_before_signing():
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_exact_verify",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    expected_bytes=lease.canonical_bytes
    expected_signature=lease.signature
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    calls=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            calls.append((data,signature))
            return key.public_verifier.verify(data,signature)
    class RecordingSigner:
        key_id=key.key_id
        public_verifier=RecordingVerifier()
        def sign(self,data):
            return key.sign(data)
    issuer=TrustedIntentIssuer(RecordingSigner(),protocol_version="AQSS-1")
    issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_exact_verify",transaction_id="transaction_exact_verify",nonce="intent_nonce_exact_verify",created_at=110.0,expires_at=120.0)
    assert calls==[(expected_bytes,expected_signature)]


def test_trusted_intent_issuer_rejects_reversed_intent_as_invalid_request_before_containment():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_reversed_intent",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id=key.key_id
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for reversed intent validity window")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="intent validity window is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_reversed_request",transaction_id="transaction_reversed_request",nonce="intent_nonce_reversed_request",created_at=150.0,expires_at=140.0)


def test_trusted_intent_issuer_rejects_zero_duration_intent_as_invalid_request_before_containment():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_zero_duration_intent",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id=key.key_id
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for zero-duration intent validity window")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="intent validity window is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_zero_duration_request",transaction_id="transaction_zero_duration_request",nonce="intent_nonce_zero_duration_request",created_at=150.0,expires_at=150.0)


def test_trusted_intent_issuer_verifies_lease_before_signing_intent():
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_verify_before_sign",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    events=[]
    class RecordingVerifier:
        def verify(self,data,signature):
            events.append("verify")
            return key.public_verifier.verify(data,signature)
    class RecordingSigner:
        key_id=key.key_id
        public_verifier=RecordingVerifier()
        def sign(self,data):
            events.append("sign")
            return key.sign(data)
    issuer=TrustedIntentIssuer(RecordingSigner(),protocol_version="AQSS-1")
    issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_verify_before_sign",transaction_id="transaction_verify_before_sign",nonce="intent_nonce_verify_before_sign",created_at=110.0,expires_at=120.0)
    assert events==["verify","sign"]


def test_trusted_intent_issuer_rejects_invalid_signed_lease_before_invalid_intent_semantics():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=200.0,expires_at=100.0,nonce="lease_nonce_invalid_authority_precedence",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id=key.key_id
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur when authority and intent intervals are invalid")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="capability lease validity window is invalid"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_invalid_authority_precedence",transaction_id="transaction_invalid_authority_precedence",nonce="intent_nonce_invalid_authority_precedence",created_at=150.0,expires_at=140.0)


def test_trusted_intent_issuer_rejects_well_formed_intent_before_lease_as_containment_failure():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_before_lease_containment",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id=key.key_id
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for out-of-lease intent")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="intent validity window must be contained within capability lease validity window"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_before_lease",transaction_id="transaction_before_lease",nonce="intent_nonce_before_lease",created_at=90.0,expires_at=110.0)


def test_trusted_intent_issuer_rejects_well_formed_intent_after_lease_as_containment_failure():
    import pytest
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_after_lease_containment",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    class ForbiddenSigner:
        key_id=key.key_id
        public_verifier=key.public_verifier
        def sign(self,data):
            raise AssertionError("intent signing must not occur for out-of-lease intent")
    issuer=TrustedIntentIssuer(ForbiddenSigner(),protocol_version="AQSS-1")
    with pytest.raises(ValueError,match="intent validity window must be contained within capability lease validity window"):
        issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_after_lease",transaction_id="transaction_after_lease",nonce="intent_nonce_after_lease",created_at=190.0,expires_at=210.0)


def test_trusted_intent_issuer_allows_intent_exactly_matching_lease_validity_window():
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="lease_nonce_exact_boundary",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25})
    issuer=TrustedIntentIssuer(key,protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,lease=lease,policy_digest="policy_digest_1",intent_id="intent_exact_boundary",transaction_id="transaction_exact_boundary",nonce="intent_nonce_exact_boundary",created_at=100.0,expires_at=200.0)
    assert intent.created_at==100.0
    assert intent.expires_at==200.0
    assert key.public_verifier.verify(intent.canonical_bytes,intent.signature)


def test_trusted_intent_issuer_never_promotes_candidate_parameter_authority_metadata():
    key=KeyPair.generate("aqss_policy_authority")
    lease=SignedCapabilityLease(device_id="device_1",capability_digest="trusted_cap_digest",firmware_identity="fw_1",protocol_version="AQSS-1",issued_at=100.0,expires_at=200.0,nonce="trusted_lease_nonce",issuer_id=key.key_id,signature="")
    lease.signature=key.sign(lease.canonical_bytes)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device_1",operation="SET_VOLUME",parameters={"volume":25,"issuer_id":"attacker_issuer","policy_digest":"attacker_policy","capability_lease_digest":"attacker_lease","transaction_id":"attacker_transaction","signature":"attacker_signature"})
    issuer=TrustedIntentIssuer(key,protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,lease=lease,policy_digest="trusted_policy",intent_id="trusted_intent",transaction_id="trusted_transaction",nonce="trusted_intent_nonce",created_at=110.0,expires_at=190.0)
    assert intent.issuer_id==key.key_id
    assert intent.policy_digest=="trusted_policy"
    assert intent.capability_lease_digest==lease.payload_digest
    assert intent.transaction_id=="trusted_transaction"
    assert intent.signature!="attacker_signature"
    assert key.public_verifier.verify(intent.canonical_bytes,intent.signature)
