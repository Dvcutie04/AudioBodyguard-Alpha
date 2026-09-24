from src.extensions.contracts import ExtensionAdapter


def test_extension_adapter_protocol_is_importable():
    assert ExtensionAdapter is not None
