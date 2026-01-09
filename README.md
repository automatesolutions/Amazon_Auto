# CrossRetail

**Multi-Retailer Price Intelligence & Arbitrage Analytics Platform**

A production-ready web scraping and analytics system for comparing product prices across Amazon, Walmart, Kohl's, Kmart, and other major retailers. Features intelligent anti-bot bypass with Bright Data Site Unblocker API, API reverse-engineering, cloud-native data pipelines, and a modern web application for real-time price comparison and arbitrage opportunity detection.

## Features

### Web Scraping
- **Flexible Architecture**: Supports both single-instance and distributed modes (scrapy-redis ready)
- **Bright Data Integration**: 
  - **Site Unblocker API**: Token-based API access (recommended) for automatic anti-bot bypass
  - **Traditional Proxy**: Username/password proxy support with automatic failover
  - **Residential Proxy**: Optional residential proxy support for additional resilience
- **API Discovery**: Automatic detection of hidden JSON APIs from Network Tab data
- **Multi-Retailer Support**: Spiders for Amazon, Walmart, Kohl's, and Kmart
- **Resilience**: Exponential backoff for 429 errors, automatic retries, and comprehensive proxy logging

### Data Storage & Analytics
- **Multi-Tiered Storage**: 
  - Raw HTML archived to Google Cloud Storage (`raw/{site}/{date}/{product_id}.html`)
  - Structured data streamed to Google BigQuery for analytics (batch inserts, auto schema creation)
- **BigQuery Schema**: Comprehensive schema with product details (brand, model, category, SKU, ratings, reviews)
- **Redis Caching**: Fast response times with intelligent caching for API endpoints

### Web Application
- **FastAPI Backend**: RESTful API with automatic OpenAPI documentation
- **Product Search**: Advanced search with filters (brand, retailer, price range, pagination)
- **Price Comparison**: Side-by-side comparison across multiple retailers
- **Arbitrage Dashboard**: Find profitable price differences automatically
- **Price History**: Visualize price trends over time with interactive charts
- **Spider Management**: Trigger and monitor scraping jobs via API
- **Modern UI**: Built with Next.js 14, React 18, TypeScript, and Tailwind CSS

## Architecture

```
┌─────────────────────┐
│  Frontend (Next.js) │
│  - Search           │
│  - Compare          │
│  - Arbitrage        │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │  Backend   │
    │  (FastAPI) │
    └──────┬──────┘
           │
    ┌──────▼──────┐      ┌──────────────┐
    │  BigQuery   │      │  Redis Cache │
    │  Analytics  │      │              │
    └──────┬──────┘      └──────────────┘
           │
    ┌──────▼──────────────────────────┐
    │  Scrapy Spiders                  │
    │  (Amazon, Walmart, Kohl's, Kmart)│
    └──────┬───────────────────────────┘
           │
    ┌──────▼──────────────┐
    │  Bright Data        │
    │  Proxy Middleware    │
    └──────┬──────────────┘
           │
    ┌──────▼──────────────┐
    │  Target Retailers   │
    └─────────────────────┘
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker and Docker Compose
- Google Cloud Platform account with BigQuery and GCS access

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd WebScrapeAMZN
   ```

2. **Configure environment variables**
   ```bash
   cp config/env_template.txt config/.env
   # Edit config/.env with your credentials
   ```

3. **Start all services with Docker Compose**
   ```bash
   docker-compose up -d
   ```
   This will start:
   - Redis (port 6379)
   - Backend API (port 8000)
   - Frontend (port 3000)

### Manual Setup

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

#### Scrapy Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd scrapy_project
```

## Configuration

Copy `config/env_template.txt` to `config/.env` and configure the following:

### Required Configuration

- **Bright Data API Access** (Recommended):
  - `BRIGHT_DATA_API_TOKEN`: Your Bright Data API token (Bearer token)
  - `BRIGHT_DATA_ZONE`: Your zone name (e.g., `webscrape_amzn`)
  - `BRIGHT_DATA_API_ENDPOINT`: API endpoint (default: `https://api.brightdata.com/request`)
  - `BRIGHT_DATA_PROXY_TYPE`: Set to `site_unblocker` for API mode

- **Bright Data Traditional Proxy** (Alternative):
  - `BRIGHT_DATA_USERNAME`: Site Unblocker username
  - `BRIGHT_DATA_PASSWORD`: Site Unblocker password
  - `BRIGHT_DATA_ENDPOINT`: Proxy endpoint (e.g., `zproxy.lum-superproxy.io:22225`)

- **Bright Data Residential Proxy** (Optional - for failover):
  - `BRIGHT_DATA_RESIDENTIAL_USERNAME`: Residential proxy username
  - `BRIGHT_DATA_RESIDENTIAL_PASSWORD`: Residential proxy password
  - `BRIGHT_DATA_RESIDENTIAL_ENDPOINT`: Residential proxy endpoint

### Optional Configuration

