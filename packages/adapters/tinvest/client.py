from dataclasses import dataclass


@dataclass(frozen=True)
class TInvestClient:
    token: str
    account_id: str
    sandbox: bool = True

    def __post_init__(self) -> None:
        if not self.sandbox:
            raise NotImplementedError("TODO: live T-Invest client is not implemented in MVP")
