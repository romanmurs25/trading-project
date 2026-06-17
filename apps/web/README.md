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
