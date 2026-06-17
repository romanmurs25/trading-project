from datetime import date, datetime, timedelta
from typing import Any

from pydantic import Field

from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import ContractSpec, DomainModel, Instrument, new_id


class ContractChain(DomainModel):
    venue: str
    underlying_symbol: str
    instruments: list[Instrument]
    contract_specs: list[ContractSpec]


class RollRule(DomainModel):
    roll_days_before_expiry: int = 5
    prefer_active_contracts: bool = True
    min_days_to_expiry: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class RollDecision(DomainModel):
    as_of: datetime
    selected_instrument_id: str
    selected_canonical_symbol: str
    reason: str
    days_to_expiry: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RollEvent(DomainModel):
    id: str = Field(default_factory=new_id)
    venue: str
    underlying_symbol: str
    from_instrument_id: str
    to_instrument_id: str
    roll_date: date
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_contract_chain(
    instruments: list[Instrument],
    contract_specs: list[ContractSpec],
    underlying_symbol: str,
) -> ContractChain:
    specs_by_instrument = {
        spec.instrument_id: spec
        for spec in contract_specs
        if spec.underlying_symbol == underlying_symbol and _expiry_date(spec) is not None
    }
    chain_instruments = [instrument for instrument in instruments if instrument.id in specs_by_instrument]
    chain_instruments.sort(
        key=lambda instrument: _expiry_date(specs_by_instrument[instrument.id]) or date.max
    )
    if not chain_instruments:
        raise DataValidationError(f"no valid contracts for underlying: {underlying_symbol}")
    return ContractChain(
        venue=chain_instruments[0].venue.value,
        underlying_symbol=underlying_symbol,
        instruments=chain_instruments,
        contract_specs=[specs_by_instrument[instrument.id] for instrument in chain_instruments],
    )


def select_front_contract(chain: ContractChain, as_of: datetime, roll_rule: RollRule) -> RollDecision:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    candidates = _valid_candidates(chain, as_of.date(), roll_rule)
    if not candidates:
        raise DataValidationError("no non-expired contracts in chain")
    selected_index = 0
    first_instrument, first_spec = candidates[0]
    first_expiry = _expiry_date(first_spec)
    if first_expiry is None:
        raise DataValidationError(f"missing expiry for {first_instrument.canonical_symbol}")
    days_to_expiry = (first_expiry - as_of.date()).days
    reason = "front contract"
    if days_to_expiry <= roll_rule.roll_days_before_expiry and len(candidates) > 1:
        selected_index = 1
        reason = "inside roll window"
    selected_instrument, selected_spec = candidates[selected_index]
    expiry = _expiry_date(selected_spec)
    if expiry is None:
        raise DataValidationError(f"missing expiry for {selected_instrument.canonical_symbol}")
    metadata: dict[str, Any] = {}
    if selected_spec.metadata.get("spec_incomplete") is True:
        metadata["spec_incomplete"] = True
        metadata["warning"] = "selected contract spec is incomplete"
    return RollDecision(
        as_of=as_of,
        selected_instrument_id=selected_instrument.id,
        selected_canonical_symbol=selected_instrument.canonical_symbol,
        reason=reason if not metadata else f"{reason}; spec incomplete",
        days_to_expiry=(expiry - as_of.date()).days,
        metadata=metadata,
    )


def generate_roll_events(
    chain: ContractChain,
    start: datetime,
    end: datetime,
    roll_rule: RollRule,
) -> list[RollEvent]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware")
    events: list[RollEvent] = []
    pairs = zip(chain.instruments, chain.instruments[1:], chain.contract_specs, strict=False)
    for current, next_instrument, spec in pairs:
        expiry = _expiry_date(spec)
        if expiry is None:
            continue
        roll_date = expiry - timedelta(days=roll_rule.roll_days_before_expiry)
        if start.date() <= roll_date < end.date():
            events.append(
                RollEvent(
                    venue=chain.venue,
                    underlying_symbol=chain.underlying_symbol,
                    from_instrument_id=current.id,
                    to_instrument_id=next_instrument.id,
                    roll_date=roll_date,
                    reason=f"roll {roll_rule.roll_days_before_expiry} days before expiry",
                )
            )
    return events


def _valid_candidates(
    chain: ContractChain,
    as_of: date,
    roll_rule: RollRule,
) -> list[tuple[Instrument, ContractSpec]]:
    candidates: list[tuple[Instrument, ContractSpec]] = []
    for instrument, spec in zip(chain.instruments, chain.contract_specs, strict=True):
        expiry = _expiry_date(spec)
        if expiry is None:
            continue
        if expiry < as_of + timedelta(days=roll_rule.min_days_to_expiry):
            continue
        if roll_rule.prefer_active_contracts and not instrument.is_active:
            continue
        candidates.append((instrument, spec))
    return candidates


def _expiry_date(spec: ContractSpec) -> date | None:
    return spec.last_trade_date or spec.expiry_date
