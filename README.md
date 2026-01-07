# North American Retail Intelligence & Analytics Pipeline

A distributed, production-ready web scraping system targeting Amazon and Walmart with intelligent anti-bot bypass, API reverse-engineering, and cloud-native data pipelines.

## Features

- **Distributed Architecture**: Scrapy-Redis for shared queue across multiple worker nodes
- **Intelligent Proxy Layer**: Bright Data Site Unblocker and Residential Proxy support with automatic failover
- **TLS Fingerprint Impersonation**: curl_cffi for bypassing fingerprint-based bot detection
- **API Discovery**: Automatic detection of hidden JSON APIs from Network Tab data
- **Multi-Tiered Storage**: 
  - Raw HTML archived to Google Cloud Storage
  - Structured data streamed to Google BigQuery for analytics
- **Resilience**: Exponential backoff for 429 errors and comprehensive proxy logging

## Architecture

```
┌─────────────────┐
│  Worker Nodes   │
│  (Scrapy)       │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Redis  │
    │  Queue  │
    └────┬────┘
         │
    ┌────▼──────────────┐
    │  Bright Data      │
    │  Proxy Middleware │
    └────┬──────────────┘
         │
    ┌────▼──────────────┐
    │  Target Sites      │
    │  (Amazon/Walmart)  │
    └───────────────────┘
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd WebScrapeAMZN
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your credentials
   ```

5. **Start Redis (using Docker)**
   ```bash
   docker-compose up -d redis
   ```

## Configuration

See `config/.env.example` for all required environment variables. Key configurations:

- **Redis**: Connection details for distributed queue
- **Bright Data**: Proxy credentials (Site Unblocker and/or Residential Proxy)
- **Google Cloud**: Service account credentials, GCS bucket, BigQuery dataset/table

Refer to the plan documentation for detailed instructions on obtaining each credential.

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

### Running Multiple Workers

Start multiple worker processes to scale horizontally:

```bash
# Terminal 1
scrapy crawl amazon

# Terminal 2
scrapy crawl amazon

# Terminal 3
scrapy crawl amazon
```

All workers share the same Redis queue, automatically distributing work.

### Proxy Configuration

Set `BRIGHT_DATA_PROXY_TYPE` in `.env`:
- `site_unblocker`: Use only Site Unblocker
- `residential`: Use only Residential Proxy
- `auto`: Try Site Unblocker first, fallback to Residential Proxy

## Project Structure

```
WebScrapeAMZN/
├── scrapy_project/
│   ├── scrapy.cfg
│   └── retail_intelligence/
│       ├── settings.py          # Scrapy settings
│       ├── items.py             # Item definitions
│       ├── pipelines.py         # GCS & BigQuery pipelines
│       ├── middlewares.py       # Proxy & resilience middleware
│       ├── spiders/
│       │   ├── amazon_spider.py
│       │   └── walmart_spider.py
│       └── utils/
│           ├── api_discovery.py
│           ├── curl_cffi_client.py
│           └── schema_mapper.py
├── config/
│   └── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## Data Flow

1. **Discovery**: Spiders discover hidden APIs from Network Tab data
2. **Scraping**: Requests routed through Bright Data proxies with exponential backoff
3. **Storage**: 
   - Raw HTML → Google Cloud Storage
   - Cleaned data → Google BigQuery
4. **Monitoring**: Proxy logging tracks success rates and performance

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

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]

