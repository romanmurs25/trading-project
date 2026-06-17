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
trading research run --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --param opening_range_minutes=5,15
trading research report --research-run-id <id> --format markdown
trading research compare --research-run-id <id> --sort-by profit_factor
trading research walk-forward-splits --from 2026-01-01 --to 2026-06-01 --train-days 60 --test-days 20 --step-days 20
trading db check-config
trading db init-placeholder
```

Тесты и качество:

```bash
pytest
ruff check .
mypy .
```

Docker Compose:

```bash
docker compose up
```

Compose поднимает API, PostgreSQL и Redis. В первом MVP база данных ещё не является обязательной для
работы safety spine, но сервис добавлен как будущая точка расширения.

## Адаптеры

- `adapters.paper`: рабочий MVP broker simulator.
- `adapters.moex_iss`: безопасный read-only adapter для исторических свечей MOEX ISS; тесты используют mocks.
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

Следующий рекомендуемый цикл: continuous futures / contract roll, richer slippage/execution model и
strategy-specific research reports.
