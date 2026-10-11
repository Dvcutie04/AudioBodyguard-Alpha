import pytest
from src.quantum import ibm_client

def test_missing_runtime_key_rejects_before_network(monkeypatch):
    monkeypatch.delenv("IBM_CLOUD_API_KEY", raising=False)
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(1)
        raise AssertionError("network must not be attempted")
    monkeypatch.setattr(ibm_client.urllib.request, "urlopen", forbidden)
    with pytest.raises(ValueError, match="IBM_CLOUD_API_KEY"):
        ibm_client.get_access_token()
    assert calls == []
