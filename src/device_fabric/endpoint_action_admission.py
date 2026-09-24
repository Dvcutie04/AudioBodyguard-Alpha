import hashlib
from copy import deepcopy
from dataclasses import replace

from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent import ControllerBoundActionIntent
from src.control.controller_bound_intent_firewall import ControllerBoundIntentFirewall
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.device_fabric.contracts import AuthorizedActionIntent, DeviceState


class EndpointActionVerifier:
    """Reference verifier for the signed SET_VOLUME endpoint request."""

    def __init__(self, *, policy_verifiers, controller_verifiers, active_controller_authority=None):
        self._firewall = ControllerBoundIntentFirewall(
            policy_verifiers=policy_verifiers,
            controller_verifiers=controller_verifiers,
            active_controller_authority=active_controller_authority,
        )

    def admit(self, *, signed_intent, capability_lease, controller_evidence, authorized_intent, now):
        if (type(signed_intent) is not ControllerBoundActionIntent
                or type(capability_lease) is not SignedCapabilityLease
                or type(controller_evidence) is not SignedControllerLeaseEvidence
                or type(authorized_intent) is not AuthorizedActionIntent):
            raise ValueError("endpoint action evidence is invalid")
        signed = deepcopy(signed_intent)
        capability = deepcopy(capability_lease)
        controller = deepcopy(controller_evidence)
        action = deepcopy(authorized_intent)
        before = action.expected_pre_state
        target = action.target_state
        if type(before) is not DeviceState or type(target) is not DeviceState:
            raise ValueError("endpoint action states are invalid")
        if signed.expected_pre_state_digest is None:
            raise ValueError("endpoint action signed prestate is required")
        if signed.operation != "SET_VOLUME" or type(signed.parameters) is not dict or set(signed.parameters) != {"volume"}:
            raise ValueError("endpoint action operation is unsupported")
        volume = signed.parameters["volume"]
        if type(volume) is not int or not 0 <= volume <= 100:
            raise ValueError("endpoint action volume is invalid")
        try:
            if before.state_digest != signed.expected_pre_state_digest or target != replace(before, volume=volume):
                raise ValueError("endpoint action physical state mismatch")
            authorization_digest = hashlib.sha256(signed.canonical_bytes).hexdigest()
            expected = (
                signed.intent_id, signed.device_id, signed.operation.lower(), signed.operation.lower(),
                signed.transaction_id, capability.payload_digest, capability.payload_digest,
                authorization_digest, signed.expires_at, signed.resource_id,
                signed.controller_id, signed.fencing_token,
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("endpoint action payload is invalid") from exc
        observed = (
            action.intent_id, action.device_id, action.action, action.operation,
            action.transaction_id, action.lease_id, action.capability_digest,
            action.authorization_digest, action.deadline_at, action.controller_resource_id,
            action.controller_id, action.controller_fencing_token,
        )
        if observed != expected or type(action.controller_fencing_token) is not int:
            raise ValueError("endpoint action binding mismatch")
        if self._firewall.validate(signed, capability, controller, now=now) is not signed:
            raise ValueError("endpoint action authorization rejected")
        return action
