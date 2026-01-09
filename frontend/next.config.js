/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    domains: [
      'storage.googleapis.com',
      'images-na.ssl-images-amazon.com',
      'm.media-amazon.com',
      'images.amazon.com',
      'i5.walmartimages.com',
      'i.walmartimages.com',
    ],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.googleapis.com',
      },
      {
        protocol: 'https',
        hostname: '**.amazon.com',
      },
      {
        protocol: 'https',
        hostname: '**.walmart.com',
      },
      {
        protocol: 'https',
        hostname: '**.walmartimages.com',
      },
      {
        protocol: 'https',
        hostname: '**.kohls.com',
      },
      {
        protocol: 'https',
        hostname: '**.kmart.com',
      },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig

