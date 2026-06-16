# Инструкции для будущей работы Codex

## Назначение проекта

Проект строит safety-first backend-first платформу для исследований, бэктестов и paper trading. Основной
рынок будущего развития — MOEX futures. Bybit допускается только как read-only/testnet направление на ранних
этапах. Реальное live trading исполнение не включается по умолчанию.

## Структура

- `apps/api` — FastAPI приложение.
- `apps/cli` — Typer CLI.
- `packages/trading_core` — доменное ядро, стратегии, риск, execution, backtest.
- `packages/adapters` — внешние адаптеры и paper broker.
- `packages/storage` — SQLAlchemy models, Alembic migrations и repository foundation.
- `tests` — unit и integration тесты без реальных credentials.
- `docs` — архитектура, режимы торговли, риск и будущая миграция.

## Команды

```bash
pytest
ruff check .
mypy .
uvicorn apps.api.main:app --reload
trading config show-safe
trading backtest run-synthetic
trading data backfill-moex --symbol SiH6 --instrument-id moex-si --interval 1m --from 2026-01-01 --to 2026-01-02
trading db check-config
```

SQLAlchemy models, Alembic initial migration и sync `SQLAlchemyStorage` уже добавлены. Repository-тесты
используют SQLite in-memory; production PostgreSQL schema должна оставаться совместимой.

## Доменные правила

- Стратегии никогда не размещают ордера.
- Стратегии не вызывают брокеров, БД, API, env и внешние сервисы.
- Стратегии выпускают только `Signal`.
- `trading_core` не импортирует `adapters`.
- Backtest в ядре зависит от `BacktestBrokerPort`, а не от `PaperBroker`.
- Перед добавлением broker adapter сначала пиши mocked tests.
- В тестах нельзя делать реальные внешние HTTP-вызовы.
- Live trading выключен по умолчанию.
- `RiskEngine` обязателен перед исполнением.
- `ExecutionEngine` не должен обходить `RiskEngine`.
- `ExecutionEngine` должен менять состояния ордеров только через `OrderStateMachine`.
- Каждый переход состояния ордера audit-логируется как `order_state_transition`.
- Все действия с ордерами должны иметь idempotency key.
- Все действия с ордерами должны audit-логироваться.
- Деньги, цены, количество, риск, комиссии и PnL — только `Decimal`.
- Никогда не логируй токены, ключи, секреты и authorization headers.
- Внешние API должны быть за портами и адаптерами.
- MOEX ISS adapter остаётся read-only: historical candles only, без execution methods.
- MOEX backfill CLI/API не делает внешний запрос без `--allow-network` / `allow_network=true`.
- Kafka и Java не используются в MVP.
- Kubernetes не используется в MVP.
- Тесты не требуют реальных credentials и не отправляют live-ордера.
- Не коммить `.venv`, caches, `__pycache__`, `*.egg-info`, `.env` и credentials.

## Definition of Done

- `pytest` проходит.
- `ruff check .` проходит.
- `mypy .` проходит или ограничение явно задокументировано.
- Нет реальных credentials в коде.
- Нет внешних HTTP-вызовов в тестах.
- Live order submission невозможен по умолчанию.
- Статический тест `test_trading_core_does_not_import_adapters` проходит.
