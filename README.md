# Safety-first intraday trading platform

Это backend-first каркас торговой платформы для исследований, бэктестов и paper trading. Первый цикл
реализации намеренно узкий: доменное ядро, риск-контур, paper broker, минимальный backtest, `/health` и CLI.

## Чем проект является

- Модульный Python-монолит для коротких внутридневных сценариев.
- Безопасная основа для MOEX futures как основного рынка.
- Изолированная среда для стратегий, которые выпускают только `Signal`.
- Каркас, где любой ордер проходит через `RiskEngine` до исполнения.
- Площадка для тестов, paper trading, журнала сделок и будущих адаптеров брокеров.

## Чем проект не является

- Это не финансовый совет.
- Это не «прибыльный бот».
- Это не production-интеграция с реальным брокером.
- Это не Java/Kafka/microservices-система.
- Это не система, которая может отправлять live-ордера по умолчанию.

## Безопасность live trading

По умолчанию:

```text
TRADING_MODE=RESEARCH
ALLOW_LIVE_TRADING=false
```

Live-исполнение должно оставаться невозможным, пока одновременно не включены все защитные условия:
режим `LIVE_GUARDED`, явный флаг `ALLOW_LIVE_TRADING=true`, поддержка live-исполнения адаптером,
положительное решение `RiskEngine`, неактивный `KillSwitch`, allowlist инструмента, свежие рыночные данные,
допустимый спред, idempotency key и audit-события до/после отправки.

## Торговые режимы

- `RESEARCH`: безопасный режим по умолчанию, без реального исполнения.
- `PAPER`: исполнение только через `PaperBroker`.
- `SANDBOX`: будущий режим для песочниц брокеров.
- `LIVE_READONLY`: будущий режим чтения реального аккаунта без заявок.
- `LIVE_GUARDED`: будущий режим live-исполнения с максимальными защитными проверками.

## Локальный запуск

Установка для разработки:

```bash
python3 -m venv /tmp/trading-project-venv
. /tmp/trading-project-venv/bin/activate
python -m pip install -e ".[dev]"
```

API:

