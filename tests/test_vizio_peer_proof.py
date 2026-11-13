from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address
import socket
import ssl
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import pytest

from native.lab.vizio_peer_proof import FixturePeerOutcome, verify_fixture_peer


def _leaf(key, ip="127.0.0.1"):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic VIZIO peer")])
    now = datetime.now(timezone.utc)
    return (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(IPv4Address(ip))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))


@contextmanager
def _serve(tmp_path, leaf, key):
    certificate = tmp_path / "synthetic-leaf.pem"
    private_key = tmp_path / "synthetic-key.pem"
    certificate.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    private_key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                              serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, private_key)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener, ThreadPoolExecutor(max_workers=1) as pool:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(3)

        def accept():
            with listener.accept()[0] as connection:
                connection.settimeout(2)
                try:
                    with context.wrap_socket(connection, server_side=True) as peer:
                        payload = peer.recv(1)
                        if not payload:
                            peer.unwrap().close()
                        return True, payload
                except ssl.SSLError:
                    return False, b""

        exchange = pool.submit(accept)
        yield listener.getsockname()[1], exchange


def test_independent_reference_verifies_the_fixture_peer_and_sends_no_payload(tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = _leaf(key)
    reference = leaf.public_bytes(serialization.Encoding.DER)
    with _serve(tmp_path, leaf, key) as (port, exchange):
        assert verify_fixture_peer(port, independent_reference_der=reference) is FixturePeerOutcome.VERIFIED
        assert exchange.result(timeout=3) == (True, b"")


@pytest.mark.parametrize("replace_key", [False, True])
def test_changed_leaf_is_refused_even_with_the_same_name_or_key(tmp_path, replace_key):
    original_key = ec.generate_private_key(ec.SECP256R1())
    reference = _leaf(original_key).public_bytes(serialization.Encoding.DER)
    other_key = ec.generate_private_key(ec.SECP256R1()) if replace_key else original_key
    with _serve(tmp_path, _leaf(other_key), other_key) as (port, exchange):
        assert verify_fixture_peer(port, independent_reference_der=reference) is FixturePeerOutcome.REFUSED
        accepted, payload = exchange.result(timeout=3)
        assert payload == b""
        if replace_key:
            assert not accepted


def test_matching_reference_for_a_different_address_is_refused(tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = _leaf(key, "192.0.2.1")
    reference = leaf.public_bytes(serialization.Encoding.DER)
    with _serve(tmp_path, leaf, key) as (port, exchange):
        assert verify_fixture_peer(port, independent_reference_der=reference) is FixturePeerOutcome.REFUSED
        assert exchange.result(timeout=3) == (False, b"")


@pytest.mark.parametrize("reference", [None, b"", b"invalid", b"x" * 16_385])
def test_invalid_independent_reference_stops_before_contact(reference):
    with patch("native.lab.vizio_peer_proof.socket.socket") as connection:
        with pytest.raises(ValueError, match="^invalid_fixture_reference$"):
            verify_fixture_peer(7345, independent_reference_der=reference)
        connection.assert_not_called()
