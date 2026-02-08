import { MarketRegimeCard } from '@/components/dashboard/MarketRegimeCard'
import { CorrelationHeatmap } from '@/components/dashboard/CorrelationHeatmap'
import { AlertCards } from '@/components/dashboard/AlertCards'

export const DashboardPage = () => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <MarketRegimeCard />
        </div>
        <div className="lg:col-span-2">
          <CorrelationHeatmap />
        </div>
      </div>
      
      <AlertCards />
    </div>
  )
}
