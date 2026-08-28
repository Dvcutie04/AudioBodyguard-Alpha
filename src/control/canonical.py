import json
import hashlib
from typing import Any, Dict


def canonicalize(data: Dict[str, Any]) -> bytes:
    """
    Deterministically serializes a dictionary into UTF-8 canonical JSON bytes.
    Enforces lexicographical key sorting, strict float formatting, and compact separators.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")


def compute_digest(data: Dict[str, Any]) -> str:
    """Computes a SHA-256 hex digest of canonicalized object data."""
    return hashlib.sha256(canonicalize(data)).hexdigest()
