# Storage Plan

Во втором цикле добавлен SQLAlchemy foundation, в третьем — Alembic initial migration и sync repository
foundation, в четвёртом — реестр MOEX instruments/contract specs и DB-backed dataset workflow.

## Что уже описано и реализовано

`packages/storage/sqlalchemy_models.py` содержит модели для ключевых таблиц:

- `instruments`
- `contract_specs`
- `candles`
- `signals`
- `order_intents`
- `risk_decisions`
- `orders`
- `executions`
- `positions`
- `backtest_runs`
- `research_runs`
- `research_backtest_results`
- `backtest_equity_points`
- `backtest_trade_records`
- `audit_logs`
- `system_events`

Decimal-значения описаны как `Numeric(38, 18)`. Временные метки используют `DateTime(timezone=True)`.

## Индексы и constraints

- `instruments`: unique `canonical_symbol`, composite index по `venue, asset_class, native_symbol`.
- `contract_specs`: unique constraint по `instrument_id`.
- `candles`: unique constraint по `venue, instrument_id, interval, ts_start`.
- `orders`: unique index через `idempotency_key`.
- `executions`: nullable unique constraint по `venue, broker_execution_id`.
- `research_runs`: indexes по `strategy_id`, `canonical_symbol`, `instrument_id`, `status`.
- `research_backtest_results`: indexes по `research_run_id`, `backtest_run_id`, `strategy_id`,
  `canonical_symbol`, `instrument_id`, `status`.
- `backtest_equity_points`: index по `backtest_run_id`.
- `backtest_trade_records`: indexes по `backtest_run_id`, `instrument_id`.
- `audit_logs`: index по `entity_type, entity_id, ts`.
- `system_events`: index по `event_type, ts`.

## Реализованные repository methods

- `save_instrument`, `save_instruments`
- `get_instrument`, `get_instrument_by_canonical_symbol`, `list_instruments`
- `save_contract_spec`, `get_contract_spec`
- `save_candles`, `load_candles`
- `save_research_run`, `get_research_run`, `list_research_runs`
- `save_research_backtest_result`, `get_research_backtest_result`, `list_research_backtest_results`
- `save_backtest_equity_points`, `load_backtest_equity_points`
- `save_backtest_trade_records`, `load_backtest_trade_records`
- базовые save-methods для signals, order intents, risk decisions, orders, executions, positions, events и
  backtest runs

## Следующий шаг

Следующий storage-шаг — добавить PostgreSQL-backed integration tests и richer query methods для research
reports/equity/trades. В MVP repository выбран sync SQLAlchemy, чтобы Alembic и runtime использовали один
драйвер (`postgresql+psycopg`).
