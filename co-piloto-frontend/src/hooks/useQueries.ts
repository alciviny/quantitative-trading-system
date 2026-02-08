import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { apiService } from '@/services/api'
import type { 
  MarketRegimeData, 
  Asset, 
  BacktestResult,
  BandData,
  SystemHealth,
  CorrelationMatrix 
} from '@/types/trading'

export const useMarketRegime = (): UseQueryResult<MarketRegimeData> => {
  return useQuery({
    queryKey: ['marketRegime'],
    queryFn: () => apiService.getMarketRegime(),
    refetchInterval: 30000, // 30 seconds
  })
}

export const useAssets = (): UseQueryResult<Asset[]> => {
  return useQuery({
    queryKey: ['assets'],
    queryFn: () => apiService.getAssets(),
    refetchInterval: 15000, // 15 seconds
  })
}

export const useAssetOHLCV = (ticker: string, days = 365): UseQueryResult<BandData[]> => {
  return useQuery({
    queryKey: ['assetOHLCV', ticker, days],
    queryFn: () => apiService.getAssetOHLCV(ticker, days),
    enabled: !!ticker,
  })
}

export const useBacktestResult = (strategy_id?: string): UseQueryResult<BacktestResult> => {
  return useQuery({
    queryKey: ['backtestResult', strategy_id],
    queryFn: () => apiService.getBacktestResult(strategy_id),
  })
}

export const useSystemHealth = (): UseQueryResult<SystemHealth> => {
  return useQuery({
    queryKey: ['systemHealth'],
    queryFn: () => apiService.getSystemHealth(),
    refetchInterval: 5000, // 5 seconds
  })
}

export const useCorrelationMatrix = (): UseQueryResult<CorrelationMatrix> => {
  return useQuery({
    queryKey: ['correlationMatrix'],
    queryFn: () => apiService.getCorrelationMatrix(),
    refetchInterval: 60000, // 1 minute
  })
}
