import axios from 'axios'
import type { 
  MarketRegimeData, 
  Asset, 
  BacktestResult,
  BandData,
  SystemHealth,
  CorrelationMatrix,
  OHLCVData
} from '@/types/trading'

const api = axios.create({
  baseURL: 'http://localhost:8001/api', // ✅ Aponta para a API real
  timeout: 10000,
})

// Se a API real não estiver disponível, usar mocks
const USE_MOCKS = false // ✅ Desabilitado - usando API real com Feature Store

export const apiService = {
  // Market Regime
  getMarketRegime: async (): Promise<MarketRegimeData> => {
    if (USE_MOCKS) {
      const { mockMarketRegime } = await import('./mockData')
      return mockMarketRegime()
    }
    const { data } = await api.get<MarketRegimeData>('/market/regime')
    return data
  },

  // Scanner/Screener
  getAssets: async (): Promise<Asset[]> => {
    if (USE_MOCKS) {
      const { mockAssets } = await import('./mockData')
      return mockAssets()
    }
    const { data } = await api.get<Asset[]>('/assets')
    return data
  },

  // Asset Detail
  getAssetOHLCV: async (ticker: string, days = 365): Promise<BandData[]> => {
    if (USE_MOCKS) {
      const { mockOHLCVData } = await import('./mockData')
      return mockOHLCVData(days)
    }
    const { data } = await api.get<BandData[]>(`/assets/${ticker}/ohlcv`, {
      params: { days }
    })
    return data
  },

  // Backtest
  getBacktestResult: async (strategy_id?: string): Promise<BacktestResult> => {
    if (USE_MOCKS) {
      const { mockBacktestResult } = await import('./mockData')
      return mockBacktestResult()
    }
    const { data } = await api.get<BacktestResult>('/backtest/results', {
      params: { strategy_id }
    })
    return data
  },

  // System Health
  getSystemHealth: async (): Promise<SystemHealth> => {
    if (USE_MOCKS) {
      const { mockSystemHealth } = await import('./mockData')
      return mockSystemHealth()
    }
    const { data } = await api.get<SystemHealth>('/system/health')
    return data
  },

  // Correlation
  getCorrelationMatrix: async (): Promise<CorrelationMatrix> => {
    if (USE_MOCKS) {
      const { mockCorrelationMatrix } = await import('./mockData')
      return mockCorrelationMatrix()
    }
    const { data } = await api.get<CorrelationMatrix>('/market/correlation')
    return data
  },

  // ✨ NOVOS ENDPOINTS - FEATURE STORE
  
  // Lista de stocks disponíveis
  getStocks: async (): Promise<string[]> => {
    const { data } = await api.get<string[]>('/stocks')
    return data
  },

  // Histórico de preços
  getPriceHistory: async (ticker: string, days = 365): Promise<OHLCVData[]> => {
    const { data } = await api.get<OHLCVData[]>(`/stocks/${ticker}/price-history`, {
      params: { days }
    })
    return data
  },

  // 🔥 INDICADORES COMPLETOS (Feature Store)
  getStockIndicators: async (ticker: string, days = 90): Promise<{
    data: Array<{
      date: string
      close: number
      returns?: number
      log_returns?: number
      volatility_20?: number
      volatility_60?: number
      volume_ma_20?: number
      volume_ratio?: number
      true_range?: number
      atr_14?: number
      roc_10?: number
      roc_20?: number
      sma_20?: number
      sma_50?: number
      sma_200?: number
      dist_sma_20?: number
      dist_sma_50?: number
      hurst_exponent?: number
      market_entropy?: number
      fractal_dimension?: number
      lempel_ziv?: number
      half_life?: number
      mean_reversion_speed?: number
      frac_diff?: number
      regime_trend?: string
      regime_volatility?: string
      regime_efficiency?: string
      [key: string]: any
    }>
    indicators: string[]
    count: number
  }> => {
    const { data } = await api.get(`/stocks/${ticker}/indicators`, {
      params: { days }
    })
    return data
  },

  // Health Check da API
  getAPIHealth: async (): Promise<{
    status: string
    version: string
    feature_store: {
      enabled: boolean
      path: string
      enriched_files: number
    }
    data_sources: Record<string, string>
  }> => {
    const { data } = await api.get('/health')
    return data
  },
}
