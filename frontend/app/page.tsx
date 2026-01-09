'use client'

import Link from 'next/link'
import Image from 'next/image'

export default function HomePage() {

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="text-center mb-16">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <div className="relative w-32 h-32 md:w-40 md:h-40">
            <Image
              src="/logo.png"
              alt="CrossRetail Logo"
              fill
              className="object-contain"
              priority
            />
          </div>
        </div>
        
        <h1 className="text-6xl md:text-7xl font-black text-primary-900 mb-4 tracking-tight uppercase font-display drop-shadow-lg">
          CrossRetail
        </h1>
        <p className="text-lg md:text-xl font-bold text-primary-800 mb-10 max-w-2xl mx-auto leading-relaxed drop-shadow-sm">
          Compare prices across Amazon, Walmart, Kohl's, Kmart, and more
        </p>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
        <Link
          href="/search"
          className="genx-card p-8 text-center transition-all"
        >
          <h2 className="text-2xl font-black text-primary-800 mb-4 uppercase tracking-wide">Search Products</h2>
          <p className="text-primary-700 font-semibold">Find products across all retailers</p>
        </Link>
        <Link
          href="/compare"
          className="genx-card p-8 text-center transition-all"
        >
          <h2 className="text-2xl font-black text-primary-800 mb-4 uppercase tracking-wide">Compare Prices</h2>
          <p className="text-primary-700 font-semibold">Side-by-side price comparison</p>
        </Link>
        <Link
          href="/arbitrage"
          className="genx-card p-8 text-center transition-all"
        >
          <h2 className="text-2xl font-black text-primary-800 mb-4 uppercase tracking-wide">Arbitrage Opportunities</h2>
          <p className="text-primary-700 font-semibold">Find profitable price differences</p>
        </Link>
      </div>

    </div>
  )
}

