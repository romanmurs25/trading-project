from datetime import date
from decimal import Decimal

import pytest
from adapters.moex_iss.instrument_mapper import (
    map_futures_contract_specs,
    map_futures_instruments,
    parse_iss_table,
)
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError


def payload() -> dict[str, object]:
    return {
        "securities": {
            "columns": [
                "SECID",
                "SHORTNAME",
                "SECNAME",
                "LOTSIZE",
                "MINSTEP",
                "STEPPRICE",
                "FACEUNIT",
                "MATDATE",
                "LASTTRADEDATE",
                "ASSETCODE",
                "STATUS",
            ],
            "data": [
                [
                    "SiH6",
                    "Si-3.26",
                    "USD/RUB Futures",
                    "1",
                    "1",
                    "1",
                    "RUB",
                    "2026-03-19",
                    "2026-03-18",
                    "Si",
                    "A",
                ]
            ],
        }
    }


def test_parse_iss_table_returns_column_dicts() -> None:
    rows = parse_iss_table(payload(), "securities")

    assert rows == [
        {
            "SECID": "SiH6",
            "SHORTNAME": "Si-3.26",
            "SECNAME": "USD/RUB Futures",
            "LOTSIZE": "1",
            "MINSTEP": "1",
            "STEPPRICE": "1",
            "FACEUNIT": "RUB",
            "MATDATE": "2026-03-19",
            "LASTTRADEDATE": "2026-03-18",
            "ASSETCODE": "Si",
            "STATUS": "A",
        }
    ]


def test_map_futures_instruments_maps_moex_rows_to_domain_models() -> None:
    instruments = map_futures_instruments(payload())

    assert len(instruments) == 1
    instrument = instruments[0]
    assert instrument.id == "moex:SiH6"
    assert instrument.venue == Venue.MOEX
    assert instrument.asset_class == AssetClass.FUTURES
    assert instrument.native_symbol == "SiH6"
    assert instrument.canonical_symbol == "MOEX:SiH6"
    assert instrument.name == "USD/RUB Futures"
    assert instrument.lot_size == Decimal("1")
    assert instrument.tick_size == Decimal("1")
    assert instrument.tick_value == Decimal("1")
    assert instrument.currency == "RUB"
    assert instrument.expiry_date == date(2026, 3, 19)
    assert instrument.metadata["moex_engine"] == "futures"
    assert instrument.metadata["moex_market"] == "forts"


def test_map_futures_contract_specs_maps_optional_dates_and_underlying() -> None:
    specs = map_futures_contract_specs(payload())

    assert len(specs) == 1
    spec = specs[0]
    assert spec.instrument_id == "moex:SiH6"
    assert spec.lot_size == Decimal("1")
    assert spec.tick_size == Decimal("1")
    assert spec.tick_value == Decimal("1")
    assert spec.currency == "RUB"
    assert spec.expiry_date == date(2026, 3, 19)
    assert spec.last_trade_date == date(2026, 3, 18)
    assert spec.underlying_symbol == "Si"
    assert spec.metadata["spec_incomplete"] is False


def test_map_futures_contract_specs_marks_missing_fields_as_incomplete() -> None:
    incomplete_payload = {
        "securities": {
            "columns": ["SECID", "SHORTNAME"],
            "data": [["BRH6", "BR-3.26"]],
        }
    }

    specs = map_futures_contract_specs(incomplete_payload)

    assert specs[0].instrument_id == "moex:BRH6"
    assert specs[0].lot_size == Decimal("1")
    assert specs[0].tick_size == Decimal("1")
    assert specs[0].tick_value == Decimal("1")
    assert specs[0].currency == "RUB"
    assert specs[0].metadata["spec_incomplete"] is True


def test_parse_iss_table_rejects_malformed_payload() -> None:
    with pytest.raises(DataValidationError):
        parse_iss_table({"securities": {"columns": ["SECID"], "data": [["SiH6", "extra"]]}}, "securities")


def test_map_futures_instruments_rejects_float_values() -> None:
    bad_payload = {
        "securities": {
            "columns": ["SECID", "LOTSIZE"],
            "data": [["SiH6", 1.0]],
        }
    }

    with pytest.raises(DataValidationError):
        map_futures_instruments(bad_payload)
