import uuid
from src.device_fabric.adapter import DeviceAdapter
from src.device_fabric.contracts import (
    DeviceIdentity,
    DeviceType,
    DeviceCapabilities,
    DeviceState,
    ActuationReceipt,
    VerificationResult,
)


class MockTVAdapter(DeviceAdapter):
    def __init__(self, device_id: str = "mock_tv_01"):
        self.identity = DeviceIdentity(
            device_id=device_id,
            device_type=DeviceType.TV,
            manufacturer="AQSS_Mock",
            model="Deterministic_TV_v1",
        )
        self.caps = DeviceCapabilities()
        self.state = DeviceState(power=True, volume=50.0, muted=False)
        self.executed_intents = set()

    async def discover(self) -> DeviceIdentity:
        return self.identity

    async def capabilities(self) -> DeviceCapabilities:
        return self.caps

    async def observe_state(self) -> DeviceState:
        return self.state

    async def execute(self, action_id: str, intent_digest: str, command: str, payload: dict) -> ActuationReceipt:
        # Idempotency Check: action_id + device_id + intent_digest
        idempotency_key = f"{action_id}:{self.identity.device_id}:{intent_digest}"
        if idempotency_key in self.executed_intents:
            return ActuationReceipt(
                receipt_id=str(uuid.uuid4()),
                action_id=action_id,
                device_id=self.identity.device_id,
                intent_digest=intent_digest,
                status="DUPLICATE_ABSORBED",
            )

        if command == "REDUCE_VOLUME":
            delta = payload.get("delta_db", 0.0)
            if delta > self.caps.max_volume_delta_db:
                return ActuationReceipt(
                    receipt_id=str(uuid.uuid4()),
                    action_id=action_id,
                    device_id=self.identity.device_id,
                    intent_digest=intent_digest,
                    status="REJECTED_CAPABILITY_EXCEEDED",
                )
            new_vol = max(0.0, self.state.volume - delta)
            self.state = DeviceState(power=self.state.power, volume=new_vol, muted=self.state.muted)
            self.executed_intents.add(idempotency_key)
            return ActuationReceipt(
                receipt_id=str(uuid.uuid4()),
                action_id=action_id,
                device_id=self.identity.device_id,
                intent_digest=intent_digest,
                status="EXECUTED",
            )

        return ActuationReceipt(
            receipt_id=str(uuid.uuid4()),
            action_id=action_id,
            device_id=self.identity.device_id,
            intent_digest=intent_digest,
            status="UNSUPPORTED_COMMAND",
        )

    async def verify(self, expected: DeviceState) -> VerificationResult:
        observed = await self.observe_state()
        is_equal = (observed.volume == expected.volume) and (observed.power == expected.power)
        return VerificationResult(
            verified=is_equal,
            expected_state=expected,
            observed_state=observed,
            error_message=None if is_equal else f"Expected volume {expected.volume}, got {observed.volume}",
        )

    async def rollback(self, previous: DeviceState, lineage_digest: str) -> ActuationReceipt:
        self.state = previous
        return ActuationReceipt(
            receipt_id=str(uuid.uuid4()),
            action_id=f"rollback_{lineage_digest[:8]}",
            device_id=self.identity.device_id,
            intent_digest=lineage_digest,
            status="ROLLED_BACK",
        )
