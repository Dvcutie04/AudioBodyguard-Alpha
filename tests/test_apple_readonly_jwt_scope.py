"""Offline regression checks for one-token-per-request Apple GET scope.

No real signing key, network call, uploaded package or personal account needed.
"""
import base64
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit


OBSERVER = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "tools/release_20261111_apple_readiness.py"),
    run_name="aqss_scoped_readonly_unit_fixture",
)


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size):
        assert size <= 2_000_001
        return b'{"data":[]}'


class _CapturingOpener:
    def __init__(self):
        self.requests = []

    def open(self, request, timeout):
        assert timeout == 30
        self.requests.append(request)
        return _Response()


def _decode_claims(request):
    header = request.get_header("Authorization")
    assert header and header.startswith("Bearer ")
    payload = header.split(" ", 1)[1].split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


class AppleScopedGetTests(unittest.TestCase):
    def test_query_bearing_scope_exactly_matches_request_target(self):
        samples = [
            ("/v1/apps", {
                "filter[bundleId]": "com.example.bodyguard",
                "fields[apps]": "bundleId",
                "limit": "2",
            }),
            ("/v1/builds", {
                "filter[app]": "12345",
                "filter[version]": "17.3",
                "filter[preReleaseVersion.version]": "1.0.0",
                "include": "preReleaseVersion,buildBetaDetail",
                "limit": "2",
            }),
            ("/v1/betaGroups", {
                "filter[app]": "12345",
                "filter[builds]": "build123",
                "filter[isInternalGroup]": "true",
                "fields[betaGroups]": "isInternalGroup,name",
                "limit": "200",
            }),
            ("/v1/apps", {}),
        ]
        fake_signature = b"\x30\x06\x02\x01\x01\x02\x01\x01"
        with patch.object(OBSERVER["subprocess"], "run",
                          return_value=SimpleNamespace(stdout=fake_signature)) as signer:
            for path, params in samples:
                with self.subTest(path=path, params=params):
                    api = OBSERVER["AppleReadOnly"](
                        Path("/nonexistent-synthetic-key"),
                        "ABCDEFGHIJ", "12345678-1234-1234-1234-123456789012",
                    )
                    capture = _CapturingOpener()
                    api.opener = capture
                    self.assertEqual(api(path, params), {"data": []})
                    self.assertEqual(len(capture.requests), 1)
                    request = capture.requests[0]
                    self.assertEqual(request.get_method(), "GET")
                    url = urlsplit(request.full_url)
                    self.assertEqual(url.scheme, "https")
                    self.assertEqual(url.hostname, "api.appstoreconnect.apple.com")
                    self.assertEqual(url.path, path)
                    expected_target = path + ("?" + url.query if url.query else "")
                    claims = _decode_claims(request)
                    self.assertEqual(claims["scope"], ["GET " + expected_target])
                    self.assertEqual(claims["aud"], "appstoreconnect-v1")
                    self.assertEqual(claims["exp"] - claims["iat"], 300)
                    self.assertEqual(signer.call_count >= 1, True)
                    if params:
                        self.assertNotEqual(claims["scope"], ["GET " + path],
                                            "Old path-only scope incorrectly ignores filtered query")

    def test_disallows_other_endpoints_and_nonstring_parameters(self):
        api = OBSERVER["AppleReadOnly"](
            Path("/nonexistent-synthetic-key"), "ABCDEFGHIJ",
            "12345678-1234-1234-1234-123456789012",
        )
        for endpoint, params in [
            ("/v1/betaTesters", {}),
            ("/v1/apps/123", {}),
            ("/v1/apps", {"filter[bundleId]": 123}),
            ("/v1/apps", [("filter[bundleId]", "com.example.bodyguard")]),
        ]:
            with self.subTest(endpoint=endpoint, params=params):
                with self.assertRaises(OBSERVER["ObservationError"]):
                    api(endpoint, params)


if __name__ == "__main__":
    unittest.main()
