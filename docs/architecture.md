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
  -> rejected: Order(RISK_REJECTED) + audit(risk_rejected)
  -> approved: audit(before_broker_submission) -> ExecutionPort -> Order/Executions
  -> Storage + audit(after_broker_submission)
```

Стратегия не знает о брокере. Брокер не принимает решение о риске. `RiskEngine` является обязательным
контуром перед исполнением.

## Поток backtest

```text
Candle -> Strategy -> Signal -> OrderIntent -> RiskEngine -> BacktestBrokerPort -> Metrics
```

`trading_core.backtest` зависит только от `BacktestBrokerPort`. `PaperBroker` находится в `adapters.paper` и
структурно реализует этот порт.

## Хранение

Для execution flow доступен `InMemoryStorage`. SQLAlchemy model foundation описан в
`packages/storage/sqlalchemy_models.py`, план миграций — в `docs/storage_plan.md`. Alembic будет добавлен
следующим storage-циклом.
