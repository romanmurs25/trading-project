# Development Workflow

Этот проект ведётся через короткие безопасные ветки и отдельные pull request на каждую задачу.

## Установка окружения

Рекомендуется держать виртуальное окружение вне репозитория, чтобы оно не попадало в архивы и commit:

```bash
python3 -m venv /tmp/trading-project-venv
. /tmp/trading-project-venv/bin/activate
python -m pip install -e ".[dev]"
```

## Проверки

Тесты:

```bash
pytest
```

Ruff:

```bash
ruff check .
```

Mypy:

```bash
mypy .
```

Перед PR все три команды должны проходить. Если команда не запускается из-за отсутствующих зависимостей,
сначала установи dev-зависимости в локальное окружение.

GitHub Actions запускает те же проверки на Python 3.12:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy .
pytest
```

## Запуск API

```bash
uvicorn apps.api.main:app --reload
```

Проверка health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

## Synthetic backtest

```bash
trading backtest run-synthetic
```

Команда должна работать без broker credentials, внешних API и live trading.

## DB-backed backtest

После сохранения instruments и candles в storage можно запускать бэктест по canonical symbol:

```bash
trading backtest run-db \
  --strategy opening_range_breakout \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02
```

Команда использует `PaperBroker` и PAPER-копию инструмента. Live venue не используется для исполнения.

## Safe config

```bash
trading config show-safe
```

Команда печатает redacted-конфигурацию. `.env` не коммитится, `.env.example` остаётся безопасным шаблоном.

## MOEX ISS dry-run backfill

Синхронизация локального реестра instruments по умолчанию не ходит в сеть:

```bash
trading data sync-moex-instruments
```

Для read-only сетевого sync нужен явный флаг:

```bash
trading data sync-moex-instruments --asset-class futures --allow-network --write
```

Просмотр локального реестра:

```bash
trading instruments list --venue MOEX --asset-class FUTURES
trading instruments get --canonical-symbol MOEX:SiH6
```

По умолчанию команда не делает внешних HTTP-запросов:

```bash
trading data backfill-moex \
  --symbol SiH6 \
  --instrument-id moex-si \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02
```

Для реального read-only запроса нужен явный флаг:

```bash
trading data backfill-moex \
  --symbol SiH6 \
  --instrument-id moex-si \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --allow-network
```

Сохранение требует явного `--write`; иначе команда остаётся dry-run.

Если инструмент уже есть в storage, можно использовать canonical symbol:

```bash
trading data backfill-moex \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --allow-network \
  --write
```

Проверка качества сохранённых свечей:

```bash
trading data quality \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02
```

## Alembic

Initial migration лежит в `packages/storage/migrations`. Для локального PostgreSQL из docker compose:

```bash
alembic upgrade head
```

Repository-слой в этом цикле sync SQLAlchemy. Default `DATABASE_URL` использует `postgresql+psycopg`.

## Ветки

- `main` защищаем и не работаем напрямую в нём.
- Для каждой задачи создаём отдельную ветку с префиксом `codex/`.
- Пример:

```bash
git switch -c codex/cycle-04-moex-instruments-dataset
```

Название ветки должно коротко описывать одну задачу. Не смешивай несколько независимых изменений в одной
ветке.

## Pull Request

Каждая задача идёт отдельным PR. В описании PR обязательно укажи:

```markdown
## Summary
- Что изменилось.

## Tests
- `pytest`
- `ruff check .`
- `mypy .`

## Known limitations
- Что осталось заглушкой.
- Какие ограничения сохранены осознанно.

## Next step
- Что рекомендуется делать следующим циклом.
```

## Что не добавлять в git

- `.venv/` и другие виртуальные окружения.
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`.
- `*.egg-info/`, `build/`, `dist/`, `*.pyc`.
- `.env`, `.env.*`, credentials, broker tokens, API keys.
- Локальные IDE/OS файлы.

`.env.example` должен оставаться в репозитории как безопасный шаблон конфигурации.
