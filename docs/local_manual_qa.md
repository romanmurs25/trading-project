# Локальная ручная проверка dashboard

Этот сценарий нужен, чтобы локально поднять backend и frontend и увидеть заполненный read-only dashboard.
Демо-данные синтетические, маленькие, детерминированные и включаются только явным флагом
`APP_SEED_DEMO_DATA=true`.

## Предварительные требования

- Python environment с установленными backend-зависимостями проекта.
- Node.js и npm.
- Frontend-зависимости установлены через `npm ci` в `apps/web`.
- Рабочая директория: корень репозитория.

Пример установки backend-зависимостей:

```bash
python3 -m venv /tmp/trading-project-venv
. /tmp/trading-project-venv/bin/activate
python -m pip install -e ".[dev]"
```

## Запуск backend

Терминал 1:

```bash
PYTHONPATH=packages:. APP_SEED_DEMO_DATA=true uvicorn apps.api.main:app --reload --port 8000
```

Если зависимости уже доступны без `PYTHONPATH`, можно использовать короткий вариант:

```bash
APP_SEED_DEMO_DATA=true uvicorn apps.api.main:app --reload --port 8000
```

## Запуск frontend

Терминал 2:

```bash
cd apps/web
npm ci
VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host 127.0.0.1
```

## Адреса

- Backend health: http://localhost:8000/health
- Frontend: http://localhost:5173

## Ручной чеклист

- Dashboard opens.
- Safety banner is visible.
- Instruments table has demo instruments: `MOEX:SiH6`, `MOEX:SiM6`, `MOEX:RIH6`.
- Instrument detail opens.
- Data Quality page works for `MOEX:SiH6`.
- Live Data page shows demo snapshots.
- Live Data Demo replay button adds read-only snapshots.
- Live Data MOEX poll без сети returns skipped and does not require credentials.
- Market Sessions page has sessions.
- Futures Chain page works with underlying `Si`.
- Continuous Series page shows `MOEX:Si:CONT:1m`.
- Research Runs page has a completed run.
- Research Run detail shows results, equity chart and trades.
- Research Report page opens.
- Settings page shows API URL and safety constraints.
- UI shell and navigation are in Russian.
- No Buy/Sell buttons.
- No order form.
- No broker credential form.
- No live trading controls.

## Демо-режим в Docker Compose

Обычный compose-запуск не включает demo seed:

```bash
docker compose up
```

Для локальной ручной проверки можно включить seed явно:

```bash
APP_SEED_DEMO_DATA=true docker compose up api web
```

## Startup smoke-проверка

Короткая проверка backend без долгоживущих процессов:

```bash
scripts/dev_smoke.sh
```

Скрипт стартует backend с `APP_SEED_DEMO_DATA=true`, проверяет `/health`,
`/api/instruments`, `/api/research/runs` и `/api/continuous-series`, затем останавливает backend.

## Диагностика

- CORS issue: проверь, что frontend открыт с `http://localhost:5173` или `http://127.0.0.1:5173`.
- API not running: открой http://localhost:8000/health и проверь, что backend отвечает.
- Frontend API base URL wrong: запусти frontend с `VITE_API_BASE_URL=http://localhost:8000`.
- Empty dashboard: скорее всего backend запущен без `APP_SEED_DEMO_DATA=true`.
- Port 8000 already in use: запусти backend на другом порту и обнови `VITE_API_BASE_URL`.
- Port 5173 already in use: Vite предложит другой порт; открой URL из вывода `npm run dev`.
- npm install issue: удали локальный `apps/web/node_modules` и повтори `npm ci`.

## Заметка о безопасности

- Demo seed использует только fake local synthetic data.
- Demo seed не делает external network calls.
- Demo seed не требует и не читает broker credentials.
- Live trading не включается.
- Broker execution не включается.
- Frontend остаётся read-only и общается с backend только через HTTP API.
