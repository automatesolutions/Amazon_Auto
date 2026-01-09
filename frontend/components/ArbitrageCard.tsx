'use client'

import Link from 'next/link'
import { ArbitrageOpportunity } from '@/lib/api'

interface ArbitrageCardProps {
  opportunity: ArbitrageOpportunity
}

export default function ArbitrageCard({ opportunity }: ArbitrageCardProps) {
  const formatPrice = (price: number) => `$${price.toFixed(2)}`
  const profitAmount = opportunity.price_diff
  const profitMargin = opportunity.profit_margin_pct

  const getProfitColor = (margin: number) => {
    if (margin >= 30) return 'text-green-600 bg-green-100'
    if (margin >= 20) return 'text-blue-600 bg-blue-100'
    if (margin >= 10) return 'text-yellow-600 bg-yellow-100'
    return 'text-gray-600 bg-gray-100'
  }

  return (
    <div className="genx-card p-8 transition-all">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <Link
            href={`/product/${opportunity.product_id}`}
            className="text-xl font-black text-primary-800 hover:text-primary-600 uppercase tracking-wide"
          >
            {opportunity.title || opportunity.product_id}
          </Link>
          <p className="text-sm text-gray-500 mt-1">
            Available at {opportunity.retailer_count} retailer{opportunity.retailer_count !== 1 ? 's' : ''}
          </p>
        </div>
        <div
          className={`px-3 py-1 rounded-full text-sm font-semibold ${getProfitColor(profitMargin)}`}
        >
          {profitMargin.toFixed(1)}% Margin
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-500">Lowest Price</p>
          <p className="text-xl font-bold text-green-600">
            {formatPrice(opportunity.min_price)}
          </p>
          {opportunity.cheapest_retailer && (
            <p className="text-xs text-gray-500 mt-1">
              at {opportunity.cheapest_retailer.toUpperCase()}
            </p>
          )}
        </div>
        <div>
          <p className="text-sm text-gray-500">Highest Price</p>
          <p className="text-xl font-bold text-red-600">
            {formatPrice(opportunity.max_price)}
          </p>
          {opportunity.expensive_retailer && (
            <p className="text-xs text-gray-500 mt-1">
              at {opportunity.expensive_retailer.toUpperCase()}
            </p>
          )}
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Potential Profit</p>
            <p className="text-2xl font-bold text-primary-600">
              {formatPrice(profitAmount)}
            </p>
          </div>
          <Link
            href={`/compare?product_ids=${opportunity.product_id}`}
            className="genx-button"
          >
            Compare →
          </Link>
        </div>
      </div>
    </div>
  )
}

