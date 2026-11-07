"""Keyless HTTP GET. Failures are returned, not invented around."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

from research.config import USER_AGENT


class FetchResult:
    def __init__(self, url: str, status: int | None, body: str, error: str | None):
        self.url = url
        self.status = status
        self.body = body
        self.error = error

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 300


def make_fetcher(pause: float = 0.25, timeout: float = 20.0):
    last = {"at": 0.0}

    def fetch(url: str, headers: dict | None = None) -> FetchResult:
        if pause:
            wait = pause - (time.monotonic() - last["at"])
            if wait > 0:
                time.sleep(wait)
        last["at"] = time.monotonic()
        header_map = {"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, text/xml, */*"}
        if headers:
            header_map.update(headers)
        request = urllib.request.Request(url, headers=header_map)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(2_000_000)
                charset = response.headers.get_content_charset() or "utf-8"
                return FetchResult(url, response.status, raw.decode(charset, "replace"), None)
        except urllib.error.HTTPError as exc:
            raw = exc.read(200_000) if exc.fp else b""
            return FetchResult(url, exc.code, raw.decode("utf-8", "replace"), f"HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001 - record every transport failure
            return FetchResult(url, None, "", str(exc))

    return fetch
