import type {
  ContinuousSeries,
  FrontContractResponse,
  FuturesChainResponse,
  HealthResponse,
  Instrument,
  LiveCandlesResponse,
  MarketDataEventsResponse,
  MarketDataState,
  MoexPollOnceResponse,
  ResearchBacktestResult,
  ResearchComparison,
  ResearchEquityResponse,
  ResearchRun,
  ResearchTradesResponse,
  SessionAwareQualityResponse,
} from "../api/types";

export const health: HealthResponse = {
  status: "ok",
  live_trading_enabled: false,
  trading_mode: "RESEARCH",
};

export const instrument: Instrument = {
  id: "moex:SiH6",
  venue: "MOEX",
  asset_class: "FUTURES",
  native_symbol: "SiH6",
  canonical_symbol: "MOEX:SiH6",
  name: "SiH6",
  lot_size: "1",
  tick_size: "1",
  tick_value: "1",
  currency: "RUB",
  expiry_date: "2026-03-19",
  is_active: true,
  metadata: {},
};

export const researchRun: ResearchRun = {
  id: "research-1",
  strategy_id: "opening_range_breakout",
  canonical_symbol: "MOEX:SiH6",
  instrument_id: "moex:SiH6",
  interval: "1m",
  start: "2026-01-01T00:00:00Z",
  end: "2026-01-02T00:00:00Z",
  parameter_grid: { opening_range_minutes: [5] },
  data_quality_gate: {},
  status: "COMPLETED",
  created_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T01:00:00Z",
  metadata: {},
};

export const researchResult: ResearchBacktestResult = {
  id: "result-1",
  research_run_id: "research-1",
  backtest_run_id: "bt-1",
  strategy_id: "opening_range_breakout",
  canonical_symbol: "MOEX:SiH6",
  instrument_id: "moex:SiH6",
  interval: "1m",
  start: "2026-01-01T00:00:00Z",
  end: "2026-01-02T00:00:00Z",
  params: { opening_range_minutes: 5 },
  metrics: {
    profit_factor: "1.5",
    expectancy: "10",
    total_pnl: "100",
    max_drawdown: "0.01",
    trades_count: "3",
  },
  quality_report: { warnings: [] },
  status: "COMPLETED",
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
};

export const researchComparison: ResearchComparison = {
  research_run_id: "research-1",
  sort_by: "profit_factor",
  rows: [
    {
      id: "result-1",
      backtest_run_id: "bt-1",
      status: "COMPLETED",
      params: { opening_range_minutes: 5 },
      metrics: researchResult.metrics,
      error_message: null,
    },
  ],
  best_row: {
    metrics: researchResult.metrics,
  },
  warnings: [],
};

export const researchEquity: ResearchEquityResponse = {
  research_run_id: "research-1",
  points: [
    {
      id: "eq-1",
      backtest_run_id: "bt-1",
      ts: "2026-01-01T00:00:00Z",
      equity: "100000",
      drawdown: "0",
    },
  ],
};

export const researchTrades: ResearchTradesResponse = {
  research_run_id: "research-1",
  trades: [
    {
      id: "trade-1",
      backtest_run_id: "bt-1",
      instrument_id: "moex:SiH6",
      side: "BUY",
      entry_ts: "2026-01-01T00:00:00Z",
      exit_ts: "2026-01-01T01:00:00Z",
      entry_price: "100",
      exit_price: "110",
      qty: "1",
      gross_pnl: "10",
      net_pnl: "9",
      r_multiple: "1.2",
      reason: "paper closed trade",
      metadata: {},
    },
  ],
};

export const dataQualityReport: SessionAwareQualityResponse = {
  canonical_symbol: "MOEX:SiH6",
  instrument_id: "moex:SiH6",
  quality_mode: "session_aware",
  report: {
    candles_count: 10,
    start: "2026-01-01T07:00:00Z",
    end: "2026-01-01T18:45:00Z",
    expected_candles_count: 12,
    missing_expected_candles_count: 2,
    unexpected_out_of_session_count: 0,
    duplicates_count: 0,
    non_monotonic_count: 0,
    zero_volume_count: 1,
    session_counts: { MAIN: 10 },
    warnings: ["missing expected session candles: 2"],
  },
};

export const futuresChain: FuturesChainResponse = {
  underlying_symbol: "Si",
  contracts: [instrument],
};

export const frontContract: FrontContractResponse = {
  as_of: "2026-03-16T00:00:00Z",
  selected_instrument_id: "moex:SiH6",
  selected_canonical_symbol: "MOEX:SiH6",
  reason: "front contract",
  days_to_expiry: 3,
  metadata: {},
};

export const continuousSeries: ContinuousSeries = {
  id: "series-1",
  venue: "MOEX",
  underlying_symbol: "Si",
  canonical_symbol: "MOEX:Si:CONT:1m",
  interval: "1m",
  roll_rule: { roll_days_before_expiry: 5 },
  adjustment_method: "none",
  start: "2026-01-01T00:00:00Z",
  end: "2026-01-02T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  metadata: {},
};

export const liveDataState: MarketDataState = {
  status: "IDLE",
  sources: ["DEMO_REPLAY"],
  active_runs: [],
  latest_event_at: "2026-01-01T10:00:00Z",
  latest_candles_count: 1,
  stale_candles_count: 0,
  warnings: [],
};

export const liveCandles: LiveCandlesResponse = {
  candles: [
    {
      id: "live-candle-1",
      source: "DEMO_REPLAY",
      venue: "MOEX",
      instrument_id: "moex:SiH6",
      canonical_symbol: "MOEX:SiH6",
      interval: "1m",
      ts_start: "2026-01-01T10:00:00Z",
      ts_end: "2026-01-01T10:01:00Z",
      open: "100",
      high: "101",
      low: "99",
      close: "100.5",
      volume: "10",
      value: "1005",
      trades_count: 5,
      updated_at: "2026-01-01T10:00:01Z",
      is_closed: true,
      freshness: "FRESH",
      metadata: {},
    },
  ],
};

export const liveEvents: MarketDataEventsResponse = {
  events: [
    {
      id: "live-event-1",
      source: "DEMO_REPLAY",
      event_type: "CANDLE_CLOSED",
      venue: "MOEX",
      instrument_id: "moex:SiH6",
      canonical_symbol: "MOEX:SiH6",
      interval: "1m",
      ts: "2026-01-01T10:00:00Z",
      received_at: "2026-01-01T10:00:01Z",
      payload: {},
      metadata: {},
    },
  ],
};

export const moexPollSkipped: MoexPollOnceResponse = {
  status: "skipped",
  source: "MOEX_ISS_POLLING",
  canonical_symbol: "MOEX:SiH6",
  interval: "1m",
  lookback_minutes: 5,
  dry_run: true,
  allow_network: false,
  candles_loaded: 0,
  candles_saved: 0,
  warnings: ["external network is disabled by default; pass allow_network=true explicitly"],
};
