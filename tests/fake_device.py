"""FakeDevice — transport test double for the Pixoo HTTP /post endpoint.

Injected into PixooClient(ip, poster=fake) in place of the real urllib
poster, so protocol tests assert on the request stream (URL, body, order)
without touching the network. Returns a canned success response.
"""
from __future__ import annotations

import json


class FakeDevice:
    """Callable poster stand-in that records every request it receives.

    Each call is recorded as {url, body, timeout, order, payload} where
    `payload` is the decoded JSON body. Returns {"error_code": 0} unless a
    custom response dict is supplied.
    """

    def __init__(self, response: dict | None = None) -> None:
        self.response = {"error_code": 0} if response is None else response
        self.requests: list[dict] = []
        self._seq = 0

    def __call__(self, url: str, body: bytes, timeout: float) -> dict:
        self.requests.append({
            "url": url,
            "body": body,
            "timeout": timeout,
            "order": self._seq,
            "payload": json.loads(body.decode()),
        })
        self._seq += 1
        return self.response

    @property
    def post_count(self) -> int:
        return len(self.requests)

    @property
    def commands(self) -> list[str]:
        return [r["payload"]["Command"] for r in self.requests]

    def payload_at(self, order: int) -> dict:
        return self.requests[order]["payload"]
