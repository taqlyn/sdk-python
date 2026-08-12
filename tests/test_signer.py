import hashlib
import json

import pytest

from taqlyn import (
    canonical_request_message,
    load_private_key,
    normalize_pem,
    sign_request,
)

GOLDEN_PEM = """-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8g
-----END PRIVATE KEY-----
"""
BODY_OBJECT = {
    "destinationWeb": "https://example.com/offer",
    "mode": "web_only",
}
BODY = json.dumps(BODY_OBJECT, separators=(",", ":"))
TIMESTAMP = 1_700_000_000
CLIENT_ID = "app_test_abc"
PATH = "/v1/short-links"
BODY_HASH = "45b1df36051aec5657b955f266811307e521e19fad0baa2dd052f2ed4a8bd6c7"
SIGNATURE = (
    "zTe0VimeWAe6dzpPxAIn+DDR46E58G63ypiSTkXd1jT1o3oxYJ4jzAof05lf3s/"
    "8sbZ7l46VjDh8ohtB+NISAA=="
)


def test_golden_signing_vector_matches_node() -> None:
    assert hashlib.sha256(BODY.encode()).hexdigest() == BODY_HASH
    message = canonical_request_message(
        "post", PATH, TIMESTAMP, CLIENT_ID, BODY
    )
    assert message == (
        f"taqlyn-v1\nPOST\n{PATH}\n{TIMESTAMP}\n{CLIENT_ID}\n{BODY_HASH}"
    )
    assert not message.endswith("\n")
    assert (
        sign_request(
            load_private_key(GOLDEN_PEM),
            "POST",
            PATH,
            TIMESTAMP,
            CLIENT_ID,
            BODY,
        )
        == SIGNATURE
    )


def test_normalizes_literal_newlines_and_rejects_secret_handle() -> None:
    literal_newlines = GOLDEN_PEM.strip().replace("\n", "\\n")
    assert "\n" in normalize_pem(literal_newlines)
    load_private_key(literal_newlines)

    with pytest.raises(ValueError, match="UX handle"):
        load_private_key("sk_test_not_a_private_key")
