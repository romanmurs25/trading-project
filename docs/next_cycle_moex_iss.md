# Cycle 3 status: MOEX ISS read-only historical candles

Цель цикла — добавить безопасную read-only загрузку исторических свечей MOEX ISS и сохранить результат в
storage foundation. Live trading в этом цикле не появляется.

## Реализовано

1. `MoexIssClient` поверх `httpx.AsyncClient`.
2. Mapper payload → `Candle` с `Decimal` и UTC conversion.
3. Pagination по ISS candles endpoint через `start`.
4. Retry/backoff и простой rate limit.
5. Mocked HTTP tests без реальных сетевых вызовов.
6. CLI:
   `trading data backfill-moex --symbol <symbol> --instrument-id <id> --interval 1m --from YYYY-MM-DD --to YYYY-MM-DD`.
7. Сохранение свечей через `StoragePort`: `InMemoryStorage` и `SQLAlchemyStorage`.
8. API endpoint для safe backfill trigger.

## Safety constraints

- Никаких execution methods в MOEX ISS adapter.
- Никаких broker credentials.
- Никаких внешних HTTP-вызовов в тестах.
- Все цены и объёмы остаются `Decimal`.

## Осталось

- Production-grade MOEX trading calendar.
- Order book и last trade read-only endpoints.
- Realtime stream.
- Futures roll/expiry contract model.
- PostgreSQL integration tests поверх docker compose или testcontainers.
