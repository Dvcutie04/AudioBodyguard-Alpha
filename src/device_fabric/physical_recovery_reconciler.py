import math

from .contracts import DeviceState, PhysicalSnapshot
from .physical_recovery_store import PhysicalRecoveryStore


class PhysicalRecoveryReconciler:
    def __init__(self, store: PhysicalRecoveryStore):
        self.store = store

    def reconcile(self, transaction_id, snapshot: PhysicalSnapshot):
        if type(snapshot) is not PhysicalSnapshot:
            raise TypeError("snapshot must be PhysicalSnapshot")
        if type(snapshot.state) is not DeviceState:
            raise TypeError("snapshot state must be DeviceState")
        if type(snapshot.epoch) is not int or snapshot.epoch < 0:
            raise ValueError("invalid snapshot epoch")
        if type(snapshot.observed_at) not in (int, float) or not math.isfinite(snapshot.observed_at) or snapshot.observed_at < 0:
            raise ValueError("invalid snapshot observation time")
        record = self.store.get(transaction_id)
        if record is None:
            raise KeyError("physical recovery record not found")
        if snapshot.device_id != record.device_id:
            raise ValueError("snapshot device does not match recovery record")
        if record.precondition_epoch is None:
            raise ValueError("recovery record lacks precondition epoch")
        if snapshot.epoch <= record.precondition_epoch:
            raise ValueError("snapshot epoch is not newer than recovery precondition")
        return self.store.reconcile_observation(
            transaction_id,
            observed_state_digest=snapshot.state_digest,
            observed_at=snapshot.observed_at,
        )
