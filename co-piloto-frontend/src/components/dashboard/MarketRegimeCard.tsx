import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useMarketRegime } from '@/hooks/useQueries'
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react'
import type { MarketRegime } from '@/types/trading'

const REGIME_CONFIG = {
  BULL: {
    label: 'Bullish',
    icon: TrendingUp,
    color: 'text-bull',
    bgColor: 'bg-bull/20',
    borderColor: 'border-bull/50',
  },
  BEAR: {
    label: 'Bearish',
    icon: TrendingDown,
    color: 'text-bear',
    bgColor: 'bg-bear/20',
    borderColor: 'border-bear/50',
  },
  LATERAL: {
    label: 'Lateral',
    icon: Minus,
    color: 'text-neutral',
    bgColor: 'bg-neutral/20',
    borderColor: 'border-neutral/50',
  },
  VOLATILE: {
    label: 'Volátil',
    icon: AlertTriangle,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/50',
  },
}

export const MarketRegimeCard = () => {
  const { data: regime, isLoading } = useMarketRegime()

  if (isLoading || !regime) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Regime de Mercado</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            <div className="h-12 bg-muted rounded"></div>
            <div className="h-8 bg-muted rounded w-2/3"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const config = REGIME_CONFIG[regime.regime as MarketRegime]
  const Icon = config.icon

  return (
    <Card className={`border-2 ${config.borderColor}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className={`h-5 w-5 ${config.color}`} />
          Clima do Mercado
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className={`text-3xl font-bold ${config.color}`}>
              {config.label}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Confiança: {regime.confidence.toFixed(1)}%
            </div>
          </div>
          <div className={`w-24 h-24 rounded-full ${config.bgColor} flex items-center justify-center`}>
            <Icon className={`h-12 w-12 ${config.color}`} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Volatilidade</div>
            <div className="text-lg font-mono font-semibold">
              {regime.volatility.toFixed(1)}%
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Força da Tendência</div>
            <div className="text-lg font-mono font-semibold">
              {regime.trend_strength.toFixed(2)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Hurst Médio</div>
            <div className="text-lg font-mono font-semibold">
              {regime.hurst_avg.toFixed(3)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4 pt-4 border-t">
          <div className="text-xs text-muted-foreground">
            Atualizado: {new Date(regime.updated_at).toLocaleTimeString('pt-BR')}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
