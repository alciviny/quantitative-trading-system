import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAssets } from '@/hooks/useQueries'
import { TrendingUp, AlertCircle, Activity } from 'lucide-react'

export const AlertCards = () => {
  const { data: assets = [] } = useAssets()

  const buySignals = assets.filter(a => a.strategy_status === 'BUY').slice(0, 5)
  const volatileAssets = assets
    .sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct))
    .slice(0, 5)
  const strongTrends = assets.filter(a => a.hurst > 0.6).slice(0, 5)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Buy Signals */}
      <Card className="border-l-4 border-l-bull">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-bull" />
            Ativos em Zona de Compra
          </CardTitle>
        </CardHeader>
        <CardContent>
          {buySignals.length === 0 ? (
            <div className="text-sm text-muted-foreground">Nenhum sinal no momento</div>
          ) : (
            <div className="space-y-2">
              {buySignals.map((asset) => (
                <div key={asset.ticker} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="bull" className="font-mono text-xs">
                      {asset.ticker}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{asset.name}</span>
                  </div>
                  <div className="text-xs font-mono font-semibold text-bull">
                    +{asset.ml_probability.toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Volatile Assets */}
      <Card className="border-l-4 border-l-yellow-500">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4 text-yellow-500" />
            Volatilidade Explosiva
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {volatileAssets.map((asset) => (
              <div key={asset.ticker} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">
                    {asset.ticker}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{asset.name}</span>
                </div>
                <div
                  className={`text-xs font-mono font-semibold ${
                    asset.change_pct >= 0 ? 'text-bull' : 'text-bear'
                  }`}
                >
                  {asset.change_pct >= 0 ? '+' : ''}
                  {asset.change_pct.toFixed(2)}%
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Strong Trends */}
      <Card className="border-l-4 border-l-primary">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-primary" />
            Tendências Fortes (Hurst &gt; 0.6)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {strongTrends.length === 0 ? (
            <div className="text-sm text-muted-foreground">Nenhuma tendência forte</div>
          ) : (
            <div className="space-y-2">
              {strongTrends.map((asset) => (
                <div key={asset.ticker} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="font-mono text-xs">
                      {asset.ticker}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{asset.name}</span>
                  </div>
                  <div className="text-xs font-mono font-semibold text-primary">
                    H: {asset.hurst.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
