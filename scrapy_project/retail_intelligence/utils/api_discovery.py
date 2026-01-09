"""
API Discovery module for identifying and intercepting hidden JSON APIs.
Analyzes Network Tab data (Fetch/XHR requests) to extract API endpoints and schemas.
"""
import logging
import re
import json
from urllib.parse import urlparse, parse_qs
from retail_intelligence.utils.curl_cffi_client import CurlCffiClient

logger = logging.getLogger(__name__)


class APIDiscovery:
    """
    Discovers hidden JSON APIs by analyzing network requests.
    Can parse Network Tab exports or analyze page HTML for API endpoints.
    """
    
    def __init__(self, browser_type='chrome110'):
        """
        Initialize API Discovery.
        
        Args:
            browser_type: Browser type for curl_cffi client
        """
        self.client = CurlCffiClient(browser_type=browser_type)
        self.discovered_apis = {}  # Cache discovered endpoints
        self.api_patterns = {
            'amazon': [
                r'api\.amazon\.com',
                r'atv-.*\.amazon\.com',
                r'completion\.amazon\.com',
                r'/api/.*',
                r'/gp/product/.*/dp/',
            ],
            'walmart': [
                r'walmart\.com/.*api.*',
                r'api\.walmart\.com',
                r'/api/.*',
                r'/product/.*',
            ],
        }
    
    def discover_from_network_tab(self, network_data, site='amazon'):
        """
        Discover APIs from Network Tab export (HAR format or list of URLs).
        
        Args:
            network_data: List of request URLs or HAR format data
            site: Target site (amazon or walmart)
        
        Returns:
            List of discovered API endpoints with metadata
        """
        discovered = []
        
        # Handle HAR format
        if isinstance(network_data, dict) and 'log' in network_data:
            entries = network_data['log'].get('entries', [])
            for entry in entries:
                url = entry['request'].get('url', '')
                if self._is_api_endpoint(url, site):
                    api_info = self._extract_api_info(url, entry)
                    if api_info:  # Only append if valid
                        discovered.append(api_info)
        
        # Handle list of URLs
        elif isinstance(network_data, list):
            for url in network_data:
                if isinstance(url, str) and self._is_api_endpoint(url, site):
                    api_info = self._extract_api_info(url)
                    if api_info:  # Only append if valid
                        discovered.append(api_info)
        
        # Cache discovered APIs
        for api in discovered:
            cache_key = f"{site}:{api['endpoint']}"
            self.discovered_apis[cache_key] = api
        
        logger.info(f'Discovered {len(discovered)} API endpoints for {site}')
        return discovered
    
    def discover_from_html(self, html_content, base_url, site='amazon'):
        """
        Discover API endpoints by analyzing HTML content (embedded JSON, script tags, etc.).
        
        Args:
            html_content: HTML content to analyze
            base_url: Base URL of the page
            site: Target site (amazon or walmart)
        
        Returns:
            List of discovered API endpoints
        """
        discovered = []
        
        # Look for embedded JSON data
        json_patterns = [
            r'window\.__APOLLO_STATE__\s*=\s*({.+?});',
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'data-product="({.+?})"',
            r'data-product-info="({.+?})"',
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, html_content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match.group(1))
                    # Extract potential API endpoints from JSON
                    endpoints = self._extract_endpoints_from_json(data, base_url, site)
                    discovered.extend(endpoints)
                except json.JSONDecodeError:
                    continue
        
        # Look for API URLs in script tags
        script_pattern = r'<script[^>]*>.*?(https?://[^\s"\'<>]+api[^\s"\'<>]+).*?</script>'
        script_matches = re.finditer(script_pattern, html_content, re.DOTALL | re.IGNORECASE)
        for match in script_matches:
            url = match.group(1)
            if self._is_api_endpoint(url, site):
                api_info = self._extract_api_info(url)
                if api_info:  # Only append if valid
                    discovered.append(api_info)
        
        logger.info(f'Discovered {len(discovered)} API endpoints from HTML for {site}')
        return discovered
    
    def fetch_api_data(self, endpoint, params=None, headers=None):
        """
        Fetch data from discovered API endpoint using curl_cffi client.
        
        Args:
            endpoint: API endpoint URL
            params: Query parameters
            headers: Custom headers
        
        Returns:
            JSON response data or None if request fails
        """
        try:
            response = self.client.get(endpoint, params=params, headers=headers)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    logger.warning(f'Non-JSON response from {endpoint}')
                    return response.text
            else:
                logger.warning(f'API request failed: {endpoint} - Status: {response.status_code}')
                return None
                
        except Exception as e:
            logger.error(f'Failed to fetch API data from {endpoint}: {e}')
            return None
    
    def _is_api_endpoint(self, url, site):
        """Check if URL matches known API patterns for the site"""
        if not url:
            return False
        
        patterns = self.api_patterns.get(site, [])
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        # Check for common API indicators
        api_indicators = ['/api/', '/api/v', 'api.', '.json', '?format=json']
        if any(indicator in url.lower() for indicator in api_indicators):
            return True
        
        return False
    
    def _extract_api_info(self, url, har_entry=None):
        """Extract API endpoint information"""
        try:
            parsed = urlparse(url)
        except (ValueError, Exception) as e:
            # Skip invalid URLs (e.g., IPv6 URLs, malformed URLs)
            logger.debug(f'Skipping invalid URL: {url} - {e}')
            return None
        
        api_info = {
            'endpoint': url,
            'base_url': f'{parsed.scheme}://{parsed.netloc}',
            'path': parsed.path,
            'params': parse_qs(parsed.query),
            'method': 'GET',
        }
        
        if har_entry:
            api_info['method'] = har_entry.get('request', {}).get('method', 'GET')
            api_info['headers'] = har_entry.get('request', {}).get('headers', [])
        
        return api_info
    
    def _extract_endpoints_from_json(self, data, base_url, site):
        """Recursively extract API endpoints from JSON data"""
        endpoints = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and value.startswith('http'):
                    if self._is_api_endpoint(value, site):
                        api_info = self._extract_api_info(value)
                        if api_info:  # Only append if valid
                            endpoints.append(api_info)
                elif isinstance(value, (dict, list)):
                    endpoints.extend(self._extract_endpoints_from_json(value, base_url, site))
        
        elif isinstance(data, list):
            for item in data:
                endpoints.extend(self._extract_endpoints_from_json(item, base_url, site))
        
        return endpoints
    
    def get_cached_endpoint(self, site, endpoint_pattern):
        """Get cached API endpoint matching pattern"""
        cache_key = f"{site}:{endpoint_pattern}"
        return self.discovered_apis.get(cache_key)
    
    def close(self):
        """Close client connection"""
        self.client.close()

