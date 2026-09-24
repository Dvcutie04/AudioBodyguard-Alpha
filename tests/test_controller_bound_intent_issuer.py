from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent import ControllerBoundActionIntent
from src.control.controller_bound_intent_issuer import ControllerBoundIntentIssuer
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.control.crypto_identity import KeyPair
from src.extensions.normalization import NormalizedCandidate


def _signed_capability(key):
    data=dict(device_id="device-tv-living-room",capability_digest="capability-digest-7",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=90.0,expires_at=200.0,nonce="capability-nonce-7",issuer_id=key.key_id)
    unsigned=SignedCapabilityLease(**data,signature="")
    return SignedCapabilityLease(**data,signature=key.sign(unsigned.canonical_bytes))


def _signed_controller_evidence(key):
    data=dict(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="controller-nonce-7",scope=("SET_VOLUME",))
    unsigned=SignedControllerLeaseEvidence(**data)
    from dataclasses import replace
    return replace(unsigned,signature=key.sign(unsigned.canonical_bytes))


def test_protected_issuer_derives_and_signs_controller_binding():
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability=_signed_capability(policy_key)
    controller=_signed_controller_evidence(controller_key)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="SET_VOLUME",parameters={"volume":25})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-controller-7",transaction_id="transaction-7",nonce="intent-nonce-7",created_at=110.0,expires_at=120.0)
    assert isinstance(intent,ControllerBoundActionIntent)
    assert intent.device_id==candidate.target_id
    assert intent.operation==candidate.operation
    assert intent.parameters==dict(candidate.parameters)
    assert intent.issuer_id==policy_key.key_id
    assert intent.capability_lease_digest==capability.payload_digest
    assert intent.resource_id==controller.resource_id
    assert intent.controller_id==controller.controller_id
    assert intent.controller_lease_digest==controller.evidence_digest
    assert intent.fencing_token==controller.fencing_token
    assert policy_key.public_verifier.verify(intent.canonical_bytes,intent.signature)


def test_protected_issuer_signs_trusted_expected_pre_state_digest():
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability=_signed_capability(policy_key)
    controller=_signed_controller_evidence(controller_key)
    candidate=NormalizedCandidate(extension_id="aqss.ui.media",target_id=capability.device_id,operation="SET_VOLUME",parameters={"volume":21})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-undo",intent_id="intent-undo",transaction_id="transaction-undo",nonce="intent-nonce-undo",created_at=110.0,expires_at=120.0,expected_pre_state_digest="b" * 64)
    assert intent.expected_pre_state_digest=="b" * 64
    assert policy_key.public_verifier.verify(intent.canonical_bytes,intent.signature)


def test_protected_issuer_rejects_invalid_controller_authority_before_signing():
    import pytest
    from dataclasses import replace
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    rogue_key=KeyPair.generate("rogue-controller-authority")
    capability=_signed_capability(policy_key)
    valid_controller=_signed_controller_evidence(controller_key)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="SET_VOLUME",parameters={"volume":25})
    class RecordingSigner:
        key_id=policy_key.key_id
        public_verifier=policy_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return policy_key.sign(data)
    signer=RecordingSigner()
    issuer=ControllerBoundIntentIssuer(signer,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    rogue_unsigned=replace(valid_controller,issuer_id=rogue_key.key_id,signature="")
    rogue=replace(rogue_unsigned,signature=rogue_key.sign(rogue_unsigned.canonical_bytes))
    with pytest.raises(ValueError,match="controller evidence issuer is not trusted"):
        issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=rogue,policy_digest="policy-digest-7",intent_id="intent-untrusted",transaction_id="transaction-untrusted",nonce="intent-nonce-untrusted",created_at=110.0,expires_at=120.0)
    tampered=replace(valid_controller,controller_id="phone-attacker")
    with pytest.raises(ValueError,match="controller evidence signature is invalid"):
        issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=tampered,policy_digest="policy-digest-7",intent_id="intent-tampered",transaction_id="transaction-tampered",nonce="intent-nonce-tampered",created_at=110.0,expires_at=120.0)
    outside_scope=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="POWER_OFF",parameters={})
    with pytest.raises(ValueError,match="candidate operation is outside controller evidence scope"):
        issuer.issue(candidate=outside_scope,capability_lease=capability,controller_evidence=valid_controller,policy_digest="policy-digest-7",intent_id="intent-scope",transaction_id="transaction-scope",nonce="intent-nonce-scope",created_at=110.0,expires_at=120.0)
    assert signer.calls==0


