# Архитектура

MVP использует clean/hexagonal architecture внутри Python-монолита.

## Слои

- `trading_core.domain` содержит enum, Pydantic-модели, ошибки и Decimal helpers.
- `trading_core.ports` описывает интерфейсы внешнего мира.
- `trading_core.risk` принимает pre-trade решения и управляет kill switch.
- `trading_core.execution` содержит state machine и idempotency helpers.
- `trading_core.strategy` содержит чистые стратегии, которые выпускают только `Signal`.
- `trading_core.backtest` соединяет стратегию, риск и broker simulator через `BacktestBrokerPort`.
- `trading_core.market` описывает market sessions, calendar classification, futures roll и continuous series
  для research/backtest workflows.
- `adapters` реализуют или подготавливают внешние интеграции.
- `apps` собирают ядро и адаптеры в API/CLI.
- `apps/web` содержит read-only frontend research dashboard. Он не импортирует Python packages и общается с
  backend только через HTTP API.

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
migration и sync `SQLAlchemyStorage`. В cycle 4 storage расширен реестром `instruments`, `contract_specs`,
поиском по `canonical_symbol` и загрузкой свечей для DB-backed backtest. Repository tests используют SQLite
in-memory, а schema остаётся совместимой с PostgreSQL.

## MOEX ISS read-only market data

`adapters.moex_iss` реализует только historical candles. Adapter не содержит execution methods и не требует
credentials. CLI/API backfill по умолчанию dry-run и не делает внешний запрос без явного разрешения сети.

## MOEX research dataset flow

```text
MOEX ISS securities payload -> Instrument/ContractSpec mapper -> StoragePort
MOEX ISS candles payload -> Candle mapper -> StoragePort
StoragePort -> backtest run-db -> PaperBroker + RiskEngine -> BacktestRun
StoragePort -> data quality -> CandleQualityReport
StoragePort -> research run -> DataQualityGate -> parameter grid -> BacktestEngine -> research results/report
```

MOEX инструменты сохраняются с `Venue.MOEX`, но `backtest run-db` запускает PAPER-копию инструмента и свечей.
Это сохраняет безопасность RiskEngine: исторические MOEX-данные используются как dataset, а не как live venue.

## Research workflow

`trading_core.research` содержит модели, parameter grid, data-quality gate, runner, reporting и walk-forward
splits. `ResearchRunner` зависит от `StoragePort`, `BacktestEngine`, `RiskEngine` и injected
`broker_factory`. Он не импортирует `adapters.paper`; CLI/API собирают runner с `PaperBroker` на app-слое.

Research flow:

```text
ResearchRun request
  -> load Instrument/Candles from StoragePort
  -> DataQualityGate
  -> parse parameter grid
  -> create Strategy via registry
  -> BacktestEngine + PaperBroker factory
  -> save BacktestRun, ResearchBacktestResult, equity curve, trade records
  -> JSON/Markdown report and comparison
```

API research endpoints MVP выполняются синхронно и используют `app.state.storage`. Они не делают внешних
сетевых запросов и не добавляют live execution path.

## Frontend research dashboard

Cycle 7 добавляет Vite/React приложение в `apps/web` внутри monorepo:

```text
Browser -> apps/web -> HTTP API -> FastAPI routers -> StoragePort
```

Frontend показывает сохранённые instruments, quality reports, sessions, futures chain, continuous futures и
research результаты. Он не имеет доступа к БД, broker adapters, `trading_core` или env backend напрямую.
В интерфейсе нет order forms, broker credential forms, live trading controls, live stream/WebSocket или
автоматического polling, который запускает write-операции.

## MOEX market realism

Cycle 6 добавляет market-structure слой без live-streaming и без broker execution:

```text
MOEX configurable session templates -> MarketCalendarService -> session-aware quality
Instrument/ContractSpec registry -> ContractChain -> RollRule -> ContinuousSeries MVP
Stored candles -> continuous-futures build -> storage -> research/backtest
```

MOEX futures session templates находятся в `trading_core.market.moex_templates`. Это configurable MVP
defaults, а не официальная production-версия календаря биржи. `MarketCalendarService` хранит generated
session start/end в UTC, классифицирует timestamps half-open интервалами и строит expected candle timestamps
только внутри trading sessions.

`analytics.session_quality` отличается от continuous-time quality: gaps через ночь, выходные и clearing
breaks не считаются missing candles. Candles вне trading sessions считаются unexpected out-of-session.

Continuous futures MVP использует `ContractSpec.expiry_date` / `last_trade_date`, `RollRule` и сохранённые
candles. Поддерживается только `adjustment_method="none"`; back-adjustment, liquidity/open-interest roll и
точная PnL attribution by session пока не реализованы.
