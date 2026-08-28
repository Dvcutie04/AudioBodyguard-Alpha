import time
from typing import Tuple, Optional

from src.device_fabric.contracts import (
    AuthorizedActionIntent, 
    CapabilityLease, 
    TransactionState, 
    PreconditionStatus, 
    DeviceState
)
from src.device_fabric.precondition import PreconditionEvaluator
from src.device_fabric.digital_twin import DigitalTwin  # <--- Update this import

# (Remove the DigitalTwin stub class completely)

class PhysicalTransactionManager:
    # ... rest of the file remains exactly the same
