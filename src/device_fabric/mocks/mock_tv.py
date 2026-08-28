"""
AQSS-36-OMEGA
Physical Truth Runtime — Mock TV Device Implementation
"""
from __future__ import annotations
from typing import Optional, Mapping
from datetime import datetime, timezone

from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    AuthorizedActionIntent,
    ContractViolation,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceState,
    DeviceType,
    canonical_digest,
    utc_now,
)


class MockTV:
    """Mock implementation of a physical TV device for testing contract execution."""

    def __init__(self, device_id: str):
        self._identity = DeviceIdentity(
            device_id=device_id,
            device_type=DeviceType.TV,
            vendor="MockCorp",
            model="MockTV-2000",
            firmware_version="1.0.0-mock",
        )
        self._state = DeviceState(
            power=True,
            volume=50.0,
            muted=False,
            input_source="HDMI_1",
        )
        self._execution_history: set[str] = set()

    @property
    def identity(self) -> DeviceIdentity:
        return self._identity

    @property
    def state(self) -> DeviceState:
        return self._state

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            device_id=self._identity.device_id,
            capabilities=frozenset({
                "set_power",
                "set_volume",
                "set_muted",
                "set_input_source",
            }),
        )

    def execute_intent(
        self,
        intent: AuthorizedActionIntent,
        transaction_digest: Optional[str] = None,
        capability_digest: Optional[str] = None,
    ) -> ActuationReceipt:
        """
        Execute an authorized action intent and generate an ActuationReceipt.
        """
        if intent.device_id != self._identity.device_id:
            raise ContractViolation("Intent device_id mismatch with target device")

        # Capture pre-actuation physical state digest
        pre_state_digest = self._state.state_digest

        # Handle duplicate absorption or state mutation
        status = ActuationStatus.EXECUTED
        if intent.intent_id in self._execution_history:
            status = ActuationStatus.DUPLICATE_ABSORBED
        else:
            self._execution_history.add(intent.intent_id)
            # Apply target state mutation
            self._state = intent.target_state

        now = utc_now()
        post_state_digest = self._state.state_digest

        # Derive fallbacks for transaction lineage if omitted by caller
        resolved_tx_digest = (
            transaction_digest
            or canonical_digest("TX_FALLBACK", intent.intent_id, now.isoformat())
        )
        resolved_cap_digest = (
            capability_digest
            or canonical_digest("CAP_FALLBACK", self._identity.device_id, intent.operation)
        )
        receipt_id = canonical_digest("RECEIPT", intent.intent_id, now.isoformat())

        return ActuationReceipt(
            receipt_id=receipt_id,
            action_id=intent.intent_id,
            device_id=self._identity.device_id,
            intent_digest=intent.authorization_digest,
            status=status,
            timestamp=now,
            transaction_digest=resolved_tx_digest,
            capability_digest=resolved_cap_digest,
            pre_state_digest=pre_state_digest,
            post_state_digest=post_state_digest,
            physical_state_digest=post_state_digest,
            executed_at=now,
        )
