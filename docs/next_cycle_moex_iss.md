# Следующий цикл: MOEX ISS read-only historical candles

Цель следующего цикла — добавить безопасную read-only загрузку исторических свечей MOEX ISS и сохранить
результат в storage. Live trading в этом цикле не появляется.

## План

1. Реализовать `MoexIssClient` поверх `httpx.AsyncClient`.
2. Добавить mapper payload → `Candle`.
3. Реализовать pagination по ISS history/candles endpoint.
4. Добавить retry/backoff и простой rate limit.
5. Написать mocked HTTP tests без реальных сетевых вызовов.
6. Добавить CLI:
   `trading data backfill-moex --symbol <symbol> --interval 1m --from YYYY-MM-DD --to YYYY-MM-DD`.
7. Сохранять свечи через `StoragePort`: сначала `InMemoryStorage`, затем SQLAlchemy repository.
8. Добавить API endpoint для backfill trigger только в read-only режиме.

## Safety constraints

- Никаких execution methods в MOEX ISS adapter.
- Никаких broker credentials.
- Никаких внешних HTTP-вызовов в тестах.
- Все цены и объёмы остаются `Decimal`.
