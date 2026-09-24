import dataclasses

import pytest

from src.core.system_config import SystemConfig


def test_system_config_recovered_historical_contract():
    config = SystemConfig()
    assert config.h_enter == 0.75
    assert config.h_exit == 0.35
    assert config.required_dwell_ticks == 3
    assert config.max_tdl_us == 500000
    assert config.expected_version == "v1.0.0"
    assert config.debug_mode is False
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.h_enter = 0.8
