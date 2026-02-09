import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { apiService } from '@/services/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Loader2, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react'

interface IndicatorData {
  date: string
  close: number
  hurst_exponent?: number
  market_entropy?: number
  fractal_dimension?: number
  volatility_20?: number
  sma_20?: number
  sma_50?: number
  regime_trend?: string
  regime_volatility?: string
  [key: string]: any
}

export function IndicatorsPage() {
  const [stocks, setStocks] = useState<string[]>([])
  const [selectedStock, setSelectedStock] = useState<string>('')
  const [days, setDays] = useState<number>(90)
  const [data, setData] = useState<IndicatorData[]>([])
  const [indicators, setIndicators] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiHealth, setApiHealth] = useState<any>(null)

  // Carrega lista de stocks e health check
  useEffect(() => {
    loadInitialData()
  }, [])

  // Carrega dados quando stock ou período muda
  useEffect(() => {
    if (selectedStock) {
      loadIndicators()
    }
  }, [selectedStock, days])

  const loadInitialData = async () => {
    try {
      const [stocksList, health] = await Promise.all([
        apiService.getStocks(),
        apiService.getAPIHealth()
      ])
      
      setStocks(stocksList)
      setApiHealth(health)
      
      if (stocksList.length > 0) {
        setSelectedStock(stocksList[0])
      }
    } catch (err) {
      setError('Erro ao conectar com a API. Certifique-se de que está rodando.')
      console.error(err)
    }
  }

  const loadIndicators = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const result = await apiService.getStockIndicators(selectedStock, days)
      setData(result.data)
      setIndicators(result.indicators)
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar indicadores')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const latest = data[data.length - 1] || {}

  const getRegimeBadge = (regime?: string) => {
    if (!regime) return <Badge variant="secondary">N/A</Badge>
    
    const colors: Record<string, string> = {
      'trending': 'bg-green-500',
      'mean_reverting': 'bg-blue-500',
      'random': 'bg-gray-500',
      'high_vol': 'bg-red-500',
      'normal_vol': 'bg-yellow-500',
      'low_vol': 'bg-green-500',
    }
    
    return (
      <Badge className={colors[regime] || 'bg-gray-500'}>
        {regime.replace('_', ' ').toUpperCase()}
      </Badge>
    )
  }

  const getTrendIcon = (hurst?: number) => {
    if (!hurst) return <Minus className="h-4 w-4" />
    if (hurst > 0.55) return <TrendingUp className="h-4 w-4 text-green-500" />
    if (hurst < 0.45) return <TrendingDown className="h-4 w-4 text-blue-500" />
    return <Minus className="h-4 w-4 text-gray-500" />
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card className="border-red-500">
          <CardHeader>
            <CardTitle className="text-red-500">❌ Erro</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
            <p className="text-sm text-gray-500 mt-2">
              Certifique-se de que a API está rodando em http://localhost:8001
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header com Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">🔬 Indicadores Complexos</h1>
          <p className="text-gray-500">Feature Store • Análise Quantitativa</p>
        </div>
        
        {apiHealth && (
          <div className="flex gap-2">
            <Badge variant="outline" className="bg-green-50">
              ✅ API v{apiHealth.version}
            </Badge>
            {apiHealth.feature_store?.enabled && (
              <Badge variant="outline" className="bg-blue-50">
                📁 {apiHealth.feature_store.enriched_files} arquivos
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Controles */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Ação</label>
              <Select value={selectedStock} onValueChange={setSelectedStock}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {stocks.map(stock => (
                    <SelectItem key={stock} value={stock}>
                      {stock}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="w-48">
              <label className="text-sm font-medium mb-2 block">Período</label>
              <Select value={days.toString()} onValueChange={(v: string) => setDays(Number(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 dias</SelectItem>
                  <SelectItem value="60">60 dias</SelectItem>
                  <SelectItem value="90">90 dias</SelectItem>
                  <SelectItem value="180">180 dias</SelectItem>
                  <SelectItem value="365">1 ano</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <Card>
          <CardContent className="py-12 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            <span className="ml-2">Carregando indicadores...</span>
          </CardContent>
        </Card>
      )}

      {!loading && data.length > 0 && (
        <>
          {/* Cards de Métricas */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Preço e Volatilidade */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">💰 Preço Atual</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">
                    R$ {latest.close?.toFixed(2)}
                  </span>
                  {latest.returns && (
                    <span className={latest.returns > 0 ? 'text-green-500' : 'text-red-500'}>
                      {(latest.returns * 100).toFixed(2)}%
                    </span>
                  )}
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Volatilidade 20d</span>
                    <span className="font-medium">
                      {((latest.volatility_20 || 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">ATR (14)</span>
                    <span className="font-medium">{latest.atr_14?.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">SMA 20</span>
                    <span className="font-medium">R$ {latest.sma_20?.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Regime de Mercado */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Regime de Mercado
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  {getTrendIcon(latest.hurst_exponent)}
                  {getRegimeBadge(latest.regime_trend)}
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Volatilidade</span>
                    {getRegimeBadge(latest.regime_volatility)}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Hurst Exponent</span>
                    <span className="font-mono font-medium">
                      {latest.hurst_exponent?.toFixed(3) || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Market Entropy</span>
                    <span className="font-mono font-medium">
                      {latest.market_entropy?.toFixed(3) || 'N/A'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Indicadores Disponíveis */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">📊 Indicadores</CardTitle>
                <CardDescription>
                  {indicators.length} indicadores calculados
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {['hurst_exponent', 'market_entropy', 'fractal_dimension', 'lempel_ziv', 'half_life', 'volatility_20']
                    .filter(ind => indicators.includes(ind))
                    .map(ind => {
                      const value = latest[ind]
                      return (
                        <div key={ind} className="bg-gray-50 p-2 rounded">
                          <div className="text-gray-500 uppercase text-[10px]">
                            {ind.replace(/_/g, ' ')}
                          </div>
                          <div className="font-mono font-bold">
                            {typeof value === 'number' ? value.toFixed(3) : 'N/A'}
                          </div>
                        </div>
                      )
                    })}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Gráfico de Preço */}
          <Card>
            <CardHeader>
              <CardTitle>📈 Evolução do Preço</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(date) => new Date(date).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                  />
                  <YAxis yAxisId="price" />
                  <Tooltip />
                  <Legend />
                  <Line yAxisId="price" type="monotone" dataKey="close" stroke="#667eea" name="Preço" strokeWidth={2} />
                  <Line yAxisId="price" type="monotone" dataKey="sma_20" stroke="#10b981" name="SMA 20" strokeWidth={1} strokeDasharray="5 5" />
                  <Line yAxisId="price" type="monotone" dataKey="sma_50" stroke="#f59e0b" name="SMA 50" strokeWidth={1} strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Gráfico de Indicadores Complexos */}
          <Card>
            <CardHeader>
              <CardTitle>🔬 Indicadores Complexos</CardTitle>
              <CardDescription>
                Hurst Exponent, Market Entropy, Fractal Dimension
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(date) => new Date(date).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                  />
                  <YAxis yAxisId="hurst" domain={[0, 1]} />
                  <YAxis yAxisId="entropy" orientation="right" domain={[0, 5]} />
                  <Tooltip />
                  <Legend />
                  <ReferenceLine yAxisId="hurst" y={0.5} stroke="#666" strokeDasharray="3 3" label="Random Walk" />
                  <Line yAxisId="hurst" type="monotone" dataKey="hurst_exponent" stroke="#667eea" name="Hurst" strokeWidth={2} />
                  <Line yAxisId="entropy" type="monotone" dataKey="market_entropy" stroke="#ef4444" name="Entropy" strokeWidth={2} />
                  <Line yAxisId="hurst" type="monotone" dataKey="fractal_dimension" stroke="#10b981" name="Fractal" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
              
              <div className="mt-4 p-4 bg-gray-50 rounded text-sm space-y-1">
                <div className="font-medium mb-2">📖 Interpretação:</div>
                <div>• Hurst &gt; 0.55: Mercado em <strong>tendência</strong> (persistente)</div>
                <div>• Hurst &lt; 0.45: Mercado com <strong>reversão à média</strong></div>
                <div>• Entropy &lt; 2.0: Mercado <strong>eficiente</strong> (ordenado)</div>
                <div>• Entropy &gt; 3.0: Mercado <strong>caótico</strong> (ruído)</div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
