# taqlyn-sdk

Taqlyn **server** SDK for Python. Signs privileged REST with an Ed25519
**private key** (never send `sk_*` alone — use the PKCS#8 PEM issued once when
credentials are created).

OpenAPI contract: [`packages/openapi/openapi.yaml`](../openapi/openapi.yaml)
(`TaqlynEd25519`, `/v1/short-links`).

This is a server-only SDK. It never embeds Match, resolve, deferred-deep-link,
or other mobile flows, and private keys must never be shipped in client apps.

## Install

```bash
pip install taqlyn-sdk
```

From this monorepo package:

```bash
cd packages/sdk-python
python -m pip install -e .
```

## Quickstart — create a short link

```bash
export TAQLYN_BASE_URL=https://api.rutvik.qzz.io
export TAQLYN_CLIENT_ID=app_test_...          # from Keys.issue (sandbox)
export TAQLYN_PRIVATE_KEY='-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----'
```

```python
import os

from taqlyn import TaqlynClient

client = TaqlynClient(
    base_url=os.environ["TAQLYN_BASE_URL"],
    client_id=os.environ["TAQLYN_CLIENT_ID"],
    private_key=os.environ["TAQLYN_PRIVATE_KEY"],  # PKCS#8 PEM (not sk_*)
)

link = client.create_short_link(
    destination_web="https://example.com/offer",
    mode="web_only",
)

print(link["shortUrl"])  # e.g. https://go.localhost/Ab12Cd
```

`TAQLYN_BASE_URL` is the API origin, with or without a trailing slash.
`TAQLYN_CLIENT_ID` starts with `app_test_` or `app_live_`.
`TAQLYN_PRIVATE_KEY` is a PKCS#8 Ed25519 PEM; literal `\n` sequences in an
environment variable are accepted. A raw 32-byte seed may also be passed as
bytes, hex, or standard/URL-safe base64.

Do **not** commit private keys. The `sk_test_*` / `sk_live_*` string is only a
UX handle — the API verifies signatures against the stored public key.

## Manage short links

```python
link = client.get_short_link("sl_...")
link = client.patch_short_link("sl_...", {"destinationWeb": "https://example.com/new"})
client.delete_short_link("sl_...")
```

Patch values use the OpenAPI JSON field names.

## Signing

Privileged routes require `X-Taqlyn-Client-Id`, `X-Taqlyn-Timestamp` (unix
seconds), and `X-Taqlyn-Signature` (standard base64 of a 64-byte Ed25519
signature).

The canonical message has no trailing newline:

```text
taqlyn-v1
{METHOD}
{PATH}
{unixTimestamp}
{clientId}
{hex(sha256(body))}
```

The path excludes the query string. An empty body hashes as SHA-256 of empty
bytes.

## Tests

```bash
python -m pip install -e ".[test]"
python -m pytest
```

## License

MIT — see [LICENSE](./LICENSE).
