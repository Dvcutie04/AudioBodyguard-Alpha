from pathlib import Path


def test_legacy_tv_controller_has_no_direct_physical_io():
    target = Path("src/bridges/tv_controller.py")
    assert target.is_file(), "LEGACY_CONTROLLER_MISSING"
    text = target.read_text(encoding="utf-8", errors="strict")
    forbidden = (
        "urllib.request.urlopen",
        "ssl.CERT_NONE",
        "subprocess.run(",
        "KEYCODE_WAKEUP",
        "KEYCODE_SLEEP",
        "/keypress/PowerOn",
        "/keypress/PowerOff",
    )
    hits = [token for token in forbidden if token in text]
    assert not hits, f"UNAUTHORIZED_PHYSICAL_IO_BOUNDARY: {hits}"


import pytest

from src.bridges.tv_controller import (
    LegacyPhysicalIOQuarantined,
    TVControllerFactory,
)


@pytest.mark.parametrize(
    "brand",
    ("vizio", "samsung", "lg", "sony", "tcl", "roku", "fire", "amazon"),
)
@pytest.mark.parametrize("operation", ("power_on", "power_off"))
def test_every_legacy_tv_power_operation_fails_closed(brand, operation):
    controller = TVControllerFactory.get_controller(brand, "192.0.2.1")
    with pytest.raises(
        LegacyPhysicalIOQuarantined,
        match="requires an authorized Device Fabric intent",
    ):
        getattr(controller, operation)()


def test_no_active_module_combines_physical_actions_with_direct_io():
    action_markers = (
        b"power_on",
        b"power_off",
        b"set_volume",
        b"set_muted",
        b"set_input_source",
        b"/keypress/",
        b"KEYCODE_",
        b"device/power_mode",
        b"send_command",
    )
    direct_io_markers = (
        b"urllib.request.urlopen",
        b"requests.",
        b"httpx.",
        b"aiohttp.",
        b"socket.socket",
        b"subprocess.run(",
        b"bleak",
        b"bluetooth",
        b"mqtt",
    )
    authorized_physical_io_files = frozenset()
    archival_name_markers = (
        ".corrupt.",
        ".recovered.",
        ".blob-recovery.",
        ".gitblob-corrupt.",
        ".empty.backup.",
        ".stub.",
    )
    offenders = {}
    for source in Path("src").rglob("*.py"):
        if "quarantine" in source.parts:
            continue
        if any(marker in source.name for marker in archival_name_markers):
            continue
        if source.as_posix() in authorized_physical_io_files:
            continue
        data = source.read_bytes()
        actions = [marker.decode("ascii") for marker in action_markers if marker in data]
        sinks = [marker.decode("ascii") for marker in direct_io_markers if marker in data]
        if actions and sinks:
            offenders[source.as_posix()] = {"actions": actions, "direct_io": sinks}
    assert not offenders, f"UNAUTHORIZED_PHYSICAL_IO_INVENTORY: {offenders}"