- **Redis**: Connection details (currently optional, required only for distributed mode)
  - `REDIS_HOST`: Redis host (default: `localhost`)
  - `REDIS_PORT`: Redis port (default: `6379`)
  - `REDIS_PASSWORD`: Redis password (if required)

- **Google Cloud Platform**: For data storage
  - `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account JSON key file
  - `GCS_BUCKET_NAME`: Google Cloud Storage bucket name for raw HTML
  - `BQ_DATASET`: BigQuery dataset name
  - `BQ_TABLE`: BigQuery table name

- **Resilience Settings**:
  - `BACKOFF_BASE_DELAY`: Base delay for exponential backoff (default: `1` second)
  - `BACKOFF_MAX_RETRIES`: Maximum retry attempts (default: `5`)
  - `BACKOFF_MAX_WAIT`: Maximum wait time (default: `300` seconds)

See `config/env_template.txt` for detailed setup instructions and examples.

## Usage

### Running Spiders

**Amazon Spider:**
```bash
cd scrapy_project
scrapy crawl amazon -a start_urls="https://www.amazon.com/s?k=laptop"
```

**Walmart Spider:**
```bash
cd scrapy_project
scrapy crawl walmart -a start_urls="https://www.walmart.com/search?q=laptop"
```

**Kohl's Spider:**
```bash
cd scrapy_project
scrapy crawl kohls -a start_urls="https://www.kohls.com/search.jsp?search=laptop"
```

**Kmart Spider:**
```bash
cd scrapy_project
scrapy crawl kmart -a start_urls="https://www.kmart.com/search=laptop"
```

### Enabling Distributed Mode (Scrapy-Redis)

To enable distributed scraping with multiple workers:

1. **Enable Redis scheduler** in `scrapy_project/retail_intelligence/settings.py`:
   ```python
   # Replace lines 59-61 with:
   SCHEDULER = 'scrapy_redis.scheduler.Scheduler'
   DUPEFILTER_CLASS = 'scrapy_redis.dupefilter.RFPDupeFilter'
   SCHEDULER_PERSIST = True
   ```

2. **Configure Redis connection** in `config/.env`:
   ```
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=
   ```

3. **Start Redis** (if using Docker Compose):
   ```bash
   docker-compose up -d redis
   ```

4. **Start multiple workers** in separate terminals:
   ```bash
   # Terminal 1
   cd scrapy_project
   scrapy crawl amazon

   # Terminal 2
   cd scrapy_project
   scrapy crawl amazon

   # Terminal 3
   cd scrapy_project
   scrapy crawl amazon
   ```

All workers will share the same Redis queue, automatically distributing work.

### Proxy Configuration

The middleware supports multiple proxy access methods:

**1. Bright Data Site Unblocker API (Recommended)**
- Uses token-based API access for automatic anti-bot bypass
- Configure with `BRIGHT_DATA_API_TOKEN` and `BRIGHT_DATA_ZONE`
- Set `BRIGHT_DATA_PROXY_TYPE=site_unblocker`

**2. Traditional Proxy Access**
- Uses username/password authentication
- Configure with `BRIGHT_DATA_USERNAME` and `BRIGHT_DATA_PASSWORD`
- Works with Site Unblocker and Residential proxies

**3. Proxy Selection Strategy**
Set `BRIGHT_DATA_PROXY_TYPE` in `.env`:
- `site_unblocker`: Use only Site Unblocker (API or proxy)
- `residential`: Use only Residential Proxy
- `auto`: Try Site Unblocker first, automatically fallback to Residential Proxy on failures

**Features:**
- Automatic retry with exponential backoff on API timeouts
- Automatic failover from Site Unblocker to Residential Proxy (in `auto` mode)
- Comprehensive logging of proxy usage and performance metrics

## Project Structure

```
WebScrapeAMZN/
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/                 # API route handlers
│   │   │   ├── products.py      # Product search and retrieval
│   │   │   ├── comparison.py    # Price comparison endpoints
│   │   │   ├── arbitrage.py     # Arbitrage opportunity detection
│   │   │   └── spiders.py       # Spider job management
│   │   ├── services/            # Business logic services
│   │   │   ├── bigquery_service.py  # BigQuery data access
│   │   │   ├── cache_service.py     # Redis caching
│   │   │   └── gcs_service.py       # GCS file operations
│   │   └── models/              # Pydantic data models
│   │       ├── product.py
│   │       ├── comparison.py
│   │       └── arbitrage.py
│   ├── scripts/                 # Utility scripts
│   │   ├── check_and_fix_bigquery_schema.py
│   │   └── create_bigquery_views.sql
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                     # Next.js 14 Frontend
│   ├── app/                     # Next.js App Router (pages)
│   │   ├── page.tsx             # Home page
│   │   ├── search/              # Product search page
│   │   ├── compare/             # Price comparison page
│   │   ├── arbitrage/           # Arbitrage dashboard
│   │   └── product/[id]/        # Product detail page
│   ├── components/              # React components
│   │   ├── ProductCard.tsx
│   │   ├── ComparisonTable.tsx
│   │   ├── ArbitrageCard.tsx
│   │   ├── PriceChart.tsx
│   │   └── ...
│   ├── lib/                     # Utilities
│   │   └── api.ts               # API client
│   ├── Dockerfile
│   └── package.json
├── scrapy_project/              # Scrapy Scraping System
│   ├── scrapy.cfg               # Scrapy project configuration
│   └── retail_intelligence/
│       ├── settings.py          # Scrapy settings (loads from config/.env)
│       ├── items.py             # ProductItem schema definition
│       ├── pipelines.py         # Data processing pipelines
│       │   ├── GCSRawHTMLPipeline       # GCS upload pipeline
│       │   └── BigQueryAnalyticsPipeline # BigQuery insertion pipeline
│       ├── middlewares.py       # Request/response middlewares
│       │   ├── BrightDataProxyMiddleware    # Bright Data proxy routing
│       │   ├── ExponentialBackoffMiddleware # 429 error handling
│       │   └── ProxyLoggingMiddleware       # Proxy statistics
│       ├── spiders/             # Spider implementations
│       │   ├── amazon_spider.py
│       │   ├── walmart_spider.py
│       │   ├── kohls_spider.py
│       │   └── kmart_spider.py
│       └── utils/               # Utility modules
│           ├── api_discovery.py      # API endpoint discovery
│           ├── curl_cffi_client.py   # TLS fingerprint client
│           └── schema_mapper.py      # Data normalization
├── config/
│   ├── env_template.txt         # Environment variable template
│   └── gcp-credentials.json     # GCP service account key (not in git)
├── docker-compose.yml           # Docker Compose configuration
├── requirements.txt             # Python dependencies (Scrapy)
└── README.md
```

## API Endpoints

### Products
- `GET /api/products/search` - Search products with filters
- `GET /api/products/{product_id}` - Get single product
- `GET /api/products/brands/list` - Get available brands

### Comparison
- `POST /api/comparison/compare` - Compare multiple products
- `GET /api/comparison/{product_id}` - Get all retailers for a product

### Arbitrage
- `GET /api/arbitrage/opportunities` - Get arbitrage opportunities
- `GET /api/arbitrage/price-history/{product_id}` - Get price history

### Spiders
- `POST /api/spiders/trigger` - Trigger scraping job
- `GET /api/spiders/status/{job_id}` - Get job status

API documentation available at `http://localhost:8000/docs` when backend is running.

