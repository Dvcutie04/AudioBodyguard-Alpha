"""Exercise peer certificate possession on a synthetic IPv4 loopback service."""

from enum import Enum
from hmac import compare_digest
import socket
import ssl

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding


_LOOPBACK = "127.0.0.1"
_CERTIFICATE_LIMIT = 16 * 1024
_IO_TIMEOUT = 2


class FixturePeerOutcome(str, Enum):
    VERIFIED = "SYNTHETIC_LOOPBACK_TLS_VERIFIED"
    REFUSED = "SYNTHETIC_LOOPBACK_TLS_REFUSED"


def verify_fixture_peer(port: int, *, independent_reference_der: bytes) -> FixturePeerOutcome:
    """Complete TLS with a pre-provisioned fixture leaf, then close the socket."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("invalid_fixture_port")
    if not isinstance(independent_reference_der, bytes) or not 0 < len(independent_reference_der) <= _CERTIFICATE_LIMIT:
        raise ValueError("invalid_fixture_reference")
    try:
        reference = x509.load_der_x509_certificate(independent_reference_der)
    except ValueError:
        raise ValueError("invalid_fixture_reference") from None
    if reference.public_bytes(Encoding.DER) != independent_reference_der:
        raise ValueError("invalid_fixture_reference")

    # Use a fresh trust store with the independently provisioned fixture leaf.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(independent_reference_der))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(_IO_TIMEOUT)
            connection.connect((_LOOPBACK, port))
            with context.wrap_socket(connection, server_hostname=_LOOPBACK) as peer:
                presented = peer.getpeercert(binary_form=True)
                matches = presented is not None and compare_digest(presented, independent_reference_der)
                peer.unwrap().close()
    except OSError:
        return FixturePeerOutcome.REFUSED
    return FixturePeerOutcome.VERIFIED if matches else FixturePeerOutcome.REFUSED
