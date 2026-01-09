'use client'

import { useState, useEffect, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'
import ComparisonTable from '@/components/ComparisonTable'
import LoadingSpinner from '@/components/LoadingSpinner'

function CompareContent() {
  const searchParams = useSearchParams()
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])

  useEffect(() => {
    const productIds = searchParams.get('product_ids')
    if (productIds) {
      setSelectedProducts(productIds.split(','))
    }
  }, [searchParams])

  const { data, isLoading, error } = useQuery({
    queryKey: ['comparison', selectedProducts],
    queryFn: () => api.compareProducts(selectedProducts),
    enabled: selectedProducts.length > 0,
  })

  const handleProductSelect = (productId: string) => {
    setSelectedProducts((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId]
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-5xl font-black text-primary-900 mb-10 uppercase tracking-wide font-display drop-shadow-sm">Compare Products</h1>

      {selectedProducts.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">
            Select products to compare. Search for products and click "Select" to add them.
          </p>
          <a
            href="/search"
            className="genx-button inline-block"
          >
            Go to Search
          </a>
        </div>
      ) : (
        <>
          <div className="mb-6">
            <h2 className="text-2xl font-black text-primary-800 mb-4 uppercase tracking-wide">Selected Products ({selectedProducts.length})</h2>
            <div className="flex flex-wrap gap-3">
              {selectedProducts.map((productId) => (
                <button
                  key={productId}
                  onClick={() => handleProductSelect(productId)}
                  className="px-4 py-2 font-bold bg-primary-600 text-white border-2 border-primary-800 shadow-genx hover:bg-primary-700 transition-all"
                >
                  {productId} ×
                </button>
              ))}
              <button
                onClick={() => setSelectedProducts([])}
                className="px-4 py-2 font-bold bg-primary-200 text-primary-800 border-2 border-primary-800 hover:bg-primary-300 transition-all"
              >
                Clear All
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">Error loading comparison. Please try again.</p>
            </div>
          ) : data ? (
            <ComparisonTable comparisons={data.data} />
          ) : null}
        </>
      )}
    </div>
  )
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}>
      <CompareContent />
    </Suspense>
  )
}

