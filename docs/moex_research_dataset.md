# MOEX Research Dataset

Этот документ описывает безопасный вертикальный срез для работы с MOEX futures как research dataset.
Он не добавляет live trading и не требует broker credentials.

## Safety defaults

- MOEX ISS используется только read-only.
- Внешняя сеть в CLI/API выключена по умолчанию.
- Для сетевого запроса нужен `--allow-network` или `allow_network=true`.
- Сохранение требует явного `--write` или `dry_run=false`.
- Backtest по MOEX candles запускается через `PaperBroker`, а не через live venue.
- Стратегии по-прежнему выпускают только `Signal`.

## Instruments registry

Синхронизация futures instruments:

```bash
trading data sync-moex-instruments --asset-class futures --allow-network --write
```

Просмотр:

```bash
trading instruments list --venue MOEX --asset-class FUTURES
trading instruments get --canonical-symbol MOEX:SiH6
```

MOEX `SECID` сохраняется как `native_symbol`, canonical symbol строится как `MOEX:<SECID>`.
Если в ISS payload не хватает полей спецификации, `ContractSpec.metadata.spec_incomplete` становится `true`.

## Candles backfill

Dry-run без сети:

```bash
trading data backfill-moex --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
```

Read-only запрос и сохранение:

```bash
trading data backfill-moex \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --allow-network \
  --write
```

## Data quality

```bash
trading data quality --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
```

Отчёт считает:

- количество свечей;
- начало и конец серии;
- duplicate timestamps;
- non-monotonic order;
- missing intervals;
- zero-volume candles;
- warnings.

Поддерживаемые интервалы: `1m`, `10m`, `1h`, `1d`.

Session-aware quality для MOEX futures:

```bash
trading data quality-session-aware --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
```

Этот отчёт использует configurable MVP session templates и не считает missing candles через ночь, выходные и
clearing breaks. Templates не заменяют официальную проверку MOEX calendar.

## Market sessions, roll and continuous futures

```bash
trading market sessions --from 2026-01-05 --to 2026-01-06 --write
trading futures chain --underlying Si
trading futures select-front --underlying Si --as-of 2026-03-16
trading data build-continuous --underlying Si --interval 1m --from 2026-03-13 --to 2026-03-17 --write
```

`build-continuous` использует только сохранённые instruments/specs/candles. MVP поддерживает только
`adjustment_method="none"` и сохраняет synthetic candles с `instrument_id="continuous:<underlying>"`.

## DB-backed backtest

```bash
trading backtest run-db \
  --strategy opening_range_breakout \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --initial-cash 100000
```

Команда:

- загружает instrument по canonical symbol;
- загружает candles из storage;
- создаёт стратегию через strategy registry;
- запускает `RiskEngine` в `PAPER` режиме;
- исполняет через `PaperBroker`;
- сохраняет `BacktestRun`, если storage это поддерживает;
- печатает JSON metrics.

## Research workflow

После загрузки instruments/candles можно запускать parameter sweep:

```bash
trading research run \
  --strategy opening_range_breakout \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --param opening_range_minutes=5,15,30 \
  --param take_profit_r_multiple=1.5,2,3
```

Отчёты:

```bash
trading research report --research-run-id <id> --format markdown
trading research compare --research-run-id <id> --sort-by profit_factor
```

Research workflow использует сохранённые свечи из storage, проходит data-quality gate перед backtest и
сохраняет research run, per-parameter results, equity curve и trade records.

Для MOEX futures research можно включить session-aware quality:

```bash
trading research run \
  --strategy opening_range_breakout \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --session-aware-quality
```

## Known limitations

- Реальный MOEX trading calendar пока не реализован.
- Session templates являются configurable MVP defaults, а не официальным production calendar.
- Futures roll/expiry policy пока не реализована.
- Continuous futures MVP пока без back-adjustment.
- `run-db` принимает стратегию без CLI-параметров стратегии.
- Research reports пока общие, не strategy-specific.
- PostgreSQL-backed integration tests ещё не добавлены.
- API endpoints пока используют in-memory storage по умолчанию.
