// Market Regime Types
export type MarketRegime = 'BULL' | 'BEAR' | 'LATERAL' | 'VOLATILE'

export interface MarketRegimeData {
  regime: MarketRegime
  confidence: number // 0-100
  volatility: number
  trend_strength: number
  hurst_avg: number
  updated_at: string
}

// Asset/Ticker Types
export interface Asset {
  ticker: string
  name: string
  price: number
  change_pct: number
  volume: number
  hurst: number
  fractal_dim: number
  entropy: number
  half_life: number
  rsi: number
  strategy_status: 'BUY' | 'SELL' | 'NEUTRAL'
  regime: MarketRegime
  ml_probability: number // 0-100
  last_signal: string
}

// OHLCV Data
export interface OHLCVData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// Kalman/VWAP Bands
export interface BandData extends OHLCVData {
  kalman_upper?: number
  kalman_lower?: number
  kalman_mean?: number
  vwap?: number
  vwap_upper?: number
  vwap_lower?: number
}

// Backtest Results
export interface BacktestMetrics {
  sharpe_ratio: number
  sortino_ratio: number
  max_drawdown: number
  win_rate: number
  profit_factor: number
  total_return: number
  annual_return: number
  total_trades: number
  avg_trade_duration: number
}

export interface EquityPoint {
  date: string
  equity: number
  drawdown: number
  benchmark: number
}

export interface BacktestResult {
  metrics: BacktestMetrics
  equity_curve: EquityPoint[]
  trades: Trade[]
}

export interface Trade {
  entry_date: string
  exit_date: string
  ticker: string
  direction: 'LONG' | 'SHORT'
  entry_price: number
  exit_price: number
  pnl: number
  pnl_pct: number
  duration_bars: number
}

// System Health
export interface SystemHealth {
  mt5_connected: boolean
  api_latency_ms: number
  memory_usage_mb: number
  cpu_usage_pct: number
  last_order_time: string | null
  orders_pending: number
  orders_executed_today: number
}

// Correlation Matrix
export interface CorrelationMatrix {
  tickers: string[]
  matrix: number[][] // correlação entre -1 e 1
}
