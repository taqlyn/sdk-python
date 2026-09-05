"""HTTP client for privileged Taqlyn ShortLink operations."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Mapping, Optional, Union

from .errors import TaqlynApiError
from .signer import load_private_key, signed_headers

DEFAULT_API_BASE_URL = "https://api.taqlyn.com"
SHORT_LINKS_PATH = "/v1/short-links"
PrivateKey = Union[str, bytes, bytearray, memoryview]


class TaqlynClient:
    """Taqlyn server SDK client using Ed25519-signed privileged REST calls."""

    def __init__(
        self,
        *,
        client_id: str,
        private_key: PrivateKey,
        base_url: Optional[str] = None,
        now: Optional[Callable[[], int]] = None,
        urlopen: Optional[Callable[..., Any]] = None,
    ) -> None:
        raw_url = (
            base_url
            or os.environ.get("TAQLYN_BASE_URL")
            or os.environ.get("TAQLYN_API_URL")
            or DEFAULT_API_BASE_URL
        )
        if not raw_url or not raw_url.strip():
            raise ValueError("base_url is required")
        if not client_id or not client_id.strip():
            raise ValueError("client_id is required")
        client_id = client_id.strip()
        if not client_id.startswith(("app_test_", "app_live_")):
            raise ValueError("client_id must start with app_test_ or app_live_")

        self.base_url = raw_url.rstrip("/")
        self.client_id = client_id
        self._private_key = load_private_key(private_key)
        self._now = now or (lambda: int(time.time()))
        self._urlopen = urlopen or urllib.request.urlopen

    def create_short_link(
        self,
        *,
        destination_web: str,
        mode: Optional[str] = None,
        destination_path: Optional[str] = None,
        params: Optional[Mapping[str, Any]] = None,
        env: Optional[str] = None,
        og_title: Optional[str] = None,
        og_description: Optional[str] = None,
        og_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a short link with ``POST /v1/short-links``."""
        if not destination_web or not destination_web.strip():
            raise ValueError("destination_web is required")

        body: Dict[str, Any] = {"destinationWeb": destination_web.strip()}
        optional_fields = (
            ("mode", mode),
            ("destinationPath", destination_path),
            ("params", params),
            ("env", env),
            ("ogTitle", og_title),
            ("ogDescription", og_description),
            ("ogImage", og_image),
        )
        body.update((name, value) for name, value in optional_fields if value is not None)
        return self._request("POST", SHORT_LINKS_PATH, body)

    def get_short_link(self, short_link_id: str) -> Dict[str, Any]:
        """Get a short link by ID."""
        return self._request("GET", self._short_link_path(short_link_id))

    def patch_short_link(
        self, short_link_id: str, updates: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Patch a short link using OpenAPI field names in ``updates``."""
        if not updates:
            raise ValueError("updates is required")
        return self._request("PATCH", self._short_link_path(short_link_id), updates)

    def delete_short_link(self, short_link_id: str) -> None:
        """Delete a short link by ID."""
        self._request("DELETE", self._short_link_path(short_link_id))

    @staticmethod
    def _short_link_path(short_link_id: str) -> str:
        if not short_link_id or not short_link_id.strip():
            raise ValueError("short_link_id is required")
        return f"{SHORT_LINKS_PATH}/{urllib.parse.quote(short_link_id.strip(), safe='')}"

    def _request(
        self,
        method: str,
        path: str,
        body_object: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        body = (
            json.dumps(body_object, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            if body_object is not None
            else b""
        )
        headers = {
            "Accept": "application/json",
            **signed_headers(
                self._private_key,
                self.client_id,
                method,
                path,
                body,
                self._now(),
            ),
        }
        if body_object is not None:
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body if body_object is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = self._urlopen(request)
            status = response.status
            raw = response.read()
        except urllib.error.HTTPError as exc:
            self._raise_api_error(exc.code, exc.read())

        parsed = self._parse_body(raw)
        if not 200 <= status < 300:
            raise TaqlynApiError(status, parsed)
        return parsed

    @staticmethod
    def _parse_body(raw: bytes) -> Any:
        if not raw:
            return None
        text = raw.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"message": text}

    def _raise_api_error(self, status: int, raw: bytes) -> None:
        raise TaqlynApiError(status, self._parse_body(raw))
