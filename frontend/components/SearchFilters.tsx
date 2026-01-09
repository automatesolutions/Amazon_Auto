'use client'

import { useState, useEffect } from 'react'
import { api, Brand } from '@/lib/api'

interface SearchFiltersProps {
  onFilterChange: (filters: FilterState) => void
}

export interface FilterState {
  query: string
  brands: string[]
  retailers: string[]
  minPrice: number | null
  maxPrice: number | null
}

const RETAILERS = [
  { value: 'amazon', label: 'Amazon' },
  { value: 'walmart', label: 'Walmart' },
  { value: 'kohls', label: "Kohl's" },
  { value: 'kmart', label: 'Kmart' },
]

export default function SearchFilters({ onFilterChange }: SearchFiltersProps) {
  const [brands, setBrands] = useState<Brand[]>([])
  const [filters, setFilters] = useState<FilterState>({
    query: '',
    brands: [],
    retailers: [],
    minPrice: null,
    maxPrice: null,
  })

  useEffect(() => {
    // Load brands
    api.getBrands().then(setBrands).catch(console.error)
  }, [])

  const updateFilter = (key: keyof FilterState, value: any) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const toggleBrand = (brand: string) => {
    const newBrands = filters.brands.includes(brand)
      ? filters.brands.filter((b) => b !== brand)
      : [...filters.brands, brand]
    updateFilter('brands', newBrands)
  }

  const toggleRetailer = (retailer: string) => {
    const newRetailers = filters.retailers.includes(retailer)
      ? filters.retailers.filter((r) => r !== retailer)
      : [...filters.retailers, retailer]
    updateFilter('retailers', newRetailers)
  }

  return (
    <div className="genx-card p-8">
      <h2 className="text-2xl font-black text-primary-800 mb-6 uppercase tracking-wide">Filters</h2>

      {/* Search Query */}
      <div className="mb-6">
        <label className="block text-sm font-bold text-primary-800 mb-3 uppercase tracking-wide">
          Search
        </label>
        <input
          type="text"
          value={filters.query}
          onChange={(e) => updateFilter('query', e.target.value)}
          placeholder="Search products..."
          className="w-full px-4 py-3 border-2 border-primary-800 bg-white text-primary-900 font-semibold focus:outline-none focus:ring-4 focus:ring-primary-300 shadow-genx"
        />
      </div>

      {/* Retailers */}
      <div className="mb-6">
        <label className="block text-sm font-bold text-primary-800 mb-3 uppercase tracking-wide">
          Retailers
        </label>
        <div className="space-y-2">
          {RETAILERS.map((retailer) => (
            <label key={retailer.value} className="flex items-center">
              <input
                type="checkbox"
                checked={filters.retailers.includes(retailer.value)}
                onChange={() => toggleRetailer(retailer.value)}
                className="mr-2"
              />
              <span className="text-sm">{retailer.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Brands */}
      <div className="mb-6">
        <label className="block text-sm font-bold text-primary-800 mb-3 uppercase tracking-wide">
          Brands
        </label>
        <div className="max-h-48 overflow-y-auto space-y-2">
          {brands.slice(0, 20).map((brand) => (
            <label key={brand.brand} className="flex items-center">
              <input
                type="checkbox"
                checked={filters.brands.includes(brand.brand)}
                onChange={() => toggleBrand(brand.brand)}
                className="mr-2"
              />
              <span className="text-sm">
                {brand.brand} ({brand.count})
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Price Range */}
      <div className="mb-6">
        <label className="block text-sm font-bold text-primary-800 mb-3 uppercase tracking-wide">
          Price Range
        </label>
        <div className="grid grid-cols-2 gap-3">
          <input
            type="number"
            placeholder="Min"
            value={filters.minPrice || ''}
            onChange={(e) =>
              updateFilter('minPrice', e.target.value ? parseFloat(e.target.value) : null)
            }
            className="px-4 py-3 border-2 border-primary-800 bg-white text-primary-900 font-semibold focus:outline-none focus:ring-4 focus:ring-primary-300 shadow-genx"
          />
          <input
            type="number"
            placeholder="Max"
            value={filters.maxPrice || ''}
            onChange={(e) =>
              updateFilter('maxPrice', e.target.value ? parseFloat(e.target.value) : null)
            }
            className="px-4 py-3 border-2 border-primary-800 bg-white text-primary-900 font-semibold focus:outline-none focus:ring-4 focus:ring-primary-300 shadow-genx"
          />
        </div>
      </div>

      {/* Clear Filters */}
      <button
        onClick={() => {
          const cleared = {
            query: '',
            brands: [],
            retailers: [],
            minPrice: null,
            maxPrice: null,
          }
          setFilters(cleared)
          onFilterChange(cleared)
        }}
        className="w-full px-6 py-3 font-bold bg-primary-200 text-primary-800 border-2 border-primary-800 hover:bg-primary-300 transition-all"
      >
        Clear Filters
      </button>
    </div>
  )
}

