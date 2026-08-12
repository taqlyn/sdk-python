"""Ed25519 signing for privileged Taqlyn REST requests."""

from __future__ import annotations

import base64
import hashlib
import re
from typing import Mapping, Union

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

Body = Union[bytes, bytearray, memoryview, str]


def canonical_request_message(
    method: str,
    path: str,
    unix_timestamp: int,
    client_id: str,
    body: Body,
) -> str:
    """Build the newline-separated canonical message (without a trailing newline)."""
    body_bytes = body.encode("utf-8") if isinstance(body, str) else bytes(body)
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    return "\n".join(
        ("taqlyn-v1", method.upper(), path, str(unix_timestamp), client_id, body_hash)
    )


def normalize_pem(pem: str) -> str:
    """Normalize PEM values containing literal ``\\n`` from environment variables."""
    normalized = pem.strip()
    if "\\n" in normalized and "\n" not in normalized:
        normalized = normalized.replace("\\n", "\n")
    return normalized


def _decode_raw_key(raw: str) -> bytes:
    value = raw.strip()
    if re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return bytes.fromhex(value)

    encoded = value.replace("-", "+").replace("_", "/")
    encoded += "=" * (-len(encoded) % 4)
    try:
        seed = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(
            "private_key: expected PKCS#8 PEM or raw 32-byte Ed25519 seed "
            "(bytes, hex, or base64)"
        ) from exc
    if len(seed) != 32:
        raise ValueError(
            "private_key: expected PKCS#8 PEM or raw 32-byte Ed25519 seed "
            "(bytes, hex, or base64)"
        )
    return seed


def load_private_key(private_key: Union[str, bytes, bytearray, memoryview]) -> Ed25519PrivateKey:
    """Load a PKCS#8 PEM or raw 32-byte Ed25519 seed."""
    if isinstance(private_key, str):
        value = normalize_pem(private_key)
        if value.startswith("sk_"):
            raise ValueError(
                "private_key: sk_* is a UX handle only; pass the PKCS#8 PEM "
                "returned at key issue"
            )
        if "-----BEGIN" in value and "PRIVATE KEY" in value:
            loaded = serialization.load_pem_private_key(value.encode("utf-8"), password=None)
            if not isinstance(loaded, Ed25519PrivateKey):
                raise ValueError("private_key: PEM key must be Ed25519")
            return loaded
        return Ed25519PrivateKey.from_private_bytes(_decode_raw_key(value))

    seed = bytes(private_key)
    if len(seed) != 32:
        raise ValueError("private_key: raw Ed25519 seed must be 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(seed)


def sign_request(
    private_key: Ed25519PrivateKey,
    method: str,
    path: str,
    unix_timestamp: int,
    client_id: str,
    body: Body,
) -> str:
    """Sign a canonical request and return standard base64."""
    message = canonical_request_message(
        method, path, unix_timestamp, client_id, body
    ).encode("utf-8")
    return base64.b64encode(private_key.sign(message)).decode("ascii")


def signed_headers(
    private_key: Ed25519PrivateKey,
    client_id: str,
    method: str,
    path: str,
    body: Body,
    unix_timestamp: int,
) -> Mapping[str, str]:
    """Build the three Taqlyn signing headers."""
    return {
        "X-Taqlyn-Client-Id": client_id,
        "X-Taqlyn-Timestamp": str(unix_timestamp),
        "X-Taqlyn-Signature": sign_request(
            private_key, method, path, unix_timestamp, client_id, body
        ),
    }
