"""
Scrapy settings for retail_intelligence project
"""
import os
import pathlib
from dotenv import load_dotenv

# Load environment variables from config/.env (relative to project root)
# settings.py is at: scrapy_project/retail_intelligence/settings.py
# .env is at: config/.env
project_root = pathlib.Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

BOT_NAME = 'retail_intelligence'

SPIDER_MODULES = ['retail_intelligence.spiders']
NEWSPIDER_MODULE = 'retail_intelligence.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure delays for requests
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# AutoThrottle settings
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Cookies
COOKIES_ENABLED = True

# Telnet Console
TELNETCONSOLE_ENABLED = False

# Default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    # Disable compression to avoid bad gzip responses from proxies
    'Accept-Encoding': 'identity',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Disable automatic response compression handling (some proxies mislabel bodies)
COMPRESSION_ENABLED = False

# Scheduler
# Using default Scrapy scheduler for direct runs.
# If you want distributed queues via Redis, restore scrapy-redis settings.
SCHEDULER = 'scrapy.core.scheduler.Scheduler'
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'
SCHEDULER_PERSIST = False

# Item pipelines
ITEM_PIPELINES = {
    'retail_intelligence.pipelines.GCSRawHTMLPipeline': 300,
    'retail_intelligence.pipelines.BigQueryAnalyticsPipeline': 400,
}

# Middleware configuration
DOWNLOADER_MIDDLEWARES = {
    'retail_intelligence.middlewares.BrightDataProxyMiddleware': 543,
    'retail_intelligence.middlewares.ExponentialBackoffMiddleware': 544,
    'retail_intelligence.middlewares.ProxyLoggingMiddleware': 545,
}

# Bright Data Configuration
# API-based access (Site Unblocker API - recommended)
BRIGHT_DATA_API_TOKEN = os.getenv('BRIGHT_DATA_API_TOKEN', '')
BRIGHT_DATA_ZONE = os.getenv('BRIGHT_DATA_ZONE', '')
BRIGHT_DATA_API_ENDPOINT = os.getenv('BRIGHT_DATA_API_ENDPOINT', 'https://api.brightdata.com/request')

# Traditional proxy access (legacy - username/password)
BRIGHT_DATA_USERNAME = os.getenv('BRIGHT_DATA_USERNAME', '')
BRIGHT_DATA_PASSWORD = os.getenv('BRIGHT_DATA_PASSWORD', '')
BRIGHT_DATA_ENDPOINT = os.getenv('BRIGHT_DATA_ENDPOINT', 'zproxy.lum-superproxy.io:22225')

BRIGHT_DATA_RESIDENTIAL_USERNAME = os.getenv('BRIGHT_DATA_RESIDENTIAL_USERNAME', '')
BRIGHT_DATA_RESIDENTIAL_PASSWORD = os.getenv('BRIGHT_DATA_RESIDENTIAL_PASSWORD', '')
BRIGHT_DATA_RESIDENTIAL_ENDPOINT = os.getenv('BRIGHT_DATA_RESIDENTIAL_ENDPOINT', 'brd.superproxy.io:22225')
BRIGHT_DATA_PROXY_TYPE = os.getenv('BRIGHT_DATA_PROXY_TYPE', 'site_unblocker')

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', '')
BQ_DATASET = os.getenv('BQ_DATASET', '')
BQ_TABLE = os.getenv('BQ_TABLE', '')

# Resilience Configuration
BACKOFF_BASE_DELAY = float(os.getenv('BACKOFF_BASE_DELAY', '1'))
BACKOFF_MAX_RETRIES = int(os.getenv('BACKOFF_MAX_RETRIES', '5'))
BACKOFF_MAX_WAIT = float(os.getenv('BACKOFF_MAX_WAIT', '300'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Enable and configure AutoThrottle extension
AUTOTHROTTLE_ENABLED = True

