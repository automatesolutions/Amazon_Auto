'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import Image from 'next/image'

export default function Navigation() {
  const pathname = usePathname()

  const navItems = [
    { href: '/', label: 'Home' },
    { href: '/search', label: 'Search' },
    { href: '/compare', label: 'Compare' },
    { href: '/arbitrage', label: 'Arbitrage' },
  ]

  return (
    <nav className="bg-white/90 backdrop-blur-md border-b-4 border-primary-900 shadow-genx">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-20">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-3">
              <div className="relative w-10 h-10">
                <Image
                  src="/logo.png"
                  alt="CrossRetail Logo"
                  fill
                  className="object-contain"
                  priority
                />
              </div>
              <span className="text-3xl font-black text-primary-900 tracking-tight uppercase font-display">CrossRetail</span>
            </Link>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-6">
              {navItems.map((item) => {
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex items-center px-4 py-2 text-sm font-black uppercase tracking-wide transition-all ${
                      isActive
                        ? 'bg-primary-700 text-white border-3 border-primary-900 shadow-genx'
                        : 'text-primary-900 hover:bg-primary-100 border-2 border-transparent hover:border-primary-700 font-bold'
                    }`}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

