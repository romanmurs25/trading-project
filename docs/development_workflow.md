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

## Ветки

- Не работаем напрямую в `main`.
- Для каждой задачи создаём отдельную ветку с префиксом `codex/`.
- Пример:

```bash
git switch -c codex/moex-iss-readonly-backfill
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
```

## Что не добавлять в git

- `.venv/` и другие виртуальные окружения.
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`.
- `*.egg-info/`, `build/`, `dist/`, `*.pyc`.
- `.env`, `.env.*`, credentials, broker tokens, API keys.
- Локальные IDE/OS файлы.

`.env.example` должен оставаться в репозитории как безопасный шаблон конфигурации.
