'use client'

import React from 'react'
import { ProductComparison, RetailerPrice } from '@/lib/api'
import Link from 'next/link'

interface ComparisonTableProps {
  comparisons: ProductComparison[]
}

export default function ComparisonTable({ comparisons }: ComparisonTableProps) {
  const formatPrice = (price?: number, currency?: string) => {
    if (!price) return 'N/A'
    const symbol = currency === 'USD' ? '$' : currency || '$'
    return `${symbol}${price.toFixed(2)}`
  }

  const getRetailerColor = (site: string) => {
    const colors: Record<string, string> = {
      amazon: 'bg-yellow-100 text-yellow-800',
      walmart: 'bg-blue-100 text-blue-800',
      kohls: 'bg-red-100 text-red-800',
      kmart: 'bg-green-100 text-green-800',
    }
    return colors[site.toLowerCase()] || 'bg-gray-100 text-gray-800'
  }

  if (comparisons.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No products to compare. Select products to compare.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border-4 border-primary-800">
        <thead className="bg-matcha-light border-b-4 border-primary-800">
          <tr>
            <th className="px-6 py-4 text-left text-sm font-black text-primary-800 uppercase tracking-wide">
              Product
            </th>
            <th className="px-6 py-4 text-left text-sm font-black text-primary-800 uppercase tracking-wide">
              Retailer
            </th>
            <th className="px-6 py-4 text-left text-sm font-black text-primary-800 uppercase tracking-wide">
              Price
            </th>
            <th className="px-6 py-4 text-left text-sm font-black text-primary-800 uppercase tracking-wide">
              Rating
            </th>
            <th className="px-6 py-4 text-left text-sm font-black text-primary-800 uppercase tracking-wide">
              Availability
            </th>
            <th className="px-6 py-4 text-left text-sm font-black text-primary-800 uppercase tracking-wide">
              Link
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y-2 divide-primary-300">
          {comparisons.map((comparison) => (
            <tr key={comparison.product_id} className="hover:bg-matcha-light transition-colors">
              <td className="px-6 py-4 whitespace-nowrap" rowSpan={comparison.retailers.length}>
                <div>
                  <Link
                    href={`/product/${comparison.product_id}`}
                    className="text-sm font-bold text-primary-900 hover:text-primary-600 uppercase tracking-wide"
                  >
                    {comparison.title || comparison.product_id}
                  </Link>
                  {comparison.price_difference && (
                    <p className="text-xs text-gray-500 mt-1">
                      Price Range: {formatPrice(comparison.min_price)} -{' '}
                      {formatPrice(comparison.max_price)} (Diff: {formatPrice(comparison.price_difference)})
                    </p>
                  )}
                </div>
              </td>
              {comparison.retailers.map((retailer: RetailerPrice, idx: number) => (
                <React.Fragment key={`${comparison.product_id}-${retailer.site}-${idx}`}>
                  {idx > 0 && <tr className="hover:bg-gray-50" />}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded ${getRetailerColor(
                        retailer.site
                      )}`}
                    >
                      {retailer.site.toUpperCase()}
                    </span>
                    {comparison.best_price_retailer === retailer.site && (
                      <span className="ml-2 text-xs text-green-600 font-semibold">Best Price</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-lg font-black text-primary-800">
                      {formatPrice(retailer.price, retailer.currency)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {retailer.rating ? (
                      <div className="flex items-center">
                        <span className="text-yellow-400">★</span>
                        <span className="text-sm text-gray-600 ml-1">
                          {retailer.rating.toFixed(1)}
                          {retailer.review_count && ` (${retailer.review_count})`}
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600">
                      {retailer.availability || 'Unknown'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <a
                      href={retailer.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-800 text-sm font-bold uppercase tracking-wide"
                    >
                      View →
                    </a>
                  </td>
                </React.Fragment>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

