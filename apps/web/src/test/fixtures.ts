import type {
  ContinuousSeries,
  FrontContractResponse,
  FuturesChainResponse,
  HealthResponse,
  Instrument,
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
    expected_candles_count: 12,
    missing_intervals_count: 2,
    duplicate_timestamps_count: 0,
    out_of_session_count: 0,
    zero_volume_count: 1,
    warnings: ["missing intervals"],
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
