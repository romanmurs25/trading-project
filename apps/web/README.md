# Frontend Research Dashboard

`apps/web` — read-only dashboard для исследования сохранённых данных backend. Это не торговый терминал.

## Установка

```bash
npm install
```

## Запуск

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Backend запускается отдельно:

```bash
uvicorn apps.api.main:app --reload
```

## Локальная ручная проверка dashboard

Полный сценарий: [../../docs/local_manual_qa.md](../../docs/local_manual_qa.md).

Терминал 1 из корня репозитория:

```bash
PYTHONPATH=packages:. APP_SEED_DEMO_DATA=true uvicorn apps.api.main:app --reload --port 8000
```

Терминал 2:

```bash
cd apps/web
npm ci
VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host 127.0.0.1
```

Открыть:

```text
http://localhost:5173
```

## Проверки

```bash
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

## Страницы

- Dashboard
- Instruments
- Instrument detail
- Data Quality
- Market Sessions
- Futures Chain
- Continuous Series
- Research Runs
- Research Run Detail
- Research Report
- Settings

## Safety limitations

- Нет live trading.
- Нет broker execution.
- Нет order forms.
- Нет broker credential/token forms.
- Нет live market data WebSocket.
- Нет frontend-доступа к БД, Python packages, broker adapters или `trading_core`.
- Все данные приходят только через HTTP API.
- Decimal strings конвертируются в JS `number` только для отрисовки графиков; backend остаётся источником
  истины для расчётов.
