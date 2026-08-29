import time
import pytest
from src.control.capability_lease import SignedCapabilityLease
from src.control.intent_firewall import IntentFirewall
from src.control.crypto_identity import KeyPair


@pytest.fixture
def crypto_env():
    governor_key = KeyPair.generate()
    verifier = governor_key.public_verifier
    firewall = IntentFirewall(trusted_verifiers={governor_key.key_id: verifier})

    now = time.time()
    raw_lease_data = {
        "subject_id": "tx_manager_001",
        "object_id": "speaker_living_room",
        "capability_digest": "cap_sha256_audio_control",
        "firmware_identity": "omega-v1.0",
        "protocol_version": "1.0",
        "issued_at": now,
        "expires_at": now + 60.0,
        "nonce": "nonce_lease_001",
        "issuer_id": governor_key.key_id
    }

    lease_canonical = SignedCapabilityLease(**raw_lease_data, signature="").canonical_bytes
    return firewall, governor_key, raw_lease_data, lease_canonical
