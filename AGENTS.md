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
trading instruments list --venue MOEX --asset-class FUTURES
trading data sync-moex-instruments
trading data backfill-moex --symbol SiH6 --instrument-id moex-si --interval 1m --from 2026-01-01 --to 2026-01-02
trading data backfill-moex --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading data quality --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading data quality-session-aware --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading market sessions --from 2026-01-05 --to 2026-01-06 --write
trading futures chain --underlying Si
trading futures select-front --underlying Si --as-of 2026-03-16
trading data build-continuous --underlying Si --interval 1m --from 2026-03-13 --to 2026-03-17 --write
trading backtest run-db --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading research run --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --param opening_range_minutes=5,15
trading research run --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --session-aware-quality
trading research report --research-run-id <id> --format json
trading research compare --research-run-id <id> --sort-by profit_factor
trading research walk-forward-splits --from 2026-01-01 --to 2026-06-01 --train-days 60 --test-days 20 --step-days 20
trading live-data state
trading live-data replay-demo --canonical-symbol MOEX:SiH6 --interval 1m --count 5
trading live-data poll-moex-once --symbol SiH6 --instrument-id moex:SiH6 --interval 1m
trading db check-config
npm --prefix apps/web install
npm --prefix apps/web run dev
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run test -- --run
npm --prefix apps/web run build
npm run api:openapi
npm run web:api-types
```

SQLAlchemy models, Alembic migrations и sync `SQLAlchemyStorage` уже добавлены. Repository-тесты используют
SQLite in-memory; production PostgreSQL schema должна оставаться совместимой.

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
- MOEX ISS instruments sync остаётся read-only и не требует credentials.
- MOEX backfill CLI/API не делает внешний запрос без `--allow-network` / `allow_network=true`.
- Read-only live-data ingestion не делает внешний запрос без `--allow-network` / `allow_network=true`.
- Demo live-data replay использует только offline synthetic candles.
- `backtest run-db` запускает сохранённые MOEX-свечи через PAPER-копию инструмента, не через live venue.
- `ResearchRunner` принимает `broker_factory`; `trading_core` не должен импортировать `adapters.paper`.
- Research workflow использует только сохранённые candles из storage и не делает external HTTP.
- Data-quality gate должен выполняться до parameter sweep/backtest execution.
- MOEX session templates являются configurable MVP defaults, а не официальным production calendar.
- Session-aware quality должен использовать только сохранённые candles и локальные templates.
- Continuous futures MVP не делает price adjustment и не должен использовать live/streaming data.
- Roll rules MVP основаны на expiry/last_trade_date; liquidity/open-interest roll пока не реализован.
- Frontend dashboard живёт в `apps/web`, работает только через HTTP API и не импортирует Python packages.
- Frontend dashboard остаётся read-only: никаких order forms, broker credentials, live trading controls или WebSocket.
- Frontend UI по умолчанию русскоязычный, но enum/status/domain IDs из API могут отображаться как технические значения.
- Decimal strings могут конвертироваться в JS `number` только для отрисовки графиков; расчёты остаются на backend.
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
