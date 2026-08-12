"""Taqlyn SDK errors."""

from __future__ import annotations

from typing import Any


class TaqlynApiError(Exception):
    """A non-success response from the Taqlyn API."""

    def __init__(self, status: int, body: Any) -> None:
        code = body.get("error", "api.error") if isinstance(body, dict) else "api.error"
        message = body.get("message", f"HTTP {status}") if isinstance(body, dict) else f"HTTP {status}"
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.body = body
