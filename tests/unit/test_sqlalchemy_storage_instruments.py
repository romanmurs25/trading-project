from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from storage.sqlalchemy_models import Base, ContractSpecRow, InstrumentRow
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import ContractSpec, Instrument


def make_storage() -> SQLAlchemyStorage:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SQLAlchemyStorage(sessionmaker(bind=engine))


def make_instrument(
    *,
    instrument_id: str = "moex-si",
    canonical_symbol: str = "MOEX:SiH6",
    is_active: bool = True,
) -> Instrument:
    return Instrument(
        id=instrument_id,
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol=canonical_symbol,
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=date(2026, 3, 19),
        is_active=is_active,
        metadata={"source": "test"},
    )


def make_contract_spec() -> ContractSpec:
    return ContractSpec(
        instrument_id="moex-si",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=date(2026, 3, 19),
        first_trade_date=date(2025, 12, 20),
        last_trade_date=date(2026, 3, 18),
        underlying_symbol="Si",
        metadata={"source": "test"},
    )


def test_sqlalchemy_storage_saves_lists_and_gets_instruments() -> None:
    storage = make_storage()
    instrument = make_instrument()

    storage.save_instrument(instrument)

    assert storage.get_instrument("moex-si") == instrument
    assert storage.get_instrument_by_canonical_symbol("MOEX:SiH6") == instrument
    assert storage.list_instruments(venue=Venue.MOEX, asset_class=AssetClass.FUTURES, is_active=True) == [
        instrument
    ]


def test_sqlalchemy_storage_upserts_instrument_by_id_and_canonical_symbol() -> None:
    storage = make_storage()
    storage.save_instrument(make_instrument(instrument_id="moex-si", canonical_symbol="MOEX:SiH6"))
    updated = make_instrument(instrument_id="moex-si", canonical_symbol="MOEX:SiH6", is_active=False)
    storage.save_instrument(updated)
    same_symbol_new_id = make_instrument(instrument_id="moex-si-new", canonical_symbol="MOEX:SiH6")
    storage.save_instrument(same_symbol_new_id)

    with storage.session_factory() as session:
        rows_count = session.scalar(select(func.count()).select_from(InstrumentRow))

    assert rows_count == 1
    assert storage.get_instrument_by_canonical_symbol("MOEX:SiH6") == same_symbol_new_id


def test_sqlalchemy_storage_saves_and_gets_contract_spec() -> None:
    storage = make_storage()
    spec = make_contract_spec()

    storage.save_contract_spec(spec)

    with storage.session_factory() as session:
        rows_count = session.scalar(select(func.count()).select_from(ContractSpecRow))

    assert rows_count == 1
    assert storage.get_contract_spec("moex-si") == spec
