from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    AuthorizedActionIntent,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceState,
    DeviceType,
)


@dataclass
class MockTV:
    """Mock TV device that simulates a real television device."""

    device_id: str = "tv_mock_001"
    identity: DeviceIdentity = field(default_factory=DeviceIdentity)
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)
    state: DeviceState = field(default_factory=DeviceState)

    def __post_init__(self):
        self.identity = DeviceIdentity(
            device_id=self.device_id,
            device_type=DeviceType.TV,
            name=f"Mock TV {self.device_id}",
            vendor="MockCorp",
        )
        self.capabilities = DeviceCapabilities(
            device_id=self.device_id,
            capabilities={
                "set_power",
                "set_volume",
                "set_muted",
                "set_input_source",
                "power",
                "volume",
                "channel",
                "input_source",
            },
            supported_actions=["set_power", "set_volume", "set_muted", "set_input_source"],
        )
        self.state = DeviceState(power=False, volume=50.0, muted=False, input_source="HDMI_1")

    async def apply_state(self, target_state: DeviceState) -> None:
        self.state = target_state

    async def execute_intent(self, intent: Any) -> bool:
        if hasattr(intent, "target_state") and isinstance(intent.target_state, DeviceState):
            self.state = intent.target_state
        elif hasattr(intent, "target_state") and isinstance(intent.target_state, dict):
            power = intent.target_state.get("power", self.state.power)
            vol = intent.target_state.get("volume", self.state.volume)
            muted = intent.target_state.get("muted", self.state.muted)
            chan = intent.target_state.get("channel", self.state.channel)
            inp = intent.target_state.get("input_source", self.state.input_source)
            self.state = DeviceState(
                power=power,
                volume=vol,
                muted=muted,
                channel=chan,
                input_source=inp,
            )
        return True


class MockTVAdapter:
    """Adapter for executing intents on MockTV."""

    def __init__(self, device_id: str = "tv_mock_001"):
        self.device = MockTV(device_id=device_id)
        self.executed_intents: Dict[str, AuthorizedActionIntent] = {}

    async def execute_intent(
        self,
        intent: AuthorizedActionIntent,
        transaction_digest: str = "",
        capability_digest: str = "",
    ) -> ActuationReceipt:
        """Execute an authorized action intent on the device."""
        intent_key = intent.intent_id
        action_id_val = intent.operation or intent.action or intent.intent_id

        # Check for duplicate intents (idempotency)
        if intent_key in self.executed_intents:
            receipt = ActuationReceipt(
                receipt_id=f"rcpt_{intent_key}_dup",
                intent_id=intent.intent_id,
                action_id=action_id_val,
                device_id=intent.device_id or self.device.identity.device_id,
                status=ActuationStatus.DUPLICATE_ABSORBED,
                timestamp=datetime.now(timezone.utc).timestamp(),
            )
            setattr(receipt, "transaction_digest", transaction_digest)
            setattr(receipt, "capability_digest", capability_digest)
            return receipt

        # Record the executed intent
        self.executed_intents[intent_key] = intent

        # Apply target state to device
        if intent.target_state:
            if isinstance(intent.target_state, DeviceState):
                await self.device.apply_state(intent.target_state)
            elif isinstance(intent.target_state, dict):
                await self.device.execute_intent(intent)

        # Create receipt with lineage metadata
        receipt = ActuationReceipt(
            receipt_id=f"rcpt_{intent.intent_id}",
            intent_id=intent.intent_id,
            action_id=action_id_val,
            device_id=intent.device_id or self.device.identity.device_id,
            status=ActuationStatus.EXECUTED,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )
        setattr(receipt, "transaction_digest", transaction_digest)
        setattr(receipt, "capability_digest", capability_digest)

        return receipt
