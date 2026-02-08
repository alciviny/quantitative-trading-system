import axios from 'axios'
import type { 
  MarketRegimeData, 
  Asset, 
  BacktestResult,
  BandData,
  SystemHealth,
  CorrelationMatrix 
} from '@/types/trading'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Se a API real não estiver disponível, usar mocks
const USE_MOCKS = false // Trocar para false quando API real estiver rodando

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
}
