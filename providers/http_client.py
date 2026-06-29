from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ProviderError


class HttpClient:
    """Small injectable HTTP client so provider adapters remain easy to test."""

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: int = 90,
    ) -> dict[str, Any]:
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        request = Request(url, data=body, headers=request_headers, method=method.upper())
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Provider HTTP {error.code}: {detail or error.reason}") from error
        except URLError as error:
            raise ProviderError(f"Provider connection failed: {error.reason}") from error

        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ProviderError("Provider returned invalid JSON.") from error
        if not isinstance(parsed, dict):
            raise ProviderError("Provider returned an unexpected JSON response.")
        return parsed

    def request_bytes(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: int = 180,
    ) -> bytes:
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        request = Request(url, data=body, headers=request_headers, method=method.upper())
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Provider HTTP {error.code}: {detail or error.reason}") from error
        except URLError as error:
            raise ProviderError(f"Provider connection failed: {error.reason}") from error
