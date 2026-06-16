# Storage Plan

Во втором цикле добавлен SQLAlchemy foundation без реального подключения в unit-тестах.

## Что уже описано

`packages/storage/sqlalchemy_models.py` содержит модели для ключевых таблиц:

- `instruments`
- `candles`
- `signals`
- `order_intents`
- `risk_decisions`
- `orders`
- `executions`
- `positions`
- `backtest_runs`
- `audit_logs`
- `system_events`

Decimal-значения описаны как `Numeric(38, 18)`. Временные метки используют `DateTime(timezone=True)`.

## Индексы и constraints

- `candles`: unique constraint по `venue, instrument_id, interval, ts_start`.
- `orders`: unique index через `idempotency_key`.
- `executions`: nullable unique constraint по `venue, broker_execution_id`.
- `audit_logs`: index по `entity_type, entity_id, ts`.
- `system_events`: index по `event_type, ts`.

## Следующий шаг

В следующем цикле нужно добавить Alembic, первую миграцию, async repositories и integration-тесты с
PostgreSQL через Docker Compose или testcontainers-подход. До этого unit-тесты остаются полностью локальными
и используют `InMemoryStorage`.
