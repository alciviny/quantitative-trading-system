import type { 
  MarketRegimeData, 
  Asset, 
  BacktestResult, 
  BandData,
  SystemHealth,
  CorrelationMatrix 
} from '@/types/trading'

// Mock Data Generator
const TICKERS = [
  { ticker: 'PETR4', name: 'Petrobras PN' },
  { ticker: 'VALE3', name: 'Vale ON' },
  { ticker: 'ITUB4', name: 'Itaú Unibanco PN' },
  { ticker: 'BBDC4', name: 'Bradesco PN' },
  { ticker: 'ABEV3', name: 'Ambev ON' },
  { ticker: 'WEGE3', name: 'WEG ON' },
  { ticker: 'B3SA3', name: 'B3 ON' },
  { ticker: 'RENT3', name: 'Localiza ON' },
  { ticker: 'MGLU3', name: 'Magazine Luiza ON' },
  { ticker: 'LREN3', name: 'Lojas Renner ON' },
  { ticker: 'RADL3', name: 'Raia Drogasil ON' },
  { ticker: 'GGBR4', name: 'Gerdau PN' },
  { ticker: 'CSNA3', name: 'CSN ON' },
  { ticker: 'SUZB3', name: 'Suzano ON' },
  { ticker: 'ELET3', name: 'Eletrobras ON' },
  { ticker: 'EMBR3', name: 'Embraer ON' },
  { ticker: 'HAPV3', name: 'Hapvida ON' },
  { ticker: 'PRIO3', name: 'PRIO ON' },
  { ticker: 'VIVT3', name: 'Vivo ON' },
  { ticker: 'JBSS3', name: 'JBS ON' },
]

const randomBetween = (min: number, max: number) => Math.random() * (max - min) + min

export const mockMarketRegime = (): MarketRegimeData => ({
  regime: ['BULL', 'BEAR', 'LATERAL', 'VOLATILE'][Math.floor(Math.random() * 4)] as any,
  confidence: randomBetween(60, 95),
  volatility: randomBetween(15, 45),
  trend_strength: randomBetween(0.3, 0.9),
  hurst_avg: randomBetween(0.45, 0.65),
  updated_at: new Date().toISOString(),
})

export const mockAssets = (): Asset[] => {
  return TICKERS.map(({ ticker, name }) => ({
    ticker,
    name,
    price: randomBetween(10, 100),
    change_pct: randomBetween(-5, 5),
    volume: randomBetween(1_000_000, 50_000_000),
    hurst: randomBetween(0.35, 0.75),
    fractal_dim: randomBetween(1.3, 1.7),
    entropy: randomBetween(0.5, 2.5),
    half_life: randomBetween(5, 40),
    rsi: randomBetween(20, 80),
    strategy_status: ['BUY', 'SELL', 'NEUTRAL'][Math.floor(Math.random() * 3)] as any,
    regime: ['BULL', 'BEAR', 'LATERAL', 'VOLATILE'][Math.floor(Math.random() * 4)] as any,
    ml_probability: randomBetween(40, 90),
    last_signal: new Date(Date.now() - randomBetween(0, 24 * 60 * 60 * 1000)).toISOString(),
  }))
}

export const mockOHLCVData = (days = 365): BandData[] => {
  const data: BandData[] = []
  let price = 100
  
  for (let i = 0; i < days; i++) {
    const change = randomBetween(-3, 3)
    price = Math.max(price + change, 50)
    
    const open = price
    const high = price + randomBetween(0, 4)
    const low = price - randomBetween(0, 4)
    const close = randomBetween(low, high)
    const volume = randomBetween(1_000_000, 10_000_000)
    
    const vwap = (high + low + close) / 3
    const atr = Math.abs(high - low)
    
    data.push({
      date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      open,
      high,
      low,
      close,
      volume,
      kalman_mean: close,
      kalman_upper: close + atr * 2,
      kalman_lower: close - atr * 2,
      vwap,
      vwap_upper: vwap + atr * 1.5,
      vwap_lower: vwap - atr * 1.5,
    })
    
    price = close
  }
  
  return data
}

export const mockBacktestResult = (): BacktestResult => {
  const days = 365
  const equity_curve = []
  let equity = 100000
  let benchmark = 100000
  
  for (let i = 0; i < days; i++) {
    const date = new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    const return_pct = randomBetween(-2, 3)
    const benchmark_return = randomBetween(-1.5, 2)
    
    equity *= (1 + return_pct / 100)
    benchmark *= (1 + benchmark_return / 100)
    
    const drawdown = Math.min(0, (equity - Math.max(...equity_curve.map(e => e.equity || equity))) / Math.max(...equity_curve.map(e => e.equity || equity)) * 100)
    
    equity_curve.push({
      date,
      equity,
      benchmark,
      drawdown,
    })
  }
  
  const trades = Array.from({ length: 50 }, () => ({
    entry_date: new Date(Date.now() - randomBetween(1, 365) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    exit_date: new Date(Date.now() - randomBetween(0, 365) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    ticker: TICKERS[Math.floor(Math.random() * TICKERS.length)].ticker,
    direction: Math.random() > 0.5 ? 'LONG' : 'SHORT' as any,
    entry_price: randomBetween(20, 80),
    exit_price: randomBetween(20, 80),
    pnl: randomBetween(-2000, 5000),
    pnl_pct: randomBetween(-5, 10),
    duration_bars: Math.floor(randomBetween(1, 30)),
  }))
  
  return {
    metrics: {
      sharpe_ratio: randomBetween(0.8, 2.5),
      sortino_ratio: randomBetween(1, 3),
      max_drawdown: randomBetween(-25, -5),
      win_rate: randomBetween(45, 70),
      profit_factor: randomBetween(1.2, 2.8),
      total_return: randomBetween(15, 80),
      annual_return: randomBetween(12, 45),
      total_trades: trades.length,
      avg_trade_duration: randomBetween(3, 15),
    },
    equity_curve,
    trades,
  }
}

export const mockSystemHealth = (): SystemHealth => ({
  mt5_connected: Math.random() > 0.1,
  api_latency_ms: randomBetween(10, 100),
  memory_usage_mb: randomBetween(500, 2000),
  cpu_usage_pct: randomBetween(10, 60),
  last_order_time: Math.random() > 0.3 ? new Date(Date.now() - randomBetween(0, 3600000)).toISOString() : null,
  orders_pending: Math.floor(randomBetween(0, 5)),
  orders_executed_today: Math.floor(randomBetween(5, 50)),
})

export const mockCorrelationMatrix = (): CorrelationMatrix => {
  const tickers = TICKERS.slice(0, 10).map(t => t.ticker)
  const size = tickers.length
  const matrix = Array.from({ length: size }, (_, i) =>
    Array.from({ length: size }, (_, j) =>
      i === j ? 1 : randomBetween(-0.8, 0.8)
    )
  )
  
  return { tickers, matrix }
}
