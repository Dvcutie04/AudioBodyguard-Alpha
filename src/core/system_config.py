from dataclasses import dataclass


@dataclass(frozen=True)
class SystemConfig:
    h_enter: float = 0.75
    h_exit: float = 0.35
    required_dwell_ticks: int = 3
    max_tdl_us: int = 500000
    expected_version: str = "v1.0.0"
    debug_mode: bool = False