```bash
uvicorn apps.api.main:app --reload
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

CLI:

```bash
trading config show-safe
trading risk status
trading risk kill
trading backtest run-synthetic
trading backtest run-db --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading instruments list --venue MOEX --asset-class FUTURES
trading instruments get --canonical-symbol MOEX:SiH6
trading data sync-moex-instruments
trading data backfill-moex --symbol SiH6 --instrument-id moex-si --interval 1m --from 2026-01-01 --to 2026-01-02
trading data quality --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading data quality-session-aware --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading market sessions --from 2026-01-05 --to 2026-01-06 --write
trading futures chain --underlying Si
trading futures select-front --underlying Si --as-of 2026-03-16
trading data build-continuous --underlying Si --interval 1m --from 2026-03-13 --to 2026-03-17 --write
trading research run --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --param opening_range_minutes=5,15
trading research run --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --session-aware-quality
trading research report --research-run-id <id> --format markdown
trading research compare --research-run-id <id> --sort-by profit_factor
trading research walk-forward-splits --from 2026-01-01 --to 2026-06-01 --train-days 60 --test-days 20 --step-days 20
trading live-data state
trading live-data replay-demo --canonical-symbol MOEX:SiH6 --interval 1m --count 5
trading live-data candles --canonical-symbol MOEX:SiH6 --interval 1m
trading live-data events --source DEMO_REPLAY
trading live-data poll-moex-once --symbol SiH6 --instrument-id moex:SiH6 --interval 1m
trading db check-config
trading db init-placeholder
```

Тесты и качество:

```bash
pytest
ruff check .
mypy .
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run test -- --run
npm --prefix apps/web run build
npm run api:openapi
npm run web:api-types
```

Frontend read-only dashboard:

```bash
npm --prefix apps/web install
VITE_API_BASE_URL=http://localhost:8000 npm --prefix apps/web run dev
```

### Локальная ручная проверка dashboard

Полный сценарий: [docs/local_manual_qa.md](docs/local_manual_qa.md).

Терминал 1:

```bash
PYTHONPATH=packages:. APP_SEED_DEMO_DATA=true uvicorn apps.api.main:app --reload --port 8000
```

Терминал 2:

```bash
cd apps/web
npm ci
VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host 127.0.0.1
```

Затем открыть:

```text
http://localhost:5173
```

Доступные root-команды:

```bash
npm run web:install
npm run web:dev
npm run web:lint
npm run web:typecheck
npm run web:test
npm run web:build
```

Docker Compose:

```bash
docker compose up
```

Compose поднимает API, frontend dashboard, PostgreSQL и Redis. В первом MVP база данных ещё не является
обязательной для работы safety spine, но сервис добавлен как будущая точка расширения.

## Адаптеры

- `adapters.paper`: рабочий MVP broker simulator.
- `adapters.moex_iss`: безопасный read-only adapter для исторических свечей MOEX ISS; тесты используют mocks.
- `adapters.demo`: offline replay adapter для read-only live-data витрины.
- `adapters.tinvest`: skeleton с запретом live-исполнения.
- `adapters.bybit`: skeleton для read-only/testnet-first подхода; Bybit TradFi не реализуется.

## Что сделано в Cycle 1

- Базовые доменные модели и enum.
- Decimal helpers и безопасная конфигурация.
- `RiskEngine`, `KillSwitch`, `OrderStateMachine`.
- `PaperBroker`, минимальный `BacktestEngine`.
- FastAPI `/health`, CLI и документация.

## Что добавлено в Cycle 2

- Убраны локальные артефакты из рабочей копии.
- Добавлен статический тест, запрещающий `trading_core -> adapters` imports.
- `BacktestEngine` переведён на `BacktestBrokerPort`.
- Добавлен запрет float для финансовых Pydantic-полей.
- Усилен `RiskEngine`: idempotency, live allowlist, max open positions, reduce-only.
- Реализован безопасный `ExecutionEngine.execute_order_intent`.
- Добавлены `InMemoryStorage`, `PaperExecutionAdapter`, pending limit orders и idempotency в paper broker.
- Backtest теперь поддерживает stop-loss, take-profit, forced close и расширенные метрики.
- Добавлен SQLAlchemy model foundation и [docs/storage_plan.md](docs/storage_plan.md).

## Что добавлено в Cycle 3

- `ExecutionEngine` валидирует переходы ордеров через `OrderStateMachine` и audit-логирует transitions.
- `PaperBroker` ведёт closed trades с entry/exit commission, partial close и reversal accounting.
- Реализован read-only MOEX ISS historical candles adapter с retry/backoff, pagination и UTC mapping.
- Добавлен safe CLI/API backfill: без `--allow-network` / `allow_network=true` внешняя сеть не используется.
- Добавлены Alembic initial migration и sync `SQLAlchemyStorage` для базового persistence.
- Добавлен GitHub Actions CI для `ruff check .`, `mypy .`, `pytest`.

## Что добавлено в Cycle 4

- Расширены `Instrument`/`ContractSpec` и storage repository для реестра инструментов и спецификаций.
- Добавлена Alembic migration `20260617_0002_contract_specs`.
- Реализован read-only MOEX ISS instruments sync для futures без внешних HTTP-вызовов в тестах.
- Добавлены CLI/API для `instruments list/get` и безопасного `sync-moex-instruments`.
- `backfill-moex` умеет работать по `--canonical-symbol` из storage.
- Добавлен `backtest run-db` для запуска стратегии по сохранённым свечам через `PaperBroker`.
- Добавлен strategy registry с `create_strategy`.
- Добавлен отчёт качества свечей `trading data quality`.
- Подробнее: [docs/moex_research_dataset.md](docs/moex_research_dataset.md).

## Что добавлено в Cycle 5

- Добавлен research workflow для повторяемой оценки стратегий.
- Добавлены parameter grids, strategy metadata, data-quality gate и walk-forward splits.
- `BacktestResult` теперь содержит equity curve и trade records.
- Добавлены storage-модели, Alembic migration `20260617_0003_research_workflow` и repository methods для
  research runs/results/equity/trades.
- Добавлены CLI/API `research run/report/compare`.
- Добавлена Markdown/JSON report generation.
- Подробнее: [docs/research_workflow.md](docs/research_workflow.md).

## Что добавлено в Cycle 6

- Добавлен `trading_core.market`: MOEX futures session templates, calendar service, contract roll model,
  continuous futures MVP и execution cost config.
- Добавлен session-aware data-quality report/gate: overnight/weekend/clearing gaps не считаются missing.
- Добавлены storage-модели, repository methods и Alembic migration `20260617_0004_market_sessions_continuous`
  для market sessions, continuous series/components и roll events.
- Добавлены CLI/API для генерации sessions, session-aware quality, futures chain/front-contract selection и
  continuous futures build.
- Research workflow получил опциональный `--session-aware-quality` и execution-cost flags.
- Подробнее: [docs/moex_market_realism.md](docs/moex_market_realism.md).

## Что добавлено в Cycle 7

- Добавлен read-only frontend research dashboard в `apps/web` на Vite, React и TypeScript.
- Dashboard общается с backend только через HTTP API и не импортирует Python packages.
- Добавлены страницы instruments, data quality, sessions, futures chain, continuous series, research runs,
  research run detail, reports и settings.
- Добавлены read-only API endpoints для research equity/trades, continuous series/components и roll events.
- CI расширен frontend-проверками: lint, typecheck, Vitest и build.
- Подробнее: [docs/frontend_dashboard.md](docs/frontend_dashboard.md).

## Что добавлено в Cycle 8

- Добавлен read-only market data spine: live candle snapshots, ingestion runs/events и состояние freshness.
- Добавлены storage-модели, repository methods и Alembic migration `20260617_0005_read_only_market_data`.
- Добавлен offline `adapters.demo` replay и безопасный MOEX ISS polling-once adapter.
- Добавлены CLI/API `live-data state/events/candles/replay-demo/poll-moex-once`.
- Demo seed теперь заполняет live-data snapshots/events без внешней сети.
- Frontend переведён на русскую read-only оболочку и получил страницу `/live-data`.
- Добавлен экспорт OpenAPI schema и генерация frontend TypeScript declarations.
- Подробнее: [docs/read_only_market_data.md](docs/read_only_market_data.md).

## Что не коммитить

- Виртуальные окружения: `.venv/`, локальные venv в корне проекта.
- Кеши: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`.
- Артефакты сборки: `*.egg-info/`, `build/`, `dist/`, `*.pyc`.
- Локальные env-файлы: `.env`, `.env.*`, кроме `.env.example`.
- Credentials, broker tokens, API keys, authorization headers и любые секреты.