def test_protected_issuer_rejects_malformed_boundary_objects_before_signing():
    import pytest
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability=_signed_capability(policy_key)
    controller=_signed_controller_evidence(controller_key)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="SET_VOLUME",parameters={"volume":25})
    class RecordingSigner:
        key_id=policy_key.key_id
        public_verifier=policy_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return policy_key.sign(data)
    signer=RecordingSigner()
    issuer=ControllerBoundIntentIssuer(signer,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    invalid_cases=(
        dict(candidate=candidate,capability_lease=object(),controller_evidence=controller),
        dict(candidate=object(),capability_lease=capability,controller_evidence=controller),
        dict(candidate=candidate,capability_lease=capability,controller_evidence=object()),
    )
    for index,invalid in enumerate(invalid_cases):
        with pytest.raises(ValueError,match="candidate, capability lease, and controller evidence must have valid types"):
            issuer.issue(**invalid,policy_digest="policy-digest-7",intent_id=f"intent-malformed-{index}",transaction_id=f"transaction-malformed-{index}",nonce=f"intent-nonce-malformed-{index}",created_at=110.0,expires_at=120.0)
    assert signer.calls==0


def test_protected_issuer_enforces_controller_time_containment_before_signing():
    import pytest
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability=_signed_capability(policy_key)
    controller=_signed_controller_evidence(controller_key)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="SET_VOLUME",parameters={"volume":25})
    class RecordingSigner:
        key_id=policy_key.key_id
        public_verifier=policy_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return policy_key.sign(data)
    signer=RecordingSigner()
    issuer=ControllerBoundIntentIssuer(signer,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    for index,(created_at,expires_at) in enumerate(((99.0,110.0),(120.0,131.0))):
        with pytest.raises(ValueError,match="intent validity window must be contained within controller evidence validity window"):
            issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-7",intent_id=f"intent-outside-controller-{index}",transaction_id=f"transaction-outside-controller-{index}",nonce=f"intent-nonce-outside-controller-{index}",created_at=created_at,expires_at=expires_at)
    assert signer.calls==0
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-exact-controller-window",transaction_id="transaction-exact-controller-window",nonce="intent-nonce-exact-controller-window",created_at=100.0,expires_at=130.0)
    assert intent.created_at==100.0
    assert intent.expires_at==130.0
    assert signer.calls==1
    assert policy_key.public_verifier.verify(intent.canonical_bytes,intent.signature)


def test_protected_issuer_rejects_invalid_capability_authority_before_signing():
    import pytest
    from dataclasses import replace
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability=_signed_capability(policy_key)
    controller=_signed_controller_evidence(controller_key)
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="SET_VOLUME",parameters={"volume":25})
    class RecordingSigner:
        key_id=policy_key.key_id
        public_verifier=policy_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return policy_key.sign(data)
    signer=RecordingSigner()
    issuer=ControllerBoundIntentIssuer(signer,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    tampered=replace(capability,capability_digest="attacker-capability")
    with pytest.raises(ValueError,match="capability lease signature is invalid"):
        issuer.issue(candidate=candidate,capability_lease=tampered,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-capability-tampered",transaction_id="transaction-capability-tampered",nonce="intent-nonce-capability-tampered",created_at=110.0,expires_at=120.0)
    wrong_device_unsigned=replace(capability,device_id="device-tv-bedroom",signature="")
    wrong_device=replace(wrong_device_unsigned,signature=policy_key.sign(wrong_device_unsigned.canonical_bytes))
    with pytest.raises(ValueError,match="candidate target does not match capability lease device"):
        issuer.issue(candidate=candidate,capability_lease=wrong_device,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-device-substitution",transaction_id="transaction-device-substitution",nonce="intent-nonce-device-substitution",created_at=110.0,expires_at=120.0)
    wrong_protocol_unsigned=replace(capability,protocol_version="AQSS-2",signature="")
    wrong_protocol=replace(wrong_protocol_unsigned,signature=policy_key.sign(wrong_protocol_unsigned.canonical_bytes))
    with pytest.raises(ValueError,match="capability lease protocol does not match protected intent issuer protocol"):
        issuer.issue(candidate=candidate,capability_lease=wrong_protocol,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-protocol-substitution",transaction_id="transaction-protocol-substitution",nonce="intent-nonce-protocol-substitution",created_at=110.0,expires_at=120.0)
    assert signer.calls==0

def test_protected_issuer_rejects_playback_position_without_trusted_candidate_admission():
    import pytest
    from dataclasses import replace
    policy_key=KeyPair.generate("media-policy-authority")
    controller_key=KeyPair.generate("media-controller-authority")
    capability=_signed_capability(policy_key)
    controller_unsigned=SignedControllerLeaseEvidence(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,issued_at=100.0,expires_at=130.0,issuer_id=controller_key.key_id,nonce="media-controller-nonce",scope=("SET_PLAYBACK_POSITION",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    for operation in ("SET_PLAYBACK_POSITION","set_playback_position","Set_Playback_Position"):
        handcrafted=NormalizedCandidate(extension_id="untrusted.handcrafted",target_id=capability.device_id,operation=operation,parameters={"playback_position_seconds":45.0,"observation_id":"invented-observation","evidence_digest":"a"*64,"observed_monotonic":100.0,"segment_start_seconds":0.0,"segment_end_seconds":45.0,"directive_key":("profile-1",capability.device_id,"show_intro:provider-1","episode-1"),"directive_version":1})
        with pytest.raises(ValueError,match="trusted candidate admission is required"):
            issuer.issue(candidate=handcrafted,capability_lease=capability,controller_evidence=controller,policy_digest="media-policy",intent_id="handcrafted-media-intent",transaction_id="handcrafted-media-transaction",nonce="handcrafted-media-nonce",created_at=110.0,expires_at=120.0)

def test_protected_issuer_rejects_lengthened_media_evidence_deadline():
    import pytest
    from dataclasses import replace
    policy_key=KeyPair.generate("media-deadline-policy-authority")
    controller_key=KeyPair.generate("media-deadline-controller-authority")
    capability=_signed_capability(policy_key)
    controller_unsigned=SignedControllerLeaseEvidence(resource_id="tv:living-room",controller_id="phone-a",fencing_token=8,issued_at=100.0,expires_at=130.0,issuer_id=controller_key.key_id,nonce="media-deadline-controller-nonce",scope=("SET_PLAYBACK_POSITION",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    parameters={"playback_position_seconds":45.0,"observation_id":"observation-deadline-1","evidence_digest":"b"*64,"observed_monotonic":100.0,"evidence_expires_monotonic":100.5,"evidence_clock_domain_id":"process:trusted-test-domain","segment_start_seconds":0.0,"segment_end_seconds":45.0,"directive_key":("profile-1",capability.device_id,"show_intro:provider-1","episode-1"),"directive_version":1}
    admitted=NormalizedCandidate(extension_id="aqss.media.segment",target_id=capability.device_id,operation="SET_PLAYBACK_POSITION",parameters=parameters)
    admission_calls=[]
    def admission(candidate):
        admission_calls.append(candidate)
        return candidate==admitted
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1",candidate_admission=admission)
    lengthened_parameters=dict(parameters)
    lengthened_parameters["evidence_expires_monotonic"]=130.0
    lengthened=NormalizedCandidate(extension_id=admitted.extension_id,target_id=admitted.target_id,operation=admitted.operation,parameters=lengthened_parameters)
    with pytest.raises(ValueError,match="trusted candidate admission rejected candidate"):
        issuer.issue(candidate=lengthened,capability_lease=capability,controller_evidence=controller,policy_digest="media-policy",intent_id="lengthened-media-intent",transaction_id="lengthened-media-transaction",nonce="lengthened-media-nonce",created_at=110.0,expires_at=120.0)
    substituted_parameters=dict(parameters)
    substituted_parameters["evidence_clock_domain_id"]="process:substituted-test-domain"
    substituted=NormalizedCandidate(extension_id=admitted.extension_id,target_id=admitted.target_id,operation=admitted.operation,parameters=substituted_parameters)
    with pytest.raises(ValueError,match="trusted candidate admission rejected candidate"):
        issuer.issue(candidate=substituted,capability_lease=capability,controller_evidence=controller,policy_digest="media-policy",intent_id="substituted-domain-intent",transaction_id="substituted-domain-transaction",nonce="substituted-domain-nonce",created_at=110.0,expires_at=120.0)
    intent=issuer.issue(candidate=admitted,capability_lease=capability,controller_evidence=controller,policy_digest="media-policy",intent_id="admitted-media-intent",transaction_id="admitted-media-transaction",nonce="admitted-media-nonce",created_at=110.0,expires_at=120.0)
    assert admission_calls==[lengthened,substituted,admitted]
    assert intent.parameters["evidence_expires_monotonic"]==100.5
    assert intent.parameters["evidence_clock_domain_id"]=="process:trusted-test-domain"
    assert policy_key.public_verifier.verify(intent.canonical_bytes,intent.signature)

