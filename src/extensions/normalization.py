from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import unicodedata

from .proposal import ExtensionProposal, _freeze


class NormalizationAuthorityError(ValueError):
    pass


_FORBIDDEN_AUTHORITY_KEYS = frozenset({
    "signature",
    "lease_id",
    "capability_lease_digest",
    "authorization_digest",
    "issuer_id",
    "policy_digest",
    "transaction_id",
    "expected_pre_state_digest",
})


def _reject_authority_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        seen_keys = set()
        for key, item in value.items():
            if not isinstance(key, str):
                raise NormalizationAuthorityError(
                    "extension parameters contain non-string key: " + repr(key)
                )
            if not key.isprintable():
                raise NormalizationAuthorityError(
                    "extension parameters contain control characters in key: " + repr(key)
                )
            if not key.strip():
                raise NormalizationAuthorityError(
                    "extension parameters contain blank key: " + repr(key)
                )
            if key != key.strip():
                raise NormalizationAuthorityError(
                    "extension parameters contain surrounding whitespace in key: " + repr(key)
                )
            nfkc_key = unicodedata.normalize("NFKC", key)
            if key != nfkc_key:
                raise NormalizationAuthorityError(
                    "extension parameters contain non-NFKC key: " + repr(key)
                )
            collision_key = nfkc_key.casefold()
            if collision_key in seen_keys:
                raise NormalizationAuthorityError(
                    "extension parameters contain casefold key collision: " + repr(key)
                )
            seen_keys.add(collision_key)
            normalized_key = nfkc_key.strip().lower()
            if normalized_key in _FORBIDDEN_AUTHORITY_KEYS:
                raise NormalizationAuthorityError(
                    "extension parameters contain reserved authority field: " + str(key)
                )
            _reject_authority_keys(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _reject_authority_keys(item)

@dataclass(frozen=True)
class NormalizedCandidate:
    extension_id: str
    target_id: str
    operation: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _freeze(self.parameters))


def normalize_proposal(proposal: ExtensionProposal) -> NormalizedCandidate:
    for field_name, value in (("extension_id", proposal.extension_id), ("target_id", proposal.target_id), ("operation", proposal.operation)):
        if not isinstance(value, str):
            raise NormalizationAuthorityError(
                "extension semantic field must be a string: " + field_name
            )
        if not value.strip():
            raise NormalizationAuthorityError(
                "extension semantic field must not be blank: " + field_name
            )
        if value != value.strip():
            raise NormalizationAuthorityError(
                "extension semantic field must not contain surrounding whitespace: " + field_name
            )
        if not value.isprintable():
            raise NormalizationAuthorityError(
                "extension semantic field must not contain control characters: " + field_name
            )
        if value != unicodedata.normalize("NFKC", value):
            raise NormalizationAuthorityError(
                "extension semantic field must be NFKC-stable: " + field_name
            )
        if field_name == "extension_id" and value != value.lower():
            raise NormalizationAuthorityError(
                "extension_id must use canonical lowercase"
            )
        if field_name == "extension_id" and any(not segment for segment in value.split(".")):
            raise NormalizationAuthorityError(
                "extension_id must contain nonempty dotted segments"
            )
        if field_name == "extension_id" and any(
            any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for character in segment)
            for segment in value.split(".")
        ):
            raise NormalizationAuthorityError(
                "extension_id segments contain invalid characters"
            )
        if field_name == "operation" and value != value.upper():
            raise NormalizationAuthorityError(
                "operation must use canonical uppercase"
            )
    if not isinstance(proposal.parameters, Mapping):
        raise NormalizationAuthorityError(
            "extension parameters must be a mapping"
        )
    _reject_authority_keys(proposal.parameters)
    return NormalizedCandidate(
        extension_id=proposal.extension_id,
        target_id=proposal.target_id,
        operation=proposal.operation,
        parameters=proposal.parameters,
    )
