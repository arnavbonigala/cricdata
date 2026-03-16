from __future__ import annotations

from curl_cffi import requests as curl_requests


class Session:
    """Shared curl_cffi session with browser TLS fingerprint impersonation."""

    def __init__(self, impersonate: str = "chrome", timeout: int = 30):
        self._session = curl_requests.Session(impersonate=impersonate)
        self.timeout = timeout

    def get(self, url: str, **kwargs) -> curl_requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self._session.get(url, **kwargs)
