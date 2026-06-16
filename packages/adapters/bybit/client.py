from dataclasses import dataclass


@dataclass(frozen=True)
class BybitClient:
    testnet: bool = True
    recv_window: int = 5000

    @property
    def base_url(self) -> str:
        if self.testnet:
            return "https://api-testnet.bybit.com"
        return "https://api.bybit.com"

    async def get_klines(self, symbol: str, interval: str, start_ms: int, end_ms: int) -> dict[str, object]:
        raise NotImplementedError(
            f"TODO: implement read-only Bybit klines for {symbol} {interval} {start_ms}-{end_ms}"
        )
