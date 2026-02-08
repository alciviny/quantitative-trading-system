import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { ScannerPage } from './pages/ScannerPage'
import { LayoutDashboard, Search, TrendingUp, Activity, Settings } from 'lucide-react'
import { cn } from './lib/utils'

function App() {
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Scanner', href: '/scanner', icon: Search },
    { name: 'Backtest', href: '/backtest', icon: TrendingUp },
    { name: 'Saúde do Sistema', href: '/health', icon: Activity },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 h-16 px-6 border-b border-border">
            <div className="w-8 h-8 bg-gradient-to-br from-bull to-primary rounded-lg flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg">Co-Piloto Quant</h1>
              <p className="text-xs text-muted-foreground">Trading Cockpit</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-border">
            <button className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <Settings className="h-5 w-5" />
              Configurações
            </button>
            <div className="mt-4 text-xs text-muted-foreground text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <div className="w-2 h-2 bg-bull rounded-full animate-pulse-glow"></div>
                <span>Sistema Online</span>
              </div>
              <div>v1.0.0 - 2026</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="pl-64">
        {/* Header */}
        <header className="sticky top-0 z-40 h-16 bg-card/95 backdrop-blur border-b border-border">
          <div className="flex items-center justify-between h-full px-8">
            <div>
              <h2 className="text-xl font-bold">
                {navigation.find(n => n.href === location.pathname)?.name || 'Co-Piloto Quant'}
              </h2>
              <p className="text-sm text-muted-foreground">
                {new Date().toLocaleDateString('pt-BR', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-sm font-mono font-semibold">IBOV</div>
                <div className="text-xs text-bull">+1.24%</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono font-semibold">USDBRL</div>
                <div className="text-xs text-bear">-0.56%</div>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/scanner" element={<ScannerPage />} />
            <Route
              path="/backtest"
              element={
                <div className="text-center py-20 text-muted-foreground">
                  Em desenvolvimento...
                </div>
              }
            />
            <Route
              path="/health"
              element={
                <div className="text-center py-20 text-muted-foreground">
                  Em desenvolvimento...
                </div>
              }
            />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default App
