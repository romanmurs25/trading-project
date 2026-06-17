# Read-only market data ingestion

Cycle 8 добавляет безопасный вертикальный срез для live-like рыночных данных без торговли и без broker execution.

## Safety boundary

- По умолчанию все команды и endpoints работают offline.
- Внешняя сеть для MOEX ISS polling доступна только при явном `--allow-network` или `allow_network=true`.
- Demo replay использует только локальные synthetic candles.
- Ingestion run всегда `read_only=true`.
- Live trading, order placement, broker credentials и WebSocket market stream не добавлены.
- Тесты не делают внешние HTTP-вызовы.

## Доменные модели

Новый пакет:

```text
packages/trading_core/live_data
```

Основные модели:

- `MarketDataIngestionRun`: запуск read-only ingestion.
- `MarketDataEvent`: audit-like события ingestion.
- `LiveCandleSnapshot`: последний известный snapshot свечи.
- `MarketDataState`: агрегированное состояние для API/UI.

Все цены, объёмы и value остаются `Decimal` на backend.

## Storage

Добавлены методы `StoragePort` для:

- сохранения и чтения ingestion runs;
- сохранения и чтения market data events;
- upsert/list latest live candle snapshots.

SQLAlchemy migration:

```text
20260617_0005_read_only_market_data
```

Таблицы:

- `market_data_ingestion_runs`
- `market_data_events`
- `live_candle_snapshots`

`live_candle_snapshots` использует unique market key:

```text
source, venue, instrument_id, interval, ts_start
```

## CLI

```bash
trading live-data state
trading live-data replay-demo --canonical-symbol MOEX:SiH6 --interval 1m --count 5
trading live-data candles --canonical-symbol MOEX:SiH6 --interval 1m
trading live-data events --source DEMO_REPLAY
trading live-data poll-moex-once --symbol SiH6 --instrument-id moex:SiH6 --interval 1m
```

`poll-moex-once` без `--allow-network` возвращает `skipped`.

Для реального read-only запроса MOEX ISS:

```bash
trading live-data poll-moex-once \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --lookback-minutes 5 \
  --allow-network
```

По умолчанию это `dry-run`; для сохранения snapshots нужен `--write`.

## API

Endpoints:

- `GET /api/live-data/state`
- `GET /api/live-data/events`
- `GET /api/live-data/candles`
- `POST /api/live-data/replay-demo`
- `POST /api/live-data/poll/moex-once`

`poll/moex-once` без `allow_network=true` возвращает `skipped` и не делает внешний запрос.

## Frontend

Страница:

```text
/live-data
```

Показывает:

- состояние ingestion;
- число live snapshots;
- stale count;
- последние свечи;
- ingestion events;
- безопасные операции demo replay и MOEX no-network check.

Frontend продолжает работать только через HTTP API и не импортирует Python packages.

## OpenAPI и frontend types

Экспорт схемы:

```bash
python3 scripts/export_openapi.py
```

Генерация frontend declarations:

```bash
npm --prefix apps/web run api:types
```

Root helper:

```bash
npm run web:api-types
```

Для `npm run web:api-types` текущий `python3` должен видеть backend-зависимости проекта, например из
активированного virtualenv.

## Ограничения

- Нет live market data stream.
- Нет WebSocket.
- Нет scheduler/background ingestion jobs.
- MOEX polling MVP использует historical candles adapter как read-only источник.
- Production MOEX trading calendar/holidays всё ещё остаются отдельной задачей.
- In-memory storage не сохраняет данные между процессами.
