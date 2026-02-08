import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table'
import { useAssets } from '@/hooks/useQueries'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { Asset } from '@/types/trading'
import { formatPrice, formatPercent, formatLargeNumber } from '@/lib/utils'
import { ArrowUpDown, TrendingUp, TrendingDown, Search, Filter } from 'lucide-react'

export const AssetTable = () => {
  const { data: assets = [], isLoading } = useAssets()
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState('')

  const columns = useMemo<ColumnDef<Asset>[]>(
    () => [
      {
        accessorKey: 'ticker',
        header: 'Ticker',
        cell: ({ row }) => (
          <div className="font-mono font-bold text-sm">
            {row.original.ticker}
          </div>
        ),
      },
      {
        accessorKey: 'name',
        header: 'Nome',
        cell: ({ row }) => (
          <div className="text-xs text-muted-foreground max-w-[150px] truncate">
            {row.original.name}
          </div>
        ),
      },
      {
        accessorKey: 'price',
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 p-0 hover:bg-transparent"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Preço
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <div className="font-mono font-semibold">
            R$ {formatPrice(row.original.price)}
          </div>
        ),
      },
      {
        accessorKey: 'change_pct',
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 p-0 hover:bg-transparent"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Variação
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const value = row.original.change_pct
          return (
            <div
              className={`font-mono font-semibold flex items-center gap-1 ${
                value >= 0 ? 'text-bull' : 'text-bear'
              }`}
            >
              {value >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {formatPercent(value)}
            </div>
          )
        },
      },
      {
        accessorKey: 'volume',
        header: 'Volume',
        cell: ({ row }) => (
          <div className="font-mono text-xs text-muted-foreground">
            {formatLargeNumber(row.original.volume)}
          </div>
        ),
      },
      {
        accessorKey: 'hurst',
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 p-0 hover:bg-transparent"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Hurst
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const value = row.original.hurst
          const isTrending = value > 0.6
          const isMeanReverting = value < 0.4
          return (
            <div
              className={`font-mono text-sm font-semibold ${
                isTrending ? 'text-bull' : isMeanReverting ? 'text-bear' : 'text-neutral'
              }`}
            >
              {value.toFixed(3)}
            </div>
          )
        },
      },
      {
        accessorKey: 'fractal_dim',
        header: 'Fractal',
        cell: ({ row }) => (
          <div className="font-mono text-sm">
            {row.original.fractal_dim.toFixed(3)}
          </div>
        ),
      },
      {
        accessorKey: 'entropy',
        header: 'Entropia',
        cell: ({ row }) => (
          <div className="font-mono text-sm">
            {row.original.entropy.toFixed(2)}
          </div>
        ),
      },
      {
        accessorKey: 'rsi',
        header: 'RSI',
        cell: ({ row }) => {
          const value = row.original.rsi
          const isOverbought = value > 70
          const isOversold = value < 30
          return (
            <div
              className={`font-mono text-sm ${
                isOverbought ? 'text-bear' : isOversold ? 'text-bull' : 'text-muted-foreground'
              }`}
            >
              {value.toFixed(1)}
            </div>
          )
        },
      },
      {
        accessorKey: 'strategy_status',
        header: 'Status',
        cell: ({ row }) => {
          const status = row.original.strategy_status
          return (
            <Badge
              variant={
                status === 'BUY' ? 'bull' : status === 'SELL' ? 'bear' : 'neutral'
              }
            >
              {status}
            </Badge>
          )
        },
        filterFn: (row, id, value) => {
          return value.includes(row.getValue(id))
        },
      },
      {
        accessorKey: 'ml_probability',
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 p-0 hover:bg-transparent"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            ML Prob
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const value = row.original.ml_probability
          return (
            <div className="flex items-center gap-2">
              <div className="w-12 bg-muted rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-primary"
                  style={{ width: `${value}%` }}
                />
              </div>
              <span className="font-mono text-xs font-semibold">
                {value.toFixed(0)}%
              </span>
            </div>
          )
        },
      },
    ],
    []
  )

  const table = useReactTable({
    data: assets,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Scanner de Ativos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-10 bg-muted rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Scanner de Ativos ({assets.length} ativos)</CardTitle>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar ticker..."
                value={globalFilter ?? ''}
                onChange={(e) => setGlobalFilter(e.target.value)}
                className="pl-8 w-64"
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                table.getColumn('strategy_status')?.setFilterValue(['BUY'])
              }
            >
              <Filter className="mr-2 h-4 w-4" />
              Apenas BUY
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.resetColumnFilters()}
            >
              Limpar Filtros
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border custom-scrollbar overflow-auto max-h-[600px]">
          <table className="w-full table-dense">
            <thead className="bg-muted/50 sticky top-0">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="text-left p-2 font-medium">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b hover:bg-muted/30 transition-colors cursor-pointer"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="p-2">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
