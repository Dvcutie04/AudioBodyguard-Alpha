import time
import pytest

from src.control.crypto_identity import KeyPair
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent
from src.control.intent_firewall import IntentFirewall, AuthRejectionCode


@pytest.fixture
def crypto_env():
    # 1. Setup Safety Governor Authority Keys
    governor_key = KeyPair.generate()
    verifier = governor_key.public_verifier
    
    # 2. Setup Firewall with Trusted Verifiers
    firewall = IntentFirewall(trusted_verifiers={governor_key.key_id: verifier})
    
    now = time.time()
    
    # 3. Mint a Valid Lease
    raw_lease_data = {
        "device_id": "speaker_living_room",
        "capability_digest": "cap_sha256_audio_control",
        "firmware_identity": "omega-v1.0",
        "protocol_version": "1.0",
        "issued_at": now,
        "expires_at": now + 60.0,
        "nonce": "nonce_lease_001",
        "issuer_id": governor_key.key_id
    }
    
    lease_canonical = SignedCapabilityLease(**raw_lease_data, signature="").canonical_bytes
    lease_signature = governor_key.sign(lease_canonical)
    
    valid_lease = SignedCapabilityLease(**raw_lease_data, signature=lease_signature)
    
    # 4. Mint a Valid Action Intent (Cryptographically Bound to Lease)
    raw_intent_data = {
        "intent_id": "intent_act_100",
        "device_id": "speaker_living_room",
        "operation": "SET_NOISE_ATTENUATION",
        "parameters": {"target_db_reduction": 12.0},
        "issuer_id": governor_key.key_id,
        "policy_digest": "policy_sha256_strict_safety",
        "capability_lease_digest": valid_lease.payload_digest,
        "created_at": now,
        "expires_at": now + 15.0,
        "nonce": "nonce_intent_100",
        "transaction_id": "tx_omega_999",
        "protocol_version": "1.0"
    }
    
    intent_canonical = SignedActionIntent(**raw_intent_data, signature="").canonical_bytes
    intent_signature = governor_key.sign(intent_canonical)
    
    valid_intent = SignedActionIntent(**raw_intent_data, signature=intent_signature)
    
    return governor_key, firewall, valid_lease, valid_intent, raw_lease_data, raw_intent_data


def test_valid_authorization_passes(crypto_env):
    _, firewall, lease, intent, _, _ = crypto_env
    
    result = firewall.validate_intent(intent, lease)
    assert isinstance(result, SignedActionIntent)
    assert result.intent_id == "intent_act_100"


def test_rejects_tampered_parameter(crypto_env):
    governor_key, firewall, lease, _, _, raw_intent = crypto_env
    
    # Adversary tries to change target DB reduction from 12.0 to 99.0 without re-signing
    tampered_intent_dict = {**raw_intent, "parameters": {"target_db_reduction": 99.0}}
    
    # Keep old signature intact
    old_canonical = SignedActionIntent(**raw_intent, signature="").canonical_bytes
    old_sig = governor_key.sign(old_canonical)
    
    tampered_intent = SignedActionIntent(**tampered_intent_dict, signature=old_sig)
    
    result = firewall.validate_intent(tampered_intent, lease)
    assert result == AuthRejectionCode.AUTH_SIGNATURE_INVALID


def test_rejects_device_id_substitution(crypto_env):
    governor_key, firewall, lease, _, _, raw_intent = crypto_env
    
    # Adversary reroutes command to bedroom speaker
    sub_intent_dict = {**raw_intent, "device_id": "speaker_bedroom"}
    sub_canonical = SignedActionIntent(**sub_intent_dict, signature="").canonical_bytes
    sub_sig = governor_key.sign(sub_canonical)
    sub_intent = SignedActionIntent(**sub_intent_dict, signature=sub_sig)
    
    result = firewall.validate_intent(sub_intent, lease)
    assert result == AuthRejectionCode.AUTH_DEVICE_MISMATCH


def test_rejects_unbound_lease_transplant(crypto_env):
    governor_key, firewall, _, intent, raw_lease, _ = crypto_env
    now = time.time()
    
    # Adversary creates a fresh valid lease for a different capability
    rogue_lease_dict = {**raw_lease, "capability_digest": "cap_sha256_unrestricted", "nonce": "nonce_rogue"}
    rogue_canonical = SignedCapabilityLease(**rogue_lease_dict, signature="").canonical_bytes
    rogue_sig = governor_key.sign(rogue_canonical)
    rogue_lease = SignedCapabilityLease(**rogue_lease_dict, signature=rogue_sig)
    
    # Intent does not carry rogue_lease.payload_digest
    result = firewall.validate_intent(intent, rogue_lease)
    assert result == AuthRejectionCode.AUTH_LEASE_MISMATCH


def test_rejects_expired_intent(crypto_env):
    governor_key, firewall, lease, _, _, raw_intent = crypto_env
    
    # Intent expired 10 seconds ago
    expired_dict = {**raw_intent, "expires_at": time.time() - 10.0}
    exp_canonical = SignedActionIntent(**expired_dict, signature="").canonical_bytes
    exp_sig = governor_key.sign(exp_canonical)
    expired_intent = SignedActionIntent(**expired_dict, signature=exp_sig)
    
    result = firewall.validate_intent(expired_intent, lease)
    assert result == AuthRejectionCode.AUTH_EXPIRED


def test_rejects_replayed_nonce(crypto_env):
    _, firewall, lease, intent, _, _ = crypto_env
    
    # First execution succeeds
    res1 = firewall.validate_intent(intent, lease)
    assert isinstance(res1, SignedActionIntent)
    
    # Replayed execution fails
    res2 = firewall.validate_intent(intent, lease)
    assert res2 == AuthRejectionCode.AUTH_REPLAY


def test_rejects_untrusted_issuer(crypto_env):
    rogue_governor = KeyPair.generate()
    _, firewall, lease, _, _, raw_intent = crypto_env
    
    # Rogue governor tries to sign an intent
    rogue_canonical = SignedActionIntent(**raw_intent, signature="").canonical_bytes
    rogue_sig = rogue_governor.sign(rogue_canonical)
    rogue_intent = SignedActionIntent(**{**raw_intent, "issuer_id": rogue_governor.key_id}, signature=rogue_sig)
    
    result = firewall.validate_intent(rogue_intent, lease)
    assert result == AuthRejectionCode.AUTH_ISSUER_UNKNOWN
