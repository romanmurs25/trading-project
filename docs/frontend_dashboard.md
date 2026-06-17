# Frontend Research Dashboard

Cycle 7 добавляет read-only frontend research dashboard внутри существующего monorepo:

```text
apps/web
```

Отдельный frontend repository в этом цикле не создаётся, потому что backend API ещё развивается, а первый
dashboard tightly coupled к текущим research/MOEX endpoints.

## Safety boundary

Frontend:

- не импортирует Python packages;
- не импортирует `trading_core`, storage или broker adapters;
- не читает БД напрямую;
- общается с backend только через HTTP API;
- не хранит secrets;
- не просит broker tokens/API keys;
- не содержит buy/sell buttons, order forms или live trading controls;
- не открывает live market data WebSocket;
- не запускает автоматический polling, который делает write-операции.

Видимый safety banner:

```text
Read-only research dashboard. No live trading. No broker execution.
```

## Запуск

Backend:

```bash
uvicorn apps.api.main:app --reload
```

Frontend:

```bash
npm --prefix apps/web install
VITE_API_BASE_URL=http://localhost:8000 npm --prefix apps/web run dev
```

Docker Compose:

```bash
docker compose up
```

## Конфигурация

`apps/web/.env.example`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Pages

- Dashboard: backend health, basic counts, safety posture.
- Instruments: searchable registry table and detail page.
- Data Quality: session-aware report request and metrics.
- Market Sessions: stored session table with venue/market filters.
- Futures Chain: chain and selected front contract.
- Continuous Series: stored continuous series, components and roll events.
- Research Runs: read-only list of stored research runs.
- Research Run Detail: params, results, equity/drawdown charts and trades.
- Research Report: JSON/markdown-like report view.
- Settings: API base URL, health and safety constraints.

## Decimal handling

Backend remains source of truth for all financial calculations. Frontend receives Decimal values as strings.
Charts convert Decimal strings to JS `number` only for visualization.

## API contract

Frontend API types are handwritten in `apps/web/src/api/types.ts` and must match backend response field names.
Cycle 8 should generate frontend types from the backend OpenAPI schema to reduce contract drift.

## Known limitations

- Нет auth.
- Нет live market stream.
- Нет order placement.
- Нет WebSocket.
- Нет frontend-triggered backfill/sync в MVP.
- In-memory backend data disappears on restart.
- Data shape пока pragmatic, без сгенерированного OpenAPI client.

## Future repo split

Possible future repository name:

```text
trading-project-web
```

Split стоит делать только после стабилизации API contract. Перед split нужны:

- OpenAPI schema/versioning;
- CORS hardening;
- отдельный frontend CI/CD;
- понятные release/version compatibility rules между backend и frontend.
