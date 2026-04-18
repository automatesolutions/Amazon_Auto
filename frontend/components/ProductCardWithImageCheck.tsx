'use client'

import { useState, useEffect } from 'react'
import ProductCard from './ProductCard'
import { Product } from '@/lib/api'

interface ProductCardWithImageCheckProps {
  product: Product
  onSelect?: (productId: string) => void
  selected?: boolean
  onImageLoadSuccess?: (productId: string) => void
  onImageLoadError?: (productId: string) => void
}

export default function ProductCardWithImageCheck({ 
  product, 
  onSelect, 
  selected,
  onImageLoadSuccess,
  onImageLoadError 
}: ProductCardWithImageCheckProps) {
  const [imageValid, setImageValid] = useState<boolean | null>(null) // null = checking, true = valid, false = invalid

  useEffect(() => {
    // Check if product has a valid image URL
    const hasValidImageUrl = product.image_url && 
      product.image_url.trim() !== '' && 
      (product.image_url.startsWith('http://') || product.image_url.startsWith('https://'))
    
    if (!hasValidImageUrl) {
      setImageValid(false)
      onImageLoadError?.(product.product_id)
      return
    }

    // Pre-validate image by trying to load it
    const img = new Image()
    img.onload = () => {
      setImageValid(true)
      onImageLoadSuccess?.(product.product_id)
    }
    img.onerror = () => {
      setImageValid(false)
      onImageLoadError?.(product.product_id)
    }
    img.src = product.image_url!

    // Cleanup
    return () => {
      img.onload = null
      img.onerror = null
    }
  }, [product.image_url, product.product_id, onImageLoadSuccess, onImageLoadError])

  // Don't render until we know if image is valid
  if (imageValid === null) {
    return null // or a loading placeholder
  }

  // Only render if image is valid
  if (!imageValid) {
    return null
  }

  return <ProductCard product={product} onSelect={onSelect} selected={selected} />
}
