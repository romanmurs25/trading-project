import hmac
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class BybitAuth:
    api_key: str
    api_secret: str
    recv_window: int = 5000

    def sign(self, timestamp_ms: int, payload: str) -> str:
        message = f"{timestamp_ms}{self.api_key}{self.recv_window}{payload}"
        return hmac.new(self.api_secret.encode(), message.encode(), sha256).hexdigest()
