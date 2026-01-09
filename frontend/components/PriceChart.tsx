'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { PriceHistoryPoint } from '@/lib/api'

interface PriceChartProps {
  data: PriceHistoryPoint[]
  title?: string
}

export default function PriceChart({ data, title }: PriceChartProps) {
  // Group data by date and site
  const chartData = data.reduce((acc, point) => {
    const existing = acc.find((d) => d.date === point.date)
    if (existing) {
      existing[point.site] = point.price
    } else {
      acc.push({
        date: point.date,
        [point.site]: point.price,
      })
    }
    return acc
  }, [] as any[])

  // Get unique sites for legend
  const sites = Array.from(new Set(data.map((d) => d.site)))

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No price history data available</p>
      </div>
    )
  }

  const colors = {
    amazon: '#FF9900',
    walmart: '#004C91',
    kohls: '#C41E3A',
    kmart: '#006B3C',
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis />
          <Tooltip
            formatter={(value: number) => `$${value.toFixed(2)}`}
            labelFormatter={formatDate}
          />
          <Legend />
          {sites.map((site) => (
            <Line
              key={site}
              type="monotone"
              dataKey={site}
              stroke={colors[site as keyof typeof colors] || '#8884d8'}
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

