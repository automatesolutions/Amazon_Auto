'use client'

import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  const [scrapingJobs, setScrapingJobs] = useState<Record<string, { jobId: string; itemsScraped: number }>>({}) // retailer -> { jobId, itemsScraped }
  const queryClient = useQueryClient()

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

  // Generate search URLs for each retailer
  const generateSearchUrls = (query: string, retailers: string[]): Record<string, string[]> => {
    const urls: Record<string, string[]> = {}
    
    if (retailers.includes('amazon')) {
      urls.amazon = [`https://www.amazon.com/s?k=${encodeURIComponent(query)}`]
    }
    if (retailers.includes('walmart')) {
      urls.walmart = [`https://www.walmart.com/search?q=${encodeURIComponent(query)}`]
    }
    if (retailers.includes('kohls')) {
      urls.kohls = [`https://www.kohls.com/search.jsp?submit-search=web-regular&search=${encodeURIComponent(query)}`]
    }
    if (retailers.includes('kmart')) {
      urls.kmart = [`https://www.kmart.com/search=${encodeURIComponent(query)}`]
    }
    
    return urls
  }

  // Scrape mutation
  const scrapeMutation = useMutation({
    mutationFn: async ({ spiderName, startUrls }: { spiderName: string; startUrls: string[] }) => {
      return api.triggerSpider({
        spider_name: spiderName,
        start_urls: startUrls,
      })
    },
    onSuccess: (data, variables) => {
      setScrapingJobs(prev => ({
        ...prev,
        [variables.spiderName]: { jobId: data.job_id, itemsScraped: 0 },
      }))
    },
  })

  // Poll for scraping status and update progress
  useEffect(() => {
    if (Object.keys(scrapingJobs).length === 0) return

    const interval = setInterval(() => {
      Object.entries(scrapingJobs).forEach(([retailer, jobInfo]) => {
        api.getSpiderStatus(jobInfo.jobId).then((status) => {
          // Update items scraped count
          setScrapingJobs(prev => ({
            ...prev,
            [retailer]: {
              jobId: jobInfo.jobId,
              itemsScraped: status.items_scraped || 0,
            },
          }))

          if (status.status === 'completed') {
            // Refresh search results
            queryClient.invalidateQueries({ queryKey: ['products', 'search'] })
            // Remove from tracking after a short delay to show final count
            setTimeout(() => {
              setScrapingJobs(prev => {
                const next = { ...prev }
                delete next[retailer]
                return next
              })
            }, 2000)
          } else if (status.status === 'failed') {
            // Remove from tracking on failure after showing error
            setTimeout(() => {
              setScrapingJobs(prev => {
                const next = { ...prev }
                delete next[retailer]
                return next
              })
            }, 5000)
          }
        }).catch(console.error)
      })
    }, 3000) // Poll every 3 seconds

    return () => clearInterval(interval)
  }, [scrapingJobs, queryClient])

  const handleScrape = () => {
    if (!filters.query || filters.query.trim() === '') {
      alert('Please enter a search query first')
      return
    }

    const retailersToScrape = filters.retailers.length > 0 
      ? filters.retailers 
      : ['amazon', 'walmart', 'kohls', 'kmart'] // Default to all if none selected

    const searchUrls = generateSearchUrls(filters.query, retailersToScrape)

    // Trigger scraping for each selected retailer
    Object.entries(searchUrls).forEach(([retailer, urls]) => {
      if (!scrapingJobs[retailer]) { // Don't start duplicate jobs
        scrapeMutation.mutate({
          spiderName: retailer,
          startUrls: urls,
        })
      }
    })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-5xl font-black text-primary-900 mb-10 uppercase tracking-wide font-display drop-shadow-sm">Product Search</h1>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Filters Sidebar - Wider for better usability */}
        <div className="lg:col-span-3">
          <SearchFilters 
            onFilterChange={(newFilters) => {
              setFilters(newFilters)
              setPage(1)
            }}
            onScrape={handleScrape}
            isScraping={scrapeMutation.isPending || Object.keys(scrapingJobs).length > 0}
          />
        </div>

        {/* Results - Still has plenty of space */}
        <div className="lg:col-span-9">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">Error loading products. Please try again.</p>
            </div>
          ) : data && data.data.length > 0 ? (() => {
            const productsWithImages = data.data.filter((product) => {
              const imageUrl = product.image_url
              if (!imageUrl || typeof imageUrl !== 'string' || imageUrl.trim() === '') {
                return false
              }
              if (!imageUrl.startsWith('http://') && !imageUrl.startsWith('https://')) {
                return false
              }
              // Filter out placeholder images
              const placeholderPatterns = [
                'grey-pixel.gif',
                'pixel.gif',
                '1x1.gif',
                'blank.gif',
                'placeholder',
                'spacer.gif',
                'transparent.gif'
              ]
              const isPlaceholder = placeholderPatterns.some(pattern => 
                imageUrl.toLowerCase().includes(pattern)
              )
              return !isPlaceholder
            })
            
            if (productsWithImages.length === 0) {
              return (
                <div className="text-center py-12">
                  <p className="text-gray-600 mb-4 text-lg font-semibold">
                    No products with images found. Try adjusting your filters or scraping more products.
                  </p>
                </div>
              )
            }
            
            return (
            <>
              <div className="mb-4 flex items-center justify-between flex-wrap gap-4">
                <p className="text-gray-600">
                  Found {productsWithImages.length} product{productsWithImages.length !== 1 ? 's' : ''} with images
                  {data.meta.total !== productsWithImages.length && (
                    <span className="text-gray-400 ml-2">
                      (of {data.meta.total} total)
                    </span>
                  )}
                </p>
                {filters.query && (
                  <button
                    onClick={handleScrape}
                    disabled={scrapeMutation.isPending || Object.keys(scrapingJobs).length > 0}
                    className="px-6 py-2 text-sm font-bold bg-primary-700 text-white border-2 border-primary-900 hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-genx transition-all uppercase tracking-wide"
                  >
                    {scrapeMutation.isPending || Object.keys(scrapingJobs).length > 0
                      ? 'Scraping...'
                      : `Scrape More${filters.retailers.length > 0 ? ` (${filters.retailers.length} retailer${filters.retailers.length > 1 ? 's' : ''})` : ' (All)'}`}
                  </button>
                )}
              </div>
              {Object.keys(scrapingJobs).length > 0 && (
                <div className="mb-4 p-4 bg-primary-50 border-2 border-primary-300 rounded">
                  <p className="text-sm font-semibold text-primary-700 mb-3">Scraping in progress:</p>
                  <div className="space-y-2">
                    {Object.entries(scrapingJobs).map(([retailer, jobInfo]) => (
                      <div key={retailer} className="flex items-center justify-between bg-white p-3 rounded border-2 border-primary-200">
                        <span className="font-bold uppercase text-primary-800">{retailer}</span>
                        <span className="text-sm font-semibold text-primary-700">
                          {jobInfo.itemsScraped} item{jobInfo.itemsScraped !== 1 ? 's' : ''} scraped
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {productsWithImages
                  .filter((product) => {
                    // Additional client-side validation
                    const imageUrl = product.image_url
                    return imageUrl && 
                           typeof imageUrl === 'string' &&
                           imageUrl.trim() !== '' && 
                           (imageUrl.startsWith('http://') || imageUrl.startsWith('https://'))
                  })
                  .map((product) => (
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
            )
          })() : (
            <div className="text-center py-12">
              <div className="max-w-md mx-auto">
                <p className="text-gray-600 mb-4 text-lg font-semibold">
                  No products found. Try adjusting your filters.
                </p>
                {filters.query && (
                  <div className="space-y-4">
                    <p className="text-sm text-gray-500 mb-4">
                      Want to scrape products for "{filters.query}"? Select retailers and click below to start scraping.
                    </p>
                    <button
                      onClick={handleScrape}
                      disabled={scrapeMutation.isPending || Object.keys(scrapingJobs).length > 0}
                      className="px-8 py-4 font-bold bg-primary-700 text-white border-2 border-primary-900 hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-genx transition-all uppercase tracking-wide"
                    >
                      {scrapeMutation.isPending || Object.keys(scrapingJobs).length > 0
                        ? 'Scraping...'
                        : `Scrape Products${filters.retailers.length > 0 ? ` (${filters.retailers.length} retailer${filters.retailers.length > 1 ? 's' : ''})` : ' (All Retailers)'}`}
                    </button>
                    {Object.keys(scrapingJobs).length > 0 && (
                      <div className="mt-4 space-y-3">
                        <p className="text-sm font-semibold text-primary-700">Scraping in progress:</p>
                        <div className="space-y-2">
                          {Object.entries(scrapingJobs).map(([retailer, jobInfo]) => (
                            <div key={retailer} className="flex items-center justify-between bg-primary-100 p-3 rounded border-2 border-primary-300">
                              <span className="font-bold uppercase text-primary-800">{retailer}</span>
                              <span className="text-sm font-semibold text-primary-700">
                                {jobInfo.itemsScraped} item{jobInfo.itemsScraped !== 1 ? 's' : ''} scraped
                              </span>
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          Results will appear automatically when scraping completes...
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

