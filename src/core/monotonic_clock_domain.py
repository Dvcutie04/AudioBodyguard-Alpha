import secrets


_PROCESS_MONOTONIC_CLOCK_DOMAIN_ID="process:"+secrets.token_hex(16)


def current_monotonic_clock_domain_id()->str:
    return _PROCESS_MONOTONIC_CLOCK_DOMAIN_ID


def validate_monotonic_clock_domain_id(value)->str:
    if type(value) is not str or not value.strip():
        raise ValueError("monotonic clock domain id must be a non-empty string")
    return value
