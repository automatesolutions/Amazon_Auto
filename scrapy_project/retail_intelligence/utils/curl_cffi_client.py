"""
curl_cffi client for TLS/JA3 fingerprint impersonation.
Mimics Chrome/Firefox TLS fingerprints for direct API calls.
"""
import logging
from curl_cffi import requests
from curl_cffi.requests import BrowserType

logger = logging.getLogger(__name__)


class CurlCffiClient:
    """
    HTTP client using curl_cffi for TLS/JA3 fingerprint impersonation.
    Bypasses fingerprint-based bot detection by mimicking real browser fingerprints.
    """
    
    # Supported browser types for fingerprint impersonation
    BROWSER_TYPES = {
        'chrome': BrowserType.chrome110,
        'chrome110': BrowserType.chrome110,
        'chrome120': BrowserType.chrome120,
        'firefox': BrowserType.firefox133,
        'firefox109': BrowserType.firefox133,  # Legacy alias, now uses firefox133
        'firefox133': BrowserType.firefox133,
        'safari': BrowserType.safari15_3,
    }
    
    def __init__(self, browser_type='chrome110', timeout=30, verify=True):
        """
        Initialize curl_cffi client.
        
        Args:
            browser_type: Browser fingerprint to mimic (chrome110, firefox133, etc.)
            timeout: Request timeout in seconds
            verify: Verify SSL certificates
        """
        self.browser_type = self.BROWSER_TYPES.get(browser_type.lower(), BrowserType.chrome110)
        self.timeout = timeout
        self.verify = verify
        self.session = None
        
        logger.info(f'CurlCffiClient initialized with browser type: {browser_type}')
    
    def get_session(self):
        """Get or create requests session"""
        if self.session is None:
            self.session = requests.Session()
        return self.session
    
    def get(self, url, headers=None, params=None, **kwargs):
        """
        Perform GET request with TLS fingerprint impersonation.
        
        Args:
            url: Target URL
            headers: Custom headers
            params: URL parameters
            **kwargs: Additional arguments passed to requests.get
        
        Returns:
            Response object
        """
        session = self.get_session()
        
        default_headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': self._get_user_agent(),
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            response = session.get(
                url,
                headers=default_headers,
                params=params,
                timeout=self.timeout,
                verify=self.verify,
                impersonate=self.browser_type,
                **kwargs
            )
            
            logger.debug(f'GET {url} - Status: {response.status_code}')
            return response
            
        except Exception as e:
            logger.error(f'GET request failed for {url}: {e}')
            raise
    
    def post(self, url, headers=None, json_data=None, data=None, **kwargs):
        """
        Perform POST request with TLS fingerprint impersonation.
        
        Args:
            url: Target URL
            headers: Custom headers
            json_data: JSON payload
            data: Form data payload
            **kwargs: Additional arguments passed to requests.post
        
        Returns:
            Response object
        """
        session = self.get_session()
        
        default_headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'User-Agent': self._get_user_agent(),
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            response = session.post(
                url,
                headers=default_headers,
                json=json_data,
                data=data,
                timeout=self.timeout,
                verify=self.verify,
                impersonate=self.browser_type,
                **kwargs
            )
            
            logger.debug(f'POST {url} - Status: {response.status_code}')
            return response
            
        except Exception as e:
            logger.error(f'POST request failed for {url}: {e}')
            raise
    
    def _get_user_agent(self):
        """Get appropriate User-Agent string for browser type"""
        user_agents = {
            BrowserType.chrome110: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            BrowserType.chrome120: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            BrowserType.firefox133: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
            BrowserType.safari15_3: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15',
        }
        return user_agents.get(self.browser_type, user_agents[BrowserType.chrome110])
    
    def close(self):
        """Close session"""
        if self.session:
            self.session.close()
            self.session = None

