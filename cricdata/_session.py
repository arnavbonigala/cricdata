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


class AsyncSession:
    """Async variant of Session using curl_cffi's built-in async support."""

    def __init__(self, impersonate: str = "chrome", timeout: int = 30):
        self._session = curl_requests.AsyncSession(impersonate=impersonate)
        self.timeout = timeout

    async def get(self, url: str, **kwargs) -> curl_requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return await self._session.get(url, **kwargs)

    async def aclose(self) -> None:
        self._session.close()

    async def __aenter__(self) -> AsyncSession:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