## GitHub workflow

- `main` защищаем и не трогаем напрямую.
- Codex работает только в ветках `codex/*`.
- Каждый цикл или отдельная задача оформляется отдельным pull request.
- В PR нужно указывать:
  - `summary`: что изменилось;
  - `tests`: какие проверки запускались;
  - `known limitations`: что осталось ограничением или заглушкой;
  - `next step`: рекомендуемый следующий шаг.
- Перед PR нужно убедиться, что `pytest`, `ruff check .` и `mypy .` проходят.
- Локальные артефакты, `.env` и credentials не должны попадать в commit.

Пример ветки:

```bash
git switch -c codex/cycle-04-moex-instruments-dataset
```

## Backtest limitations

Backtest остаётся MVP-симулятором. Если stop-loss и take-profit достигнуты в одной свече, используется
консервативное допущение: сначала stop-loss. `latency_ms` в `PaperBroker` зарезервирован и не влияет на
исполнение в MVP.

## Почему Kafka и Java не используются в MVP

MVP строит проверяемое ядро. Kafka, Java, Kubernetes и микросервисы добавили бы операционную сложность
раньше, чем появятся реальные объёмы событий, независимые команды и требования к replay. Будущая миграция
описана в [docs/future_java_kafka_migration.md](docs/future_java_kafka_migration.md).

## Следующий цикл

Следующий рекомендуемый цикл: frontend/API contract hardening, auth boundary для read-only dashboard,
persisted ingestion jobs, official MOEX calendar integration и более реалистичная session/regime аналитика.
