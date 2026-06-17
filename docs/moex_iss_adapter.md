# MOEX ISS Read-Only Adapter

`adapters.moex_iss` реализует только безопасное чтение исторических свечей MOEX ISS. В адаптере нет
execution methods, broker credentials, live order submission или account operations.

## Safety boundaries

- Adapter read-only.
- Нет `place_order`, `cancel_order` и других execution methods.
- Тесты используют mocked HTTP или fake client.
- CLI/API не делают внешний запрос без явного `--allow-network` / `allow_network=true`.
- Live trading не добавляется и остаётся невозможным по умолчанию.

## Interval mapping

MOEX ISS candles endpoint использует числовые интервалы:

- `1m` -> `1`
- `10m` -> `10`
- `1h` -> `60`
- `1d` -> `24`

Неподдержанный interval вызывает `DataValidationError`.

## Pagination

`MoexIssMarketDataAdapter` запрашивает страницы через параметр `start`. Если размер страницы меньше
`page_size`, pagination завершается. Для MVP `page_size` по умолчанию равен `100`.

## Retry/backoff

`MoexIssClient` повторяет временные ошибки:

- network errors;
- HTTP `429`;
- HTTP `5xx`.

После исчерпания попыток ошибка превращается в `AdapterError`. Ответ JSON разбирается через
`json.loads(..., parse_float=Decimal)`, чтобы финансовые значения не попадали в домен как `float`.

## Timestamp handling

MOEX ISS обычно отдаёт naive datetime в timezone биржи. Mapper интерпретирует такие даты как
`Europe/Moscow`, затем конвертирует их в timezone-aware UTC `datetime`.

## Commands

Синхронизация futures instruments по умолчанию не делает внешний запрос:

```bash
trading data sync-moex-instruments
```

Read-only запрос к MOEX ISS instruments требует явного флага:

```bash
trading data sync-moex-instruments --asset-class futures --allow-network --write
```

Просмотр локального реестра:

```bash
trading instruments list --venue MOEX --asset-class FUTURES
trading instruments get --canonical-symbol MOEX:SiH6
```

Dry-run без сети:

```bash
trading data backfill-moex --symbol SiH6 --instrument-id moex-si --interval 1m --from 2026-01-01 --to 2026-01-02
```

Read-only запрос с явным разрешением сети:

```bash
trading data backfill-moex --symbol SiH6 --instrument-id moex-si --interval 1m --from 2026-01-01 --to 2026-01-02 --allow-network
```

Сохранение требует `--write`.

После синхронизации instruments можно использовать canonical symbol:

```bash
trading data backfill-moex --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --allow-network --write
```

Проверка качества локальных свечей:

```bash
trading data quality --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
```

## Migrations

```bash
alembic upgrade head
```

## Known limitations

- Нет real broker execution.
- Нет order book.
- Нет realtime stream.
- Нет production-grade MOEX trading calendar.
- Futures contract roll/expiry пока не решены.
- Specs могут быть помечены `metadata.spec_incomplete=true`, если MOEX payload не содержит всех полей.
