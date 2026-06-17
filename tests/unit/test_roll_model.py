from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import ContractSpec, Instrument
from trading_core.market.roll import (
    RollRule,
    build_contract_chain,
    generate_roll_events,
    select_front_contract,
)


def instrument(symbol: str, expiry: date) -> Instrument:
    return Instrument(
        id=f"moex:{symbol}",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
    )


def spec(symbol: str, expiry: date, incomplete: bool = False) -> ContractSpec:
    return ContractSpec(
        instrument_id=f"moex:{symbol}",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
        last_trade_date=expiry,
        underlying_symbol="Si",
        metadata={"spec_incomplete": incomplete},
    )


def test_chain_sorted_by_expiry_and_front_contract_before_roll_window() -> None:
    chain = build_contract_chain(
        [instrument("SiM6", date(2026, 6, 18)), instrument("SiH6", date(2026, 3, 19))],
        [spec("SiM6", date(2026, 6, 18)), spec("SiH6", date(2026, 3, 19))],
        "Si",
    )

    decision = select_front_contract(chain, datetime(2026, 3, 1, tzinfo=UTC), RollRule())

    assert [item.canonical_symbol for item in chain.instruments] == ["MOEX:SiH6", "MOEX:SiM6"]
    assert decision.selected_canonical_symbol == "MOEX:SiH6"


def test_next_contract_selected_inside_roll_window() -> None:
    chain = build_contract_chain(
        [instrument("SiH6", date(2026, 3, 19)), instrument("SiM6", date(2026, 6, 18))],
        [spec("SiH6", date(2026, 3, 19)), spec("SiM6", date(2026, 6, 18))],
        "Si",
    )

    decision = select_front_contract(
        chain,
        datetime(2026, 3, 16, tzinfo=UTC),
        RollRule(roll_days_before_expiry=5),
    )

    assert decision.selected_canonical_symbol == "MOEX:SiM6"
    assert "roll window" in decision.reason


def test_expired_contract_skipped_and_incomplete_spec_warns() -> None:
    chain = build_contract_chain(
        [instrument("SiH6", date(2026, 3, 19)), instrument("SiM6", date(2026, 6, 18))],
        [spec("SiH6", date(2026, 3, 19)), spec("SiM6", date(2026, 6, 18), incomplete=True)],
        "Si",
    )

    decision = select_front_contract(chain, datetime(2026, 4, 1, tzinfo=UTC), RollRule())

    assert decision.selected_canonical_symbol == "MOEX:SiM6"
    assert decision.metadata["spec_incomplete"] is True


def test_roll_events_generated() -> None:
    chain = build_contract_chain(
        [instrument("SiH6", date(2026, 3, 19)), instrument("SiM6", date(2026, 6, 18))],
        [spec("SiH6", date(2026, 3, 19)), spec("SiM6", date(2026, 6, 18))],
        "Si",
    )

    events = generate_roll_events(
        chain,
        datetime(2026, 3, 1, tzinfo=UTC),
        datetime(2026, 7, 1, tzinfo=UTC),
        RollRule(roll_days_before_expiry=5),
    )

    assert len(events) == 1
    assert events[0].from_instrument_id == "moex:SiH6"
    assert events[0].to_instrument_id == "moex:SiM6"
    assert events[0].roll_date == date(2026, 3, 14)


def test_chain_with_no_valid_contracts_rejected() -> None:
    with pytest.raises(DataValidationError):
        build_contract_chain([instrument("SiH6", date(2026, 3, 19))], [], "Si")
