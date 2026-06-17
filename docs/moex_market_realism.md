# MOEX Market Realism

Cycle 6 добавляет research-only слой понимания MOEX futures market structure. Он не добавляет live data
stream, broker execution или live trading.

## Session Templates

`trading_core.market.moex_templates` содержит configurable MVP defaults для FORTS/MOEX futures:

- morning session;
- main session;
- intraday clearing break;
- evening clearing break;
- evening session.

Templates используют `Europe/Moscow`, а generated `MarketSession.start/end` сохраняются в UTC. Эти defaults
не являются официальным production calendar и должны быть проверены против календаря MOEX перед реальным
research-grade использованием.

```bash
trading market sessions --from 2026-01-05 --to 2026-01-06 --venue MOEX --market forts --write
```

## Session-Aware Quality

Continuous-time quality считает все интервалы между `start` и `end`. Session-aware quality строит expected
timestamps только внутри trading sessions:

- overnight gaps не считаются missing;
- weekend gaps не считаются missing;
- clearing breaks не считаются missing;
- candles вне trading sessions считаются unexpected out-of-session.

```bash
trading data quality-session-aware --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02
trading research run --strategy opening_range_breakout --canonical-symbol MOEX:SiH6 --interval 1m --from 2026-01-01 --to 2026-01-02 --session-aware-quality
```

## Contract Chain And Roll

`trading_core.market.roll` строит `ContractChain` из сохранённых `Instrument` и `ContractSpec`. Front contract
selection использует `expiry_date` или `last_trade_date` и `RollRule.roll_days_before_expiry`.

```bash
trading futures chain --underlying Si
trading futures select-front --underlying Si --as-of 2026-03-16 --roll-days-before-expiry 5
```

MVP не использует volume/open interest. Production roll может потребовать liquidity-based rules.

## Continuous Futures MVP

`trading data build-continuous` строит synthetic series из сохранённых candles:

```bash
trading data build-continuous --underlying Si --interval 1m --from 2026-03-13 --to 2026-03-17 --write
```

MVP behavior:

- только `adjustment_method="none"`;
- canonical symbol включает interval: `MOEX:<underlying>:CONT:<interval>`, например `MOEX:Si:CONT:1m`;
- synthetic candles получают `instrument_id="continuous:<underlying>"`;
- components сохраняют, какой contract использовался на диапазоне;
- roll events сохраняются отдельно;
- price back-adjustment не реализован.

## Execution Costs

`BacktestExecutionCostConfig` задаёт Decimal-only параметры:

- `commission_rate`;
- `fixed_commission_per_order`;
- `slippage_ticks`;
- `spread_bps`.

CLI `backtest run-db` и `research run` принимают `--commission-rate`, `--slippage-ticks`, `--spread-bps`.
В MVP `PaperBroker` получает `commission_rate` и `slippage`; полный spread simulator пока не реализован.

## API

MVP endpoints:

- `GET /api/market/sessions`;
- `POST /api/market/sessions/generate`;
- `GET /api/data/quality/session-aware`;
- `GET /api/futures/chain`;
- `GET /api/futures/select-front`;
- `POST /api/data/continuous/build`.

Все endpoints используют `app.state.storage`, не делают external HTTP и не создают live execution path.

## Known Limitations

- Нет official MOEX production calendar integration.
- Session templates являются configurable MVP defaults.
- Нет liquidity/open-interest roll logic.
- Нет back-adjusted continuous futures.
- Нет live data stream.
- Нет broker execution.
- PaperBroker slippage model остаётся MVP.
- Нет точной PnL attribution by session/contract/regime.

## Next Step

Следующий цикл должен добавить official/sourced MOEX calendar ingestion, special trading days, liquidity-aware
roll rules, back-adjusted continuous futures и richer session/contract research reports.
