from dataclasses import dataclass


@dataclass(frozen=True)
class MoexIssClient:
    base_url: str

    async def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, object]:
        raise NotImplementedError("TODO: implement read-only MOEX ISS HTTP client with mocked tests")
