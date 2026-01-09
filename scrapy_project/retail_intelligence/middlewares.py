"""
Scrapy middlewares for retail_intelligence project
"""
import logging
import time
import json
import requests
from urllib.parse import urlparse
from scrapy import signals
from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
from scrapy.exceptions import NotConfigured, IgnoreRequest
from scrapy.http import Request, Response, TextResponse
from scrapy.utils.misc import load_object

logger = logging.getLogger(__name__)


class BrightDataProxyMiddleware:
    """
    Middleware for routing requests through Bright Data.
    Supports both Site Unblocker API (token-based) and traditional proxy (username/password).
    """
    
    def __init__(self, settings):
        self.settings = settings
        
        # Site Unblocker API configuration (NEW - token-based)
        self.api_token = settings.get('BRIGHT_DATA_API_TOKEN', '')
        self.zone = settings.get('BRIGHT_DATA_ZONE', '')
        self.api_endpoint = settings.get('BRIGHT_DATA_API_ENDPOINT', 'https://api.brightdata.com/request')
        self.use_api = bool(self.api_token and self.zone)
        
        # Traditional Site Unblocker proxy configuration (legacy - username/password)
        self.site_unblocker_username = settings.get('BRIGHT_DATA_USERNAME', '')
        self.site_unblocker_password = settings.get('BRIGHT_DATA_PASSWORD', '')
        self.site_unblocker_endpoint = settings.get('BRIGHT_DATA_ENDPOINT', 'zproxy.lum-superproxy.io:22225')
        
        # Residential Proxy configuration
        self.residential_username = settings.get('BRIGHT_DATA_RESIDENTIAL_USERNAME', '')
        self.residential_password = settings.get('BRIGHT_DATA_RESIDENTIAL_PASSWORD', '')
        self.residential_endpoint = settings.get('BRIGHT_DATA_RESIDENTIAL_ENDPOINT', 'brd.superproxy.io:22225')
        
        # Proxy selection strategy
        self.proxy_type = settings.get('BRIGHT_DATA_PROXY_TYPE', 'site_unblocker').lower()
        
        # Check configuration
        site_unblocker_configured = self.use_api or (bool(self.site_unblocker_username and self.site_unblocker_password))
        residential_configured = bool(self.residential_username and self.residential_password)
        
        if not site_unblocker_configured and not residential_configured:
            raise NotConfigured('Bright Data credentials not configured. Set BRIGHT_DATA_API_TOKEN and BRIGHT_DATA_ZONE for API access, or BRIGHT_DATA_USERNAME and BRIGHT_DATA_PASSWORD for proxy access.')
        
        # Build proxy URLs (only for traditional proxy mode)
        self.site_unblocker_proxy = None
        if not self.use_api and site_unblocker_configured:
            self.site_unblocker_proxy = f'http://{self.site_unblocker_username}:{self.site_unblocker_password}@{self.site_unblocker_endpoint}'
        
        self.residential_proxy = None
        if residential_configured:
            self.residential_proxy = f'http://{self.residential_username}:{self.residential_password}@{self.residential_endpoint}'
        
        # Track proxy usage for failover
        self.proxy_failures = {}
        self.max_failures_before_switch = 3
        
        logger.info(f'Bright Data Middleware initialized. Mode: {"API" if self.use_api else "Proxy"}, Proxy type: {self.proxy_type}')
        if self.use_api:
            logger.info(f'Site Unblocker API configured (zone: {self.zone})')
        elif site_unblocker_configured:
            logger.info('Site Unblocker Proxy configured')
        if residential_configured:
            logger.info('Residential Proxy configured')
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def process_request(self, request, spider):
        """Route request through Bright Data API or proxy"""
        # Skip if proxy already set
        if 'proxy' in request.meta or request.meta.get('bright_data_processed'):
            return None
        
        # If using API mode, intercept and make API call
        if self.use_api and self.proxy_type in ['site_unblocker', 'auto']:
            return self._process_via_api(request, spider)
        
        # Otherwise use traditional proxy
        proxy_url = self._select_proxy(request)
        if proxy_url:
            request.meta['proxy'] = proxy_url
            request.meta['proxy_type'] = self._get_proxy_type(proxy_url)
            logger.debug(f'Using proxy: {request.meta["proxy_type"]} for {request.url}')
        
        return None
    
    def _process_via_api(self, request, spider):
        """Process request through Bright Data API with retry logic"""
        max_retries = 3
        base_timeout = 60  # Increased from 30 to 60 seconds
        retry_count = request.meta.get('bright_data_api_retry', 0)
        
        # If we've exceeded retries, fallback to proxy mode if available
        if retry_count >= max_retries:
            logger.warning(
                f'Bright Data API failed after {max_retries} retries for {request.url}. '
                f'Falling back to proxy mode if available.'
            )
            # Try to use traditional proxy as fallback
            if self.site_unblocker_proxy or self.residential_proxy:
                proxy_url = self._select_proxy(request)
                if proxy_url:
                    request.meta['proxy'] = proxy_url
                    request.meta['proxy_type'] = self._get_proxy_type(proxy_url)
                    request.meta.pop('bright_data_api_retry', None)
                    logger.info(f'Using proxy fallback: {request.meta["proxy_type"]} for {request.url}')
                    return None
            # If no proxy available, return None to let Scrapy handle
            return None
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
            
            payload = {
                'zone': self.zone,
                'url': request.url,
                'format': 'raw'
            }
            
            # Add custom headers if needed
            # Convert Scrapy headers (which may be bytes) to string keys/values
            if request.headers:
                headers_dict = {}
                for key, value_list in request.headers.items():
                    # Convert bytes keys to strings
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    # Get first header value and convert bytes to string if needed
                    value = value_list[0] if value_list else b''
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                    headers_dict[key_str] = value_str
                payload['headers'] = headers_dict
            
            # Calculate timeout with exponential backoff
            timeout = base_timeout * (2 ** retry_count)
            timeout = min(timeout, 120)  # Cap at 120 seconds
            
            logger.debug(
                f'Making Bright Data API request for: {request.url} '
                f'(attempt {retry_count + 1}/{max_retries}, timeout={timeout}s)'
            )
            
            # Make API request
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            # Check for API errors in response
            if response.status_code != 200:
                error_msg = f'Bright Data API returned status {response.status_code}'
                try:
                    error_data = response.json()
                    error_msg += f': {error_data}'
                except:
                    error_msg += f': {response.text[:200]}'
                raise Exception(error_msg)
            
            # Create Scrapy TextResponse from API response (TextResponse supports .text attribute)
            scrapy_response = TextResponse(
                url=request.url,
                status=response.status_code,
                headers=response.headers,
                body=response.content,
                request=request,
                encoding='utf-8'  # Default encoding, will be detected from content
            )
            
            request.meta['bright_data_processed'] = True
            request.meta['proxy_type'] = 'site_unblocker_api'
            request.meta.pop('bright_data_api_retry', None)  # Clear retry count on success
            
            logger.debug(f'Bright Data API request successful for: {request.url}')
            return scrapy_response
            
        except requests.exceptions.Timeout as e:
            logger.warning(
                f'Bright Data API timeout for {request.url} (attempt {retry_count + 1}/{max_retries}): {e}'
            )
            # Retry by returning a new request
            return self._retry_api_request(request, retry_count + 1)
            
        except requests.exceptions.RequestException as e:
            logger.warning(
                f'Bright Data API request error for {request.url} (attempt {retry_count + 1}/{max_retries}): {e}'
            )
            # Retry for connection errors
            return self._retry_api_request(request, retry_count + 1)
            
        except Exception as e:
            logger.error(f'Bright Data API request failed for {request.url}: {e}')
            # For other errors, try retry once more
            if retry_count < max_retries - 1:
                return self._retry_api_request(request, retry_count + 1)
            # Return None to let Scrapy handle the error or fallback to proxy
            return None
    
    def _retry_api_request(self, request, retry_count):
        """Retry API request by returning a new request with incremented retry count"""
        logger.info(
            f'Retrying Bright Data API request for {request.url} '
            f'(attempt {retry_count + 1})'
        )
        
        # Create new request with incremented retry count
        new_request = request.copy()
        new_request.meta['bright_data_api_retry'] = retry_count
        new_request.dont_filter = True
        new_request.meta.pop('bright_data_processed', None)  # Reset processed flag
        
        # Return the new request to retry
        return new_request
    
    def process_response(self, request, response, spider):
        """Handle proxy failures and implement failover"""
        proxy_type = request.meta.get('proxy_type', 'unknown')
        
        # Check for proxy-related failures
        if response.status in [403, 407, 502, 503]:
            self._record_proxy_failure(proxy_type)
            
            # If using auto mode and primary proxy failed, try fallback
            if self.proxy_type == 'auto' and proxy_type == 'site_unblocker':
                if self.residential_proxy and self._should_failover(proxy_type):
                    logger.warning(f'Switching from Site Unblocker to Residential Proxy for {request.url}')
                    new_request = request.copy()
                    new_request.meta['proxy'] = self.residential_proxy
                    new_request.meta['proxy_type'] = 'residential'
                    new_request.dont_filter = True
                    return new_request
        
        # Reset failure count on success
        if response.status == 200:
            self._reset_proxy_failures(proxy_type)
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Handle proxy exceptions"""
        proxy_type = request.meta.get('proxy_type', 'unknown')
        self._record_proxy_failure(proxy_type)
        logger.error(f'Proxy exception ({proxy_type}): {exception}')
        return None
    
    def _select_proxy(self, request):
        """Select appropriate proxy based on configuration"""
        if self.proxy_type == 'residential':
            return self.residential_proxy or self.site_unblocker_proxy
        elif self.proxy_type == 'site_unblocker':
            return self.site_unblocker_proxy or self.residential_proxy
        elif self.proxy_type == 'auto':
            # Try site unblocker first, fallback to residential
            if self.site_unblocker_proxy and not self._should_failover('site_unblocker'):
                return self.site_unblocker_proxy
            elif self.residential_proxy:
                return self.residential_proxy
            else:
                return self.site_unblocker_proxy
        else:
            # Default to site unblocker
            return self.site_unblocker_proxy or self.residential_proxy
    
    def _get_proxy_type(self, proxy_url):
        """Determine proxy type from URL"""
        if 'lum-superproxy.io' in proxy_url or 'zproxy' in proxy_url:
            return 'site_unblocker'
        elif 'brd.superproxy.io' in proxy_url or 'brd-customer' in proxy_url:
            return 'residential'
        return 'unknown'
    
    def _record_proxy_failure(self, proxy_type):
        """Record proxy failure for failover logic"""
        if proxy_type not in self.proxy_failures:
            self.proxy_failures[proxy_type] = 0
        self.proxy_failures[proxy_type] += 1
    
    def _reset_proxy_failures(self, proxy_type):
        """Reset failure count on success"""
        if proxy_type in self.proxy_failures:
            self.proxy_failures[proxy_type] = 0
    
    def _should_failover(self, proxy_type):
        """Check if failover should occur"""
        failures = self.proxy_failures.get(proxy_type, 0)
        return failures >= self.max_failures_before_switch


class ExponentialBackoffMiddleware:
    """
    Middleware for handling 429 (Too Many Requests) responses with exponential backoff.
    """
    
    def __init__(self, settings):
        self.base_delay = settings.getfloat('BACKOFF_BASE_DELAY', 1.0)
        self.max_retries = settings.getint('BACKOFF_MAX_RETRIES', 5)
        self.max_wait = settings.getfloat('BACKOFF_MAX_WAIT', 300.0)
        
        logger.info(f'ExponentialBackoffMiddleware initialized: base_delay={self.base_delay}s, max_retries={self.max_retries}')
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def process_response(self, request, response, spider):
        """Handle 429 responses with exponential backoff"""
        if response.status == 429:
            retry_count = request.meta.get('retry_count', 0)
            
            if retry_count >= self.max_retries:
                logger.error(f'Max retries ({self.max_retries}) exceeded for {request.url}')
                return response
            
            # Check for Retry-After header
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    wait_time = float(retry_after)
                except ValueError:
                    wait_time = self._calculate_backoff(retry_count)
            else:
                wait_time = self._calculate_backoff(retry_count)
            
            # Cap wait time at max_wait
            wait_time = min(wait_time, self.max_wait)
            
            logger.warning(
                f'429 Too Many Requests for {request.url}. '
                f'Retrying in {wait_time:.2f}s (attempt {retry_count + 1}/{self.max_retries})'
            )
            
            # Create new request with incremented retry count
            new_request = request.copy()
            new_request.meta['retry_count'] = retry_count + 1
            new_request.dont_filter = True
            
            # Schedule retry after wait time
            spider.crawler.engine.schedule(new_request, spider)
            
            # Ignore current response
            raise IgnoreRequest(f'429 response, retrying after {wait_time}s')
        
        return response
    
    def _calculate_backoff(self, retry_count):
        """Calculate exponential backoff delay"""
        wait_time = self.base_delay * (2 ** retry_count)
        return wait_time


class ProxyLoggingMiddleware:
    """
    Middleware for logging proxy usage statistics and performance metrics.
    """
    
    def __init__(self, settings):
        self.stats = {
            'requests': {},
            'responses': {},
            'errors': {},
            'response_times': {},
        }
        self.log_interval = settings.getint('PROXY_LOG_INTERVAL', 100)  # Log every N requests
        self.request_count = 0
        
        logger.info('ProxyLoggingMiddleware initialized')
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.settings)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def process_request(self, request, spider):
        """Log request initiation"""
        proxy_type = request.meta.get('proxy_type', 'none')
        start_time = time.time()
        request.meta['_proxy_start_time'] = start_time
        
        # Update stats
        if proxy_type not in self.stats['requests']:
            self.stats['requests'][proxy_type] = 0
        self.stats['requests'][proxy_type] += 1
        
        self.request_count += 1
        
        return None
    
    def process_response(self, request, response, spider):
        """Log successful response"""
        proxy_type = request.meta.get('proxy_type', 'none')
        start_time = request.meta.get('_proxy_start_time', time.time())
        response_time = time.time() - start_time
        
        # Update stats
        if proxy_type not in self.stats['responses']:
            self.stats['responses'][proxy_type] = 0
            self.stats['response_times'][proxy_type] = []
        
        self.stats['responses'][proxy_type] += 1
        self.stats['response_times'][proxy_type].append(response_time)
        
        # Log periodically
        if self.request_count % self.log_interval == 0:
            self._log_stats()
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Log exceptions"""
        proxy_type = request.meta.get('proxy_type', 'none')
        
        if proxy_type not in self.stats['errors']:
            self.stats['errors'][proxy_type] = 0
        self.stats['errors'][proxy_type] += 1
        
        return None
    
    def spider_closed(self, spider, reason):
        """Log final statistics when spider closes"""
        self._log_stats(final=True)
    
    def _log_stats(self, final=False):
        """Log proxy usage statistics"""
        stats_summary = {
            'timestamp': time.time(),
            'final': final,
            'proxy_stats': {}
        }
        
        for proxy_type in set(list(self.stats['requests'].keys()) + 
                             list(self.stats['responses'].keys()) + 
                             list(self.stats['errors'].keys())):
            requests = self.stats['requests'].get(proxy_type, 0)
            responses = self.stats['responses'].get(proxy_type, 0)
            errors = self.stats['errors'].get(proxy_type, 0)
            
            response_times = self.stats['response_times'].get(proxy_type, [])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            success_rate = (responses / requests * 100) if requests > 0 else 0
            
            stats_summary['proxy_stats'][proxy_type] = {
                'total_requests': requests,
                'successful_responses': responses,
                'errors': errors,
                'success_rate': round(success_rate, 2),
                'avg_response_time': round(avg_response_time, 3),
            }
        
        logger.info(f'Proxy Statistics: {json.dumps(stats_summary, indent=2)}')

