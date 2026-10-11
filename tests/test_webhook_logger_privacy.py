"""A failed legacy webhook must not return its credential-bearing URL."""
import json
import urllib.error

import pytest

from src.bridges.webhook_logger import IFTTTWebhookLogger


@pytest.mark.parametrize("failure", ["http", "connection"])
def test_webhook_failure_does_not_disclose_its_key(monkeypatch, failure):
    key = "synthetic-private-webhook-key"
    logger = IFTTTWebhookLogger("synthetic_event", key)
    error = (
        urllib.error.HTTPError(logger.url, 403, f"Rejected {logger.url}", {}, None)
        if failure == "http"
        else urllib.error.URLError(f"Could not reach {logger.url}")
    )

    def fail_without_network(*args, **kwargs):
        raise error

    monkeypatch.setattr("src.bridges.webhook_logger.urllib.request.urlopen", fail_without_network)
    result = logger.log_event("synthetic_input")
    assert result["status"] == "error"
    assert key not in json.dumps(result)
    assert logger.url not in json.dumps(result)
