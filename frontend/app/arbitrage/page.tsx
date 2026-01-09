'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import ArbitrageCard from '@/components/ArbitrageCard'
import LoadingSpinner from '@/components/LoadingSpinner'

export default function ArbitragePage() {
  const [minMargin, setMinMargin] = useState(10.0)
  const [minPriceDiff, setMinPriceDiff] = useState(5.0)

  const { data, isLoading, error } = useQuery({
    queryKey: ['arbitrage', minMargin, minPriceDiff],
    queryFn: () => api.getArbitrageOpportunities(minMargin, minPriceDiff, 50),
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-5xl font-black text-primary-900 mb-10 uppercase tracking-wide font-display drop-shadow-sm">Arbitrage Opportunities</h1>

      {/* Filters */}
      <div className="genx-card p-8 mb-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-black text-primary-900 mb-3 uppercase tracking-wide">
              Minimum Profit Margin (%)
            </label>
            <input
              type="number"
              value={minMargin}
              onChange={(e) => setMinMargin(parseFloat(e.target.value) || 0)}
              min="0"
              step="0.1"
              className="w-full px-4 py-3 border-3 border-primary-900 bg-white/95 backdrop-blur-sm text-primary-900 font-bold focus:outline-none focus:ring-4 focus:ring-primary-400 shadow-genx"
            />
          </div>
          <div>
            <label className="block text-sm font-black text-primary-900 mb-3 uppercase tracking-wide">
              Minimum Price Difference ($)
            </label>
            <input
              type="number"
              value={minPriceDiff}
              onChange={(e) => setMinPriceDiff(parseFloat(e.target.value) || 0)}
              min="0"
              step="0.1"
              className="w-full px-4 py-3 border-3 border-primary-900 bg-white/95 backdrop-blur-sm text-primary-900 font-bold focus:outline-none focus:ring-4 focus:ring-primary-400 shadow-genx"
            />
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-600">Error loading arbitrage opportunities. Please try again.</p>
        </div>
      ) : data && data.data.length > 0 ? (
        <>
          <div className="mb-4">
            <p className="text-gray-600">
              Found {data.meta.count} opportunity{data.meta.count !== 1 ? 'ies' : 'y'}
            </p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {data.data.map((opportunity) => (
              <ArbitrageCard key={opportunity.product_id} opportunity={opportunity} />
            ))}
          </div>
        </>
      ) : (
        <div className="text-center py-12">
          <p className="text-gray-500">
            No arbitrage opportunities found. Try adjusting the filters.
          </p>
        </div>
      )}
    </div>
  )
}

