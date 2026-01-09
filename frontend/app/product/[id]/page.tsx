'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import { api } from '@/lib/api'
import PriceChart from '@/components/PriceChart'
import LoadingSpinner from '@/components/LoadingSpinner'
import Link from 'next/link'

export default function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params)
  const productId = resolvedParams.id

  const { data: product, isLoading: productLoading } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => api.getProduct(productId),
  })

  const { data: retailers, isLoading: retailersLoading } = useQuery({
    queryKey: ['product-retailers', productId],
    queryFn: () => api.getProductRetailers(productId),
  })

  const { data: priceHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['price-history', productId],
    queryFn: () => api.getPriceHistory(productId, 30),
  })

  if (productLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <p className="text-red-600">Product not found</p>
          <Link href="/" className="genx-button mt-4 inline-block">
            Go back home
          </Link>
        </div>
      </div>
    )
  }

  const formatPrice = (price?: number, currency?: string) => {
    if (!price) return 'N/A'
    const symbol = currency === 'USD' ? '$' : currency || '$'
    return `${symbol}${price.toFixed(2)}`
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Product Image */}
        <div className="genx-card p-8">
          {product.image_url ? (
            <div className="relative h-96 bg-matcha-light border-2 border-primary-800">
              <Image
                src={product.image_url}
                alt={product.title || 'Product image'}
                fill
                className="object-contain rounded-lg"
                sizes="(max-width: 768px) 100vw, 50vw"
              />
            </div>
          ) : (
            <div className="h-96 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
              No Image Available
            </div>
          )}
        </div>

        {/* Product Info */}
        <div className="genx-card p-8">
          <h1 className="text-4xl font-black text-primary-800 mb-6 uppercase tracking-wide">
            {product.title || 'Untitled Product'}
          </h1>

          {product.description && (
            <p className="text-primary-700 mb-8 font-semibold">{product.description}</p>
          )}

          <div className="space-y-6">
            <div>
              <span className="text-sm font-bold text-primary-700 uppercase tracking-wide">Price</span>
              <p className="text-4xl font-black text-primary-800 mt-2">
                {formatPrice(product.price, product.currency)}
              </p>
            </div>

            {product.rating && (
              <div>
                <span className="text-sm text-gray-500">Rating</span>
                <div className="flex items-center">
                  <span className="text-yellow-400 text-2xl">★</span>
                  <span className="text-lg font-semibold ml-2">
                    {product.rating.toFixed(1)}
                    {product.review_count && ` (${product.review_count} reviews)`}
                  </span>
                </div>
              </div>
            )}

            {product.brand && (
              <div>
                <span className="text-sm font-bold text-primary-700 uppercase tracking-wide">Brand</span>
                <p className="text-lg font-bold text-primary-800 mt-1">{product.brand}</p>
              </div>
            )}

            {product.model && (
              <div>
                <span className="text-sm font-bold text-primary-700 uppercase tracking-wide">Model</span>
                <p className="text-lg font-bold text-primary-800 mt-1">{product.model}</p>
              </div>
            )}

            {product.category && (
              <div>
                <span className="text-sm font-bold text-primary-700 uppercase tracking-wide">Category</span>
                <p className="text-lg font-bold text-primary-800 mt-1">{product.category}</p>
              </div>
            )}

            {product.availability && (
              <div>
                <span className="text-sm font-bold text-primary-700 uppercase tracking-wide">Availability</span>
                <p className="text-lg font-bold text-primary-800 mt-1">{product.availability}</p>
              </div>
            )}

            <div>
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                className="genx-button inline-block"
              >
                View on {product.site.toUpperCase()} →
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Retailers Comparison */}
      {retailers && retailers.data.length > 0 && (
        <div className="genx-card p-8 mb-10">
          <h2 className="text-3xl font-black text-primary-800 mb-6 uppercase tracking-wide">Available at Other Retailers</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {retailers.data[0].retailers.map((retailer, idx) => (
              <div key={idx} className="border-2 border-primary-800 bg-matcha-light p-6">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-black text-primary-800 uppercase tracking-wide">{retailer.site.toUpperCase()}</span>
                  <span className="text-2xl font-black text-primary-800">
                    {formatPrice(retailer.price, retailer.currency)}
                  </span>
                </div>
                {retailer.rating && (
                  <div className="text-sm font-bold text-primary-700 mb-3">
                    ★ {retailer.rating.toFixed(1)}
                    {retailer.review_count && ` (${retailer.review_count})`}
                  </div>
                )}
                <a
                  href={retailer.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-800 text-sm font-bold uppercase tracking-wide"
                >
                  View Product →
                </a>
              </div>
            ))}
          </div>
          <div className="mt-6">
            <Link
              href={`/compare?product_ids=${productId}`}
              className="genx-button inline-block"
            >
              Compare all retailers →
            </Link>
          </div>
        </div>
      )}

      {/* Price History */}
      {priceHistory && priceHistory.data.length > 0 && (
        <div className="mb-8">
          <PriceChart data={priceHistory.data} title="Price History (Last 30 Days)" />
        </div>
      )}
    </div>
  )
}

