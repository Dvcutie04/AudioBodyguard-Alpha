import time
import uuid
from typing import Optional, Tuple

from src.device_fabric.contracts import (
    AuthorizedActionIntent, CapabilityLease, DeviceState, TransactionState
)
from src.device_fabric.transaction import PhysicalTransactionManager


class FabricRouter:
    """
    The main routing gateway for the AQSS-36-OMEGA Physical Commit Layer.
    Translates raw commands into cryptographically bound intents.
    """
    def __init__(self, transaction_manager: PhysicalTransactionManager):
        self.tx_manager = transaction_manager
        
    async def dispatch_intent(
        self, 
        device_id: str, 
        operation: str, 
        expected_pre_state: DeviceState,
        target_state: DeviceState,
        lease_duration: float = 5.0
    ) -> Tuple[TransactionState, Optional[str]]:
        """
        Packages a physical command into an authorized intent and dispatches it.
        """
        now = time.time()
        
        # 1. Synthesize the Cryptographic Intent
        intent = AuthorizedActionIntent(
            intent_id=f"req_{uuid.uuid4().hex[:8]}",
            device_id=device_id,
            operation=operation,
            target_state=target_state,
            expected_pre_state=expected_pre_state,
            authorization_digest="auth_sha256_placeholder", # Phase 3 IAM integration
            deadline_at=now + 10.0
        )
        
        # 2. Mint an Ephemeral Capability Lease
        lease = CapabilityLease(
            device_id=device_id,
            capability_digest="cap_sha256_placeholder",
            firmware_identity="omega-v1.0",
            protocol_version="1.0",
            issued_at=now,
            expires_at=now + lease_duration,
            nonce=uuid.uuid4().hex,
            issuer="omega_router"
        )
        
        # 3. Hand off to the Verification Engine
        return await self.tx_manager.execute_transaction(intent, lease, now)
