'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import ProductCard from '@/components/ProductCard'
import SearchFilters, { FilterState } from '@/components/SearchFilters'
import LoadingSpinner from '@/components/LoadingSpinner'

export default function SearchPage() {
  const [filters, setFilters] = useState<FilterState>({
    query: '',
    brands: [],
    retailers: [],
    minPrice: null,
    maxPrice: null,
  })
  const [page, setPage] = useState(1)

  const { data, isLoading, error } = useQuery({
    queryKey: ['products', 'search', filters, page],
    queryFn: () =>
      api.searchProducts({
        query: filters.query || undefined,
        brands: filters.brands.length > 0 ? filters.brands : undefined,
        retailers: filters.retailers.length > 0 ? filters.retailers : undefined,
        min_price: filters.minPrice || undefined,
        max_price: filters.maxPrice || undefined,
        page,
        per_page: 20,
      }),
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-5xl font-black text-primary-900 mb-10 uppercase tracking-wide font-display drop-shadow-sm">Product Search</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <SearchFilters onFilterChange={(newFilters) => {
            setFilters(newFilters)
            setPage(1)
          }} />
        </div>

        {/* Results */}
        <div className="lg:col-span-3">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">Error loading products. Please try again.</p>
            </div>
          ) : data && data.data.length > 0 ? (
            <>
              <div className="mb-4">
                <p className="text-gray-600">
                  Found {data.meta.total} product{data.meta.total !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {data.data.map((product) => (
                  <ProductCard key={product.product_id} product={product} />
                ))}
              </div>
              {data.meta.total_pages > 1 && (
                <div className="flex justify-center gap-2 mt-8">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-6 py-3 font-bold bg-primary-200 text-primary-800 border-2 border-primary-800 shadow-genx disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none transition-all"
                  >
                    ← Previous
                  </button>
                  <span className="px-6 py-3 font-bold text-primary-800 bg-matcha-light border-2 border-primary-800">
                    Page {page} of {data.meta.total_pages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(data.meta.total_pages, p + 1))}
                    disabled={page === data.meta.total_pages}
                    className="px-6 py-3 font-bold bg-primary-200 text-primary-800 border-2 border-primary-800 shadow-genx disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none transition-all"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">No products found. Try adjusting your filters.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

