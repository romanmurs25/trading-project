from datetime import date, datetime
from typing import Any

from pydantic import Field

from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, ContractSpec, DomainModel, Instrument, new_id, utc_now
from trading_core.market.roll import (
    RollEvent,
    RollRule,
    build_contract_chain,
    generate_roll_events,
    select_front_contract,
)


class ContinuousSeries(DomainModel):
    id: str = Field(default_factory=new_id)
    venue: str
    underlying_symbol: str
    canonical_symbol: str
    interval: str
    roll_rule: dict[str, Any]
    adjustment_method: str
    start: datetime
    end: datetime
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContinuousSeriesComponent(DomainModel):
    id: str = Field(default_factory=new_id)
    continuous_series_id: str
    instrument_id: str
    canonical_symbol: str
    start: datetime
    end: datetime
    roll_date: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_continuous_futures_series(
    underlying_symbol: str,
    instruments: list[Instrument],
    contract_specs: list[ContractSpec],
    candles_by_instrument: dict[str, list[Candle]],
    start: datetime,
    end: datetime,
    interval: str,
    roll_rule: RollRule,
    adjustment_method: str = "none",
) -> tuple[ContinuousSeries, list[ContinuousSeriesComponent], list[Candle], list[RollEvent]]:
    if adjustment_method != "none":
        raise DataValidationError("only adjustment_method='none' is supported in MVP")
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware")
    chain = build_contract_chain(instruments, contract_specs, underlying_symbol)
    events = generate_roll_events(chain, start, end, roll_rule)
    selected_candles: list[Candle] = []
    warnings: list[str] = []
    for instrument in chain.instruments:
        for candle in candles_by_instrument.get(instrument.id, []):
            if candle.interval != interval or not (start <= candle.ts_start < end):
                continue
            decision = select_front_contract(chain, candle.ts_start, roll_rule)
            if decision.selected_instrument_id == instrument.id:
                selected_candles.append(
                    candle.model_copy(
                        update={
                            "instrument_id": f"continuous:{underlying_symbol}",
                            "source": f"{instrument.id}:continuous-futures:{candle.source}",
                        }
                    )
                )
    selected_candles.sort(key=lambda candle: candle.ts_start)
    if not selected_candles:
        warnings.append("missing candles for selected contracts")

    series = ContinuousSeries(
        venue=chain.venue,
        underlying_symbol=underlying_symbol,
        canonical_symbol=f"{chain.venue}:{underlying_symbol}:CONT",
        interval=interval,
        roll_rule=roll_rule.model_dump(mode="json"),
        adjustment_method=adjustment_method,
        start=start,
        end=end,
        metadata={"warnings": warnings},
    )
    components = _components_from_candles(series.id, selected_candles)
    return series, components, selected_candles, events


def _components_from_candles(series_id: str, candles: list[Candle]) -> list[ContinuousSeriesComponent]:
    components: list[ContinuousSeriesComponent] = []
    current_key: str | None = None
    current_start: datetime | None = None
    current_end: datetime | None = None
    for candle in candles:
        source_instrument = _source_instrument_from_candle(candle)
        if current_key is None:
            current_key = source_instrument
            current_start = candle.ts_start
            current_end = candle.ts_end
            continue
        if source_instrument == current_key:
            current_end = candle.ts_end
            continue
        components.append(
            _component(series_id, current_key, current_start, current_end)
        )
        current_key = source_instrument
        current_start = candle.ts_start
        current_end = candle.ts_end
    if current_key is not None:
        components.append(_component(series_id, current_key, current_start, current_end))
    return components


def _source_instrument_from_candle(candle: Candle) -> str:
    source = str(candle.source)
    if ":continuous-futures:" in source:
        return source.split(":continuous-futures:", 1)[0]
    return candle.instrument_id


def _component(
    series_id: str,
    instrument_id: str,
    start: datetime | None,
    end: datetime | None,
) -> ContinuousSeriesComponent:
    if start is None or end is None:
        raise DataValidationError("continuous component requires timestamps")
    return ContinuousSeriesComponent(
        continuous_series_id=series_id,
        instrument_id=instrument_id,
        canonical_symbol=instrument_id,
        start=start,
        end=end,
        metadata={"source": "continuous-futures"},
    )
