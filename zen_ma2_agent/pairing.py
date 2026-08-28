from __future__ import annotations

import secrets
from dataclasses import dataclass, field


@dataclass
class PairingManager:
    code: str = field(default_factory=lambda: f"{secrets.randbelow(1_000_000):06d}")
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(12))
    _tokens: set[str] = field(default_factory=set, init=False, repr=False)

    def pair(self, code: str, nonce: str | None = None) -> str | None:
        if code != self.code or (nonce is not None and nonce != self.nonce):
            return None
        token = secrets.token_urlsafe(32)
        self._tokens.add(token)
        return token

    def valid(self, token: str | None) -> bool:
        return bool(token and token in self._tokens)

    @property
    def connected_count(self) -> int:
        return len(self._tokens)
