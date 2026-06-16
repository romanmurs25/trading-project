# Архитектура

MVP использует clean/hexagonal architecture внутри Python-монолита.

## Слои

- `trading_core.domain` содержит enum, Pydantic-модели, ошибки и Decimal helpers.
- `trading_core.ports` описывает интерфейсы внешнего мира.
- `trading_core.risk` принимает pre-trade решения и управляет kill switch.
- `trading_core.execution` содержит state machine и idempotency helpers.
- `trading_core.strategy` содержит чистые стратегии, которые выпускают только `Signal`.
- `trading_core.backtest` соединяет стратегию, риск и broker simulator через `BacktestBrokerPort`.
- `adapters` реализуют или подготавливают внешние интеграции.
- `apps` собирают ядро и адаптеры в API/CLI.

## Поток ордера в MVP

```text
OrderIntent -> ExecutionEngine -> audit(before_risk_check) -> RiskEngine
  -> rejected: Order NEW -> RISK_REJECTED + audit(order_state_transition)
  -> approved: Order NEW -> APPROVED + audit(order_state_transition)
  -> broker submission: APPROVED -> SUBMITTED -> FILLED/FAILED/etc.
  -> Storage + executions + audit(after_broker_submission)
```

Стратегия не знает о брокере. Брокер не принимает решение о риске. `RiskEngine` является обязательным
контуром перед исполнением. `ExecutionEngine` не выставляет state напрямую: каждый переход проходит через
`OrderStateMachine`.

`ExecutionEngine` создаёт canonical `Order.id` до broker submission и сохраняет snapshots после значимых
переходов состояния. Если adapter возвращает свой `Order.id`, он не становится доменным canonical id:
broker-поля и executions remap-ятся обратно на canonical order.

## Поток backtest

```text
Candle -> Strategy -> Signal -> OrderIntent -> RiskEngine -> BacktestBrokerPort -> Metrics
```

`trading_core.backtest` зависит только от `BacktestBrokerPort`. `PaperBroker` находится в `adapters.paper` и
структурно реализует этот порт.

## Хранение

Для execution flow доступен `InMemoryStorage`. В cycle 3 добавлены SQLAlchemy models, Alembic initial
migration и sync `SQLAlchemyStorage`. Repository tests используют SQLite in-memory, а schema остаётся
совместимой с PostgreSQL.

## MOEX ISS read-only market data

`adapters.moex_iss` реализует только historical candles. Adapter не содержит execution methods и не требует
credentials. CLI/API backfill по умолчанию dry-run и не делает внешний запрос без явного разрешения сети.
