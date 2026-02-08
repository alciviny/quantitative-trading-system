import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCorrelationMatrix } from '@/hooks/useQueries'

export const CorrelationHeatmap = () => {
  const { data, isLoading } = useCorrelationMatrix()

  if (isLoading || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Matriz de Correlação</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse h-64 bg-muted rounded"></div>
        </CardContent>
      </Card>
    )
  }

  const { tickers, matrix } = data
  const cellSize = Math.min(50, Math.floor(600 / tickers.length))

  const getColor = (value: number) => {
    if (value > 0.7) return 'bg-bull text-bull-foreground'
    if (value > 0.4) return 'bg-bull/60 text-foreground'
    if (value > 0) return 'bg-bull/20 text-foreground'
    if (value > -0.4) return 'bg-bear/20 text-foreground'
    if (value > -0.7) return 'bg-bear/60 text-foreground'
    return 'bg-bear text-bear-foreground'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Matriz de Correlação entre Ativos</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto custom-scrollbar">
          <div className="inline-block min-w-full">
            <div className="flex">
              <div style={{ width: cellSize }} className="flex-shrink-0" />
              {tickers.map((ticker) => (
                <div
                  key={ticker}
                  style={{ width: cellSize, height: cellSize }}
                  className="flex items-center justify-center text-xs font-mono text-muted-foreground"
                >
                  <div className="transform -rotate-45 origin-center">
                    {ticker}
                  </div>
                </div>
              ))}
            </div>
            {matrix.map((row, i) => (
              <div key={i} className="flex">
                <div
                  style={{ width: cellSize, height: cellSize }}
                  className="flex items-center justify-center text-xs font-mono font-medium text-muted-foreground"
                >
                  {tickers[i]}
                </div>
                {row.map((value, j) => (
                  <div
                    key={j}
                    style={{ width: cellSize, height: cellSize }}
                    className={`flex items-center justify-center text-xs font-mono font-semibold border border-border/30 ${getColor(value)} transition-colors cursor-pointer hover:opacity-80`}
                    title={`${tickers[i]} vs ${tickers[j]}: ${value.toFixed(2)}`}
                  >
                    {value.toFixed(2)}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-center gap-6 mt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-bull rounded"></div>
            <span>Correlação Positiva (+1)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-neutral/30 rounded"></div>
            <span>Sem Correlação (0)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-bear rounded"></div>
            <span>Correlação Negativa (-1)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
