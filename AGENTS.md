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
- `packages/storage` — будущий слой хранения.
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
trading db check-config
```

SQLAlchemy models уже описаны. Alembic-миграции будут добавлены в следующих циклах. До появления
Alembic-команд не имитируй рабочие миграции.

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
- Все действия с ордерами должны иметь idempotency key.
- Все действия с ордерами должны audit-логироваться.
- Деньги, цены, количество, риск, комиссии и PnL — только `Decimal`.
- Никогда не логируй токены, ключи, секреты и authorization headers.
- Внешние API должны быть за портами и адаптерами.
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
