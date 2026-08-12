import json
from typing import Any

from taqlyn import TaqlynClient

from test_signer import CLIENT_ID, GOLDEN_PEM, SIGNATURE, TIMESTAMP


class MockResponse:
    status = 201

    def read(self) -> bytes:
        return json.dumps(
            {
                "id": "sl_test",
                "code": "Ab12Cd",
                "shortUrl": "https://go.example/Ab12Cd",
                "host": "go.example",
                "mode": "web_only",
                "destinationWeb": "https://example.com/offer",
                "env": "sandbox",
                "orgId": "org_test",
                "appId": "app_test",
            }
        ).encode()


def test_create_short_link_sends_signed_openapi_request() -> None:
    captured: dict[str, Any] = {}

    def mock_urlopen(request: Any) -> MockResponse:
        captured["request"] = request
        return MockResponse()

    client = TaqlynClient(
        base_url="https://api.example/",
        client_id=CLIENT_ID,
        private_key=GOLDEN_PEM,
        now=lambda: TIMESTAMP,
        urlopen=mock_urlopen,
    )
    link = client.create_short_link(
        destination_web="https://example.com/offer",
        mode="web_only",
    )

    request = captured["request"]
    headers = {name.lower(): value for name, value in request.header_items()}
    assert request.full_url == "https://api.example/v1/short-links"
    assert request.method == "POST"
    assert request.data == (
        b'{"destinationWeb":"https://example.com/offer","mode":"web_only"}'
    )
    assert headers["x-taqlyn-client-id"] == CLIENT_ID
    assert headers["x-taqlyn-timestamp"] == str(TIMESTAMP)
    assert headers["x-taqlyn-signature"] == SIGNATURE
    assert link["shortUrl"] == "https://go.example/Ab12Cd"
