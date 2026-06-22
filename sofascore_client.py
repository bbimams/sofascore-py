"""Thin client for SofaScore's private football API.

The two things SofaScore's edge checks are:

1. A TLS / JA3 fingerprint that looks like a real browser. The plain ``requests``
   library fails this; ``curl_cffi`` solves it via ``impersonate=...`` which
   replays a real browser's ClientHello.
2. An ``X-Requested-With`` token derived from the current 30-minute clock window:
       token = sha256( floor(unix_seconds / 1800) )[:6]
   plus the browser-style ``Sec-Fetch-*`` headers used by XHR/fetch calls.

DNS resolution can optionally use DNS-over-HTTPS (DoH) via ``doh_url`` so the
client does not depend on the system/ISP resolver.
"""

from __future__ import annotations

import hashlib
import time

from curl_cffi import CurlOpt, requests

DEFAULT_BASE_URL = "https://api.sofascore.com/api/v1"
DEFAULT_ORIGIN = "https://www.sofascore.com"
DEFAULT_IMPERSONATE = "chrome"


class SofaScoreError(Exception):
    """Raised when the upstream request cannot be completed."""


class SofaScoreClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        origin: str = DEFAULT_ORIGIN,
        impersonate: str = DEFAULT_IMPERSONATE,
        timeout: float = 20.0,
        doh_url: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.origin = origin.rstrip("/")
        self.impersonate = impersonate
        self.timeout = timeout
        self.doh_url = doh_url

    # ------------------------------------------------------------------ #
    # Token + headers
    # ------------------------------------------------------------------ #
    def token(self, now: float | None = None) -> str:
        """Return the rotating X-Requested-With token for the current window."""
        now = time.time() if now is None else now
        window = int(now // 1800)
        return hashlib.sha256(str(window).encode()).hexdigest()[:6]

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.origin,
            "Referer": self.origin + "/",
            "X-Requested-With": self.token(),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Sec-GPC": "1",
        }

    # ------------------------------------------------------------------ #
    # Session / DoH
    # ------------------------------------------------------------------ #
    def _new_session(self):
        kwargs: dict = {"impersonate": self.impersonate}
        if self.doh_url:
            kwargs["curl_options"] = {CurlOpt.DOH_URL: self.doh_url}
        return requests.Session(**kwargs)

    # ------------------------------------------------------------------ #
    # Requests
    # ------------------------------------------------------------------ #
    def get(self, path: str) -> tuple[bytes, int]:
        """GET an upstream path (e.g. ``/event/123``) and return (body, status)."""
        url = self.base_url + path
        sess = self._new_session()
        try:
            resp = sess.get(url, headers=self._headers(), timeout=self.timeout)
        except Exception as exc:
            raise SofaScoreError(str(exc)) from exc
        finally:
            try:
                sess.close()
            except Exception:
                pass
        return resp.content, resp.status_code
