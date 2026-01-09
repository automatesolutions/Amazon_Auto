'use client'

import Image from 'next/image'
import Link from 'next/link'
import { Product } from '@/lib/api'

interface ProductCardProps {
  product: Product
  onSelect?: (productId: string) => void
  selected?: boolean
}

export default function ProductCard({ product, onSelect, selected }: ProductCardProps) {
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

  return (
    <div
      className={`genx-card overflow-hidden transition-all ${
        selected ? 'ring-4 ring-primary-400' : ''
      }`}
    >
      <div className="relative h-48 bg-white border-b-3 border-primary-900">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.title || 'Product image'}
            fill
            className="object-contain"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            No Image
          </div>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <span
            className={`px-2 py-1 text-xs font-semibold rounded ${getRetailerColor(
              product.site
            )}`}
          >
            {product.site.toUpperCase()}
          </span>
          {onSelect && (
            <button
              onClick={() => onSelect(product.product_id)}
              className={`px-4 py-2 text-sm font-black border-3 border-primary-900 transition-all ${
                selected
                  ? 'bg-primary-700 text-white shadow-genx'
                  : 'bg-primary-50 text-primary-900 hover:bg-primary-100 font-bold'
              }`}
            >
              {selected ? '✓ Selected' : 'Select'}
            </button>
          )}
        </div>
        <Link href={`/product/${product.product_id}`}>
          <h3 className="text-lg font-black text-primary-900 mb-3 line-clamp-2 hover:text-primary-700 uppercase tracking-wide font-display">
            {product.title || 'Untitled Product'}
          </h3>
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-3xl font-black text-primary-900">
              {formatPrice(product.price, product.currency)}
            </p>
            {product.rating && (
              <div className="flex items-center mt-1">
                <span className="text-yellow-400">★</span>
                <span className="text-sm text-gray-600 ml-1">
                  {product.rating.toFixed(1)}
                  {product.review_count && ` (${product.review_count})`}
                </span>
              </div>
            )}
          </div>
        </div>
        {product.brand && (
          <p className="text-sm font-semibold text-primary-700 mt-3 uppercase">Brand: {product.brand}</p>
        )}
        {product.availability && (
          <p className="text-sm font-semibold text-primary-600 mt-2">
            {product.availability}
          </p>
        )}
      </div>
    </div>
  )
}

