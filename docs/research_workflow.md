# Research Workflow

Cycle 5 добавляет повторяемый research workflow для оценки стратегий на сохранённых candles. Он не добавляет
live trading, broker execution, realtime market data или внешние HTTP-вызовы.

## Seed instruments and candles

Сначала нужен локальный реестр instruments:

```bash
trading data sync-moex-instruments --asset-class futures --allow-network --write --storage db
```

Затем сохраняются candles:

```bash
trading data backfill-moex \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --allow-network \
  --write \
  --storage db
```

Без `--allow-network` MOEX команды остаются dry-run/skipped.

## Parameter grids

Research принимает несколько `--param key=value1,value2`:

```bash
trading research run \
  --strategy opening_range_breakout \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --storage db \
  --param opening_range_minutes=5,15,30 \
  --param take_profit_r_multiple=1.5,2,3
```

Parameter grid разворачивается в cartesian product. Numeric-looking строки становятся `Decimal`, float
отклоняется. По умолчанию действует guard `max_combinations=500`.

## Data-quality gate

Перед backtest запускается gate поверх `analyze_candle_series`:

- no candles;
- duplicate timestamps;
- missing intervals;
- zero-volume candles при заданном threshold;
- non-monotonic order.

По умолчанию gate строгий. CLI-флаг `--allow-data-quality-warnings` ослабляет gate для exploratory runs.

Важно: текущая проверка `missing intervals` continuous-time based. Она пока не понимает MOEX trading
sessions, выходные, clearing breaks и contract-specific calendars. Для реального MOEX intraday research
используйте gate аккуратно или запускайте exploratory runs с `--allow-data-quality-warnings`, пока не
появится session-aware quality gate.

Cycle 6 добавляет опциональный session-aware gate:

```bash
trading research run \
  --strategy opening_range_breakout \
  --canonical-symbol MOEX:SiH6 \
  --interval 1m \
  --from 2026-01-01 \
  --to 2026-01-02 \
  --session-aware-quality
```

При включении `--session-aware-quality` `quality_report` сохраняет `quality_mode=session_aware`.
По умолчанию остаётся старый `continuous_time` gate, чтобы не ломать существующие сценарии.

## Persistence

Research workflow сохраняет:

- `ResearchRun`;
- `BacktestRun`;
- `ResearchBacktestResult`;
- `BacktestEquityPoint`;
- `BacktestTradeRecord`.

In-memory storage process-local: данные не сохраняются между отдельными CLI process. Для повторяемых CLI
сценариев нужен `--storage db`.

## Reports and comparison

JSON/Markdown report:

```bash
trading research report --research-run-id <id> --storage db --format markdown
```

Comparison:

```bash
trading research compare --research-run-id <id> --storage db --sort-by profit_factor
```

Report включает strategy, symbol, interval, period, parameter grid, data quality summary, top parameter sets,
warnings и known limitations.

## Walk-forward splits

```bash
trading research walk-forward-splits \
  --from 2026-01-01 \
  --to 2026-06-01 \
  --train-days 60 \
  --test-days 20 \
  --step-days 20
```

Cycle 5 генерирует splits, но не запускает полноценную walk-forward optimization.

## Known limitations

- Нет production MOEX calendar.
- Нет continuous futures.
- Нет contract roll.
- Slippage/execution model ограничен `PaperBroker` MVP.
- Нет live trading.
- Нет broker execution.
- Нет realtime market data.
- Нет order book.
- In-memory CLI storage process-local.
- Reports пока общие, не strategy-specific.
- Missing-interval gate пока не session-aware: не учитывает MOEX sessions, выходные, clearing breaks и
  contract-specific calendars.
- Session-aware gate использует configurable MVP MOEX templates, не официальный production calendar.
- Continuous futures MVP пока не делает back-adjustment и не использует liquidity/open-interest roll.

## Next step

Cycle 6 должен добавить session-aware quality checking:

- session-aware data-quality gate для MOEX;
- continuous futures / contract roll;
- richer execution/slippage model;
- strategy-specific research reports;
- PostgreSQL integration tests для research workflow.
