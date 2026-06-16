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
- `adapters.moex_iss`: безопасный read-only skeleton без реальных тестовых HTTP-вызовов.
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

## Что не коммитить

- Виртуальные окружения: `.venv/`, локальные venv в корне проекта.
- Кеши: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`.
- Артефакты сборки: `*.egg-info/`, `build/`, `dist/`, `*.pyc`.
- Локальные env-файлы: `.env`, `.env.*`, кроме `.env.example`.
- Credentials, broker tokens, API keys, authorization headers и любые секреты.

## GitHub workflow

- `main` не трогаем напрямую.
- Codex работает только в ветках `codex/*`.
- Каждая задача оформляется отдельным pull request.
- В PR нужно указывать:
  - `summary`: что изменилось;
  - `tests`: какие проверки запускались;
  - `known limitations`: что осталось ограничением или заглушкой.
- Перед PR нужно убедиться, что `pytest`, `ruff check .` и `mypy .` проходят.
- Локальные артефакты, `.env` и credentials не должны попадать в commit.

## Backtest limitations

Backtest остаётся MVP-симулятором. Если stop-loss и take-profit достигнуты в одной свече, используется
консервативное допущение: сначала stop-loss. `latency_ms` в `PaperBroker` зарезервирован и не влияет на
исполнение в MVP.

## Почему Kafka и Java не используются в MVP

MVP строит проверяемое ядро. Kafka, Java, Kubernetes и микросервисы добавили бы операционную сложность
раньше, чем появятся реальные объёмы событий, независимые команды и требования к replay. Будущая миграция
описана в [docs/future_java_kafka_migration.md](docs/future_java_kafka_migration.md).

## Следующий цикл

Следующий рекомендуемый цикл: MOEX ISS read-only historical candles + DB persistence/backfill. План описан в
[docs/next_cycle_moex_iss.md](docs/next_cycle_moex_iss.md).
