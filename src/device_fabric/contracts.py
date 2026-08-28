"""
AQSS-36-OMEGA
Physical Truth Runtime — Core Contracts
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from hashlib import sha256
from typing import Mapping, Optional

class ContractViolation(ValueError):
    """Raised when a Physical Truth contract violates an invariant."""

# ... (Your DeviceState, AuthorizedActionIntent, and the rest of the classes continue here) ...
