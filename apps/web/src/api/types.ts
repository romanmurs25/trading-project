export type DecimalString = string;
export type IsoDate = string;
export type IsoDateTime = string;

export interface HealthResponse {
  status: string;
  live_trading_enabled: boolean;
  trading_mode: string;
}

export interface Instrument {
  id: string;
  venue: string;
  asset_class: string;
  native_symbol: string;
  canonical_symbol: string;
  name: string;
  lot_size: DecimalString;
  tick_size: DecimalString;
  tick_value: DecimalString;
  currency: string;
  expiry_date?: IsoDate | null;
  is_active: boolean;
  metadata: Record<string, unknown>;
}

export interface ContractSpec {
  instrument_id: string;
  lot_size: DecimalString;
  tick_size: DecimalString;
  tick_value: DecimalString;
  currency: string;
  expiry_date?: IsoDate | null;
  first_trade_date?: IsoDate | null;
  last_trade_date?: IsoDate | null;
  underlying_symbol?: string | null;
  metadata: Record<string, unknown>;
}

export interface InstrumentDetail {
  instrument: Instrument;
  contract_spec: ContractSpec | null;
}

export interface CandleQualityReport {
  candles_count: number;
  expected_candles_count?: number;
  missing_intervals_count?: number;
  duplicate_timestamps_count?: number;
  zero_volume_count?: number;
  warnings: string[];
}

export interface SessionAwareCandleQualityReport {
  candles_count: number;
  expected_candles_count: number;
  missing_intervals_count: number;
  duplicate_timestamps_count: number;
  out_of_session_count: number;
  zero_volume_count: number;
  warnings: string[];
}

export interface SessionAwareQualityResponse {
  canonical_symbol: string;
  instrument_id: string;
  quality_mode: "session_aware";
  report: SessionAwareCandleQualityReport;
}

export interface MarketSession {
  id: string;
  venue: string;
  market: string;
  session_type: string;
  session_date: IsoDate;
  timezone: string;
  start: IsoDateTime;
  end: IsoDateTime;
  is_trading: boolean;
  metadata: Record<string, unknown>;
}

export interface ResearchRun {
  id: string;
  strategy_id: string;
  canonical_symbol: string;
  instrument_id: string;
  interval: string;
  start: IsoDateTime;
  end: IsoDateTime;
  parameter_grid: Record<string, unknown>;
  data_quality_gate: Record<string, unknown>;
  status: string;
  created_at: IsoDateTime;
  completed_at?: IsoDateTime | null;
  notes?: string | null;
  metadata: Record<string, unknown>;
}

export interface ResearchBacktestResult {
  id: string;
  research_run_id: string;
  backtest_run_id?: string | null;
  strategy_id: string;
  canonical_symbol: string;
  instrument_id: string;
  interval: string;
  start: IsoDateTime;
  end: IsoDateTime;
  params: Record<string, unknown>;
  metrics: Record<string, DecimalString | number | null>;
  quality_report: Record<string, unknown>;
  status: string;
  error_message?: string | null;
  created_at: IsoDateTime;
}

export interface ResearchReport {
  research_run_id: string;
  summary?: Record<string, unknown>;
  best_results?: Record<string, unknown>;
  rows?: Record<string, unknown>[];
  markdown?: string;
  warnings?: string[];
  [key: string]: unknown;
}

export interface ResearchComparison {
  research_run_id: string;
  sort_by: string;
  rows: Array<{
    id: string;
    backtest_run_id?: string | null;
    status: string;
    params: Record<string, unknown>;
    metrics: Record<string, DecimalString | number | null>;
    error_message?: string | null;
  }>;
  best_row?: Record<string, unknown> | null;
  warnings: string[];
}

export interface BacktestEquityPoint {
  id: string;
  backtest_run_id: string;
  ts: IsoDateTime;
  equity: DecimalString;
  drawdown: DecimalString;
}

export interface ResearchEquityResponse {
  research_run_id: string;
  points: BacktestEquityPoint[];
}

export interface BacktestTradeRecord {
  id: string;
  backtest_run_id: string;
  instrument_id: string;
  side: string;
  entry_ts?: IsoDateTime | null;
  exit_ts?: IsoDateTime | null;
  entry_price?: DecimalString | null;
  exit_price?: DecimalString | null;
  qty: DecimalString;
  gross_pnl: DecimalString;
  net_pnl: DecimalString;
  r_multiple?: DecimalString | null;
  reason?: string | null;
  metadata: Record<string, unknown>;
}

export interface ResearchTradesResponse {
  research_run_id: string;
  trades: BacktestTradeRecord[];
}

export interface ContinuousSeries {
  id: string;
  venue: string;
  underlying_symbol: string;
  canonical_symbol: string;
  interval: string;
  roll_rule: Record<string, unknown>;
  adjustment_method: string;
  start: IsoDateTime;
  end: IsoDateTime;
  created_at: IsoDateTime;
  metadata: Record<string, unknown>;
}

export interface ContinuousSeriesComponent {
  id: string;
  continuous_series_id: string;
  instrument_id: string;
  canonical_symbol: string;
  start: IsoDateTime;
  end: IsoDateTime;
  roll_date?: IsoDate | null;
  metadata: Record<string, unknown>;
}

export interface ContinuousSeriesComponentsResponse {
  continuous_series_id: string;
  components: ContinuousSeriesComponent[];
}

export interface RollEvent {
  id: string;
  venue: string;
  underlying_symbol: string;
  from_instrument_id: string;
  to_instrument_id: string;
  roll_date: IsoDate;
  reason: string;
  metadata: Record<string, unknown>;
}

export interface FuturesChainResponse {
  underlying_symbol: string;
  contracts: Instrument[];
}

export interface FrontContractResponse {
  as_of: IsoDateTime;
  selected_instrument_id: string;
  selected_canonical_symbol: string;
  reason: string;
  days_to_expiry: number;
  metadata: Record<string, unknown>;
}
