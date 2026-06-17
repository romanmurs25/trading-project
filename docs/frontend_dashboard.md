# Frontend Research Dashboard

Cycle 7 добавил read-only frontend research dashboard внутри существующего monorepo. Cycle 8 расширяет его
страницей read-only market data и русскоязычной оболочкой:

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
Только чтение: исследование и рыночные данные. Live trading и broker execution отключены.
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

- Обзор: backend health, базовые счётчики, live-data count и safety posture.
- Инструменты: searchable registry table and detail page.
- Качество данных: session-aware report request and metrics.
- Live Data: read-only ingestion state, demo replay, latest snapshots and events.
- Рыночные сессии: stored session table with venue/market filters.
- Фьючерсная цепочка: chain and selected front contract.
- Непрерывные серии: stored continuous series, components and roll events.
- Исследования: read-only list of stored research runs.
- Детали исследования: params, results, equity/drawdown charts and trades.
- Отчёт исследования: JSON/markdown-like report view.
- Настройки: API base URL, health and safety constraints.

## Decimal handling

Backend remains source of truth for all financial calculations. Frontend receives Decimal values as strings.
Charts convert Decimal strings to JS `number` only for visualization.

## API contract

Backend OpenAPI schema is exported to:

```text
apps/web/src/api/openapi.json
```

Generated TypeScript declarations live in:

```text
apps/web/src/api/generated.ts
```

Commands:

```bash
python3 scripts/export_openapi.py
npm --prefix apps/web run api:types
```

`apps/web/src/api/types.ts` пока остаётся pragmatic handwritten API layer, но generated declarations дают
контрактную базу для постепенного уменьшения drift.

## Known limitations

- Нет auth.
- Нет live market stream.
- Нет order placement.
- Нет WebSocket.
- Нет frontend-triggered backfill/sync в MVP.
- In-memory backend data disappears on restart.
- Data shape пока pragmatic, generated OpenAPI declarations есть, полноценный generated client ещё не внедрён.

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
