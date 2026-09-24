import inspect
import json
from dataclasses import MISSING, fields, replace

import pytest

from src.control.controller_bound_intent import ControllerBoundActionIntent
from src.control.crypto_identity import KeyPair


def _raw(key_id):
    return {
        "intent_id":"intent-controller-7",
        "device_id":"device-tv-living-room",
        "operation":"POWER_OFF",
        "parameters":{"reason":"user_request"},
        "issuer_id":key_id,
        "policy_digest":"policy-digest-7",
        "capability_lease_digest":"capability-digest-7",
        "resource_id":"tv:living-room",
        "controller_id":"phone-a",
        "controller_lease_digest":"controller-evidence-digest-7",
        "fencing_token":7,
        "created_at":101.0,
        "expires_at":120.0,
        "nonce":"intent-nonce-7",
        "transaction_id":"transaction-7",
        "protocol_version":"AQSS-1",
    }


def test_controller_binding_fields_are_required_and_canonical():
    key=KeyPair.generate(key_id="aqss-policy-authority")
    intent=ControllerBoundActionIntent(**_raw(key.key_id))
    required={"resource_id","controller_id","controller_lease_digest","fencing_token"}
    definitions={item.name:item for item in fields(ControllerBoundActionIntent)}
    assert required <= definitions.keys()
    assert all(definitions[name].default is MISSING and definitions[name].default_factory is MISSING for name in required)
    expected=json.dumps(_raw(key.key_id),sort_keys=True,separators=(",",":")).encode("utf-8")
    assert intent.canonical_bytes==expected
    with pytest.raises(TypeError):
        ControllerBoundActionIntent(**{k:v for k,v in _raw(key.key_id).items() if k!="controller_id"})


def test_controller_binding_cannot_be_changed_after_intent_signing():
    key=KeyPair.generate(key_id="aqss-policy-authority")
    unsigned=ControllerBoundActionIntent(**_raw(key.key_id))
    signed=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    assert key.public_verifier.verify(signed.canonical_bytes,signed.signature)
    alterations=(
        replace(signed,resource_id="tv:bedroom"),
        replace(signed,controller_id="phone-b"),
        replace(signed,controller_lease_digest="controller-evidence-digest-8"),
        replace(signed,fencing_token=8),
    )
    for tampered in alterations:
        assert not key.public_verifier.verify(tampered.canonical_bytes,tampered.signature)


def test_controller_bound_intent_rejects_malformed_authority_data():
    key=KeyPair.generate(key_id="aqss-policy-authority")
    text_fields=("intent_id","device_id","operation","issuer_id","policy_digest","capability_lease_digest","resource_id","controller_id","controller_lease_digest","nonce","transaction_id","protocol_version")
    invalid=[{name:"   "} for name in text_fields]
    invalid.extend((
        {"fencing_token":True},
        {"fencing_token":0},
        {"fencing_token":-1},
        {"created_at":True},
        {"created_at":float("nan")},
        {"created_at":float("inf")},
        {"expires_at":float("nan")},
        {"expires_at":float("inf")},
        {"expires_at":101.0},
        {"expires_at":100.0},
        {"parameters":[]},
        {"parameters":{1:"invalid-key"}},
        {"parameters":{"value":object()}},
        {"signature":None},
    ))
    for changes in invalid:
        with pytest.raises(ValueError):
            ControllerBoundActionIntent(**{**_raw(key.key_id),**changes})


def test_controller_bound_intent_signs_optional_expected_pre_state_digest():
    key=KeyPair.generate(key_id="aqss-policy-authority")
    digest="b" * 64
    raw={**_raw(key.key_id),"expected_pre_state_digest":digest}
    unsigned=ControllerBoundActionIntent(**raw)
    expected=json.dumps(raw,sort_keys=True,separators=(",",":")).encode("utf-8")
    assert unsigned.canonical_bytes==expected
    signed=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    assert key.public_verifier.verify(signed.canonical_bytes,signed.signature)
    assert not key.public_verifier.verify(replace(signed,expected_pre_state_digest="c" * 64).canonical_bytes,signed.signature)
    for invalid in ("","b" * 63,"B" * 64,"g" * 64,7):
        with pytest.raises(ValueError,match="expected_pre_state_digest"):
            ControllerBoundActionIntent(**{**_raw(key.key_id),"expected_pre_state_digest":invalid})