## Data Flow

1. **Discovery**: Spiders discover hidden APIs from Network Tab data
2. **Scraping**: Requests routed through Bright Data proxies with exponential backoff
3. **Storage**: 
   - Raw HTML → Google Cloud Storage
   - Cleaned data → Google BigQuery (with brand, model, category, SKU)
4. **Analytics**: BigQuery materialized views for fast queries
5. **API**: FastAPI backend serves data to frontend
6. **Frontend**: Next.js app displays comparisons and arbitrage opportunities
7. **Caching**: Redis caches frequent queries for performance

## Monitoring

Proxy statistics are logged periodically and on spider close:
- Request counts per proxy type
- Success/failure rates
- Average response times
- Error tracking

## Troubleshooting

### Redis Connection Issues
- Ensure Redis is running: `docker-compose ps`
- Check `REDIS_HOST` and `REDIS_PORT` in `.env`

### Proxy Authentication Errors
- Verify Bright Data credentials in dashboard
- Check proxy endpoint format matches Bright Data documentation

### BigQuery Errors
- Ensure service account has required permissions
- Verify dataset and table exist (or enable auto-creation)
- Run `backend/scripts/create_bigquery_views.sql` to create optimized views

### Frontend Issues
- Ensure backend API is running on port 8000
- Check `NEXT_PUBLIC_API_URL` environment variable
- Clear browser cache if seeing stale data

### Backend Issues
- Check Redis connection: `docker-compose ps redis`
- Verify GCP credentials path in environment variables
- Check API logs: `docker-compose logs backend`
- Verify BigQuery table exists: Check `BQ_DATASET` and `BQ_TABLE` in `.env`

### Bright Data API Issues
- **API Token Invalid**: Verify `BRIGHT_DATA_API_TOKEN` matches your Bright Data dashboard
- **Zone Not Found**: Ensure `BRIGHT_DATA_ZONE` matches your zone name exactly
- **API Timeouts**: The middleware automatically retries with exponential backoff (up to 3 retries)
- **Fallback to Proxy**: If API fails after retries, the system will fallback to traditional proxy if configured

## License

[Your License Here]

## Contributing

Contributions are welcome! If you'd like to improve this project, fix bugs, or add new features, feel free to fork the repository, make your changes, and submit a pull request. Your efforts will help make this trading application even better!

If you found this project helpful or learned something new from it, you can support the development with just a cup of coffee ☕. It's always appreciated and keeps the ideas flowing!

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-blue?style=for-the-badge&logo=coffee&logoColor=white)](https://buymeacoffee.com/jonelpericon)

