"""Transaction and receipt definitions for the device fabric layer."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Transaction:
    """Represents a transaction request sent across the device fabric."""

    transaction_id: str
    intent_digest: str
    capability_lease: Any
    target_device_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    nonce: Optional[str] = None
    signature: Optional[str] = None


@dataclass
class TransactionReceipt:
    """Represents the execution receipt returned by a device or adapter."""

    transaction_id: str
    status: str
    device_id: str
    execution_result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    receipt_signature: Optional[str] = None


class PhysicalTransactionManager:
    """Manages execution and tracking of physical device transactions."""

    def __init__(self, fabric_router=None):
        self.fabric_router = fabric_router
        self.active_transactions: Dict[str, Transaction] = {}

    def execute_transaction(self, transaction: Transaction) -> TransactionReceipt:
        """Execute a physical transaction on the target device."""
        self.active_transactions[transaction.transaction_id] = transaction
        return TransactionReceipt(
            transaction_id=transaction.transaction_id,
            status="SUCCESS",
            device_id=transaction.target_device_id,
            execution_result={"status": "completed"}
        )
