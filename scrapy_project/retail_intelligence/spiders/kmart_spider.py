"""
Kmart spider with API discovery and product scraping.
"""
import scrapy
import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from retail_intelligence.items import ProductItem
from retail_intelligence.utils.api_discovery import APIDiscovery

logger = logging.getLogger(__name__)


class KmartSpider(scrapy.Spider):
    """
    Spider for scraping Kmart product data.
    Uses API discovery to find hidden endpoints before scraping HTML.
    """
    
    name = 'kmart'
    allowed_domains = ['kmart.com']
    
    def __init__(self, *args, **kwargs):
        super(KmartSpider, self).__init__(*args, **kwargs)
        self.api_discovery = APIDiscovery(browser_type='chrome110')
        self.start_urls = kwargs.get('start_urls', '').split(',') if kwargs.get('start_urls') else []
        
        # Default start URLs if none provided
        if not self.start_urls:
            self.start_urls = [
                'https://www.kmart.com/search=laptop',
                'https://www.kmart.com/search=smartphone',
            ]
    
    async def start(self):
        """Generate initial requests (async method for Scrapy 2.13+)"""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={'dont_cache': False}
            )
    
    def parse_search_results(self, response):
        """Parse Kmart search results page"""
        logger.info(f'Parsing search results page: {response.url} (status: {response.status})')
        
        if response.status != 200:
            logger.warning(f'Non-200 status code {response.status} for {response.url}')
            return
        
        # Debug: Log response info
        logger.info(f'Response size: {len(response.text)} bytes')
        logger.debug(f'Response headers: {dict(response.headers)}')
        
        # Check for redirects
        if response.url != response.request.url:
            logger.warning(f'Redirect detected: {response.request.url} -> {response.url}')
        
        # Check if we got any links at all
        all_links_count = len(response.css('a::attr(href)').getall())
        logger.info(f'Total links found on page: {all_links_count}')
        
        # Check if page is mostly empty (might be JS-rendered or error page)
        if len(response.text) < 5000:
            logger.warning(f'Response is very small ({len(response.text)} bytes). Page might be JavaScript-rendered, show an error, or redirect.')
            # Log a sample of the response
            sample = response.text[:500] if len(response.text) > 500 else response.text
            logger.debug(f'Response sample: {sample}')
        
        # Try API discovery first
        api_endpoints = self.api_discovery.discover_from_html(
            response.text,
            response.url,
            site='kmart'
        )
        
        # Extract product links from search results - try multiple strategies
        product_links = []
        
        # Strategy 1: CSS selectors (try many variations)
        selectors = [
            # Data attribute based
            'div[data-product-id] a::attr(href)',
            'a[data-product-id]::attr(href)',
            'div[data-item-id] a::attr(href)',
            'a[data-item-id]::attr(href)',
            # Class-based
            'div.product-tile a::attr(href)',
            'div.product-item a::attr(href)',
            'div.product-card a::attr(href)',
            'a.product-link::attr(href)',
            'a.product-tile-link::attr(href)',
            'div[class*="ProductTile"] a::attr(href)',
            'div[class*="ProductCard"] a::attr(href)',
            'div[class*="product"] a::attr(href)',
            # URL pattern based
            'a[href*="/product/"]::attr(href)',
            'a[href*="/p-"]::attr(href)',
            'a[href*="/ip/"]::attr(href)',
            'a[href*="/item/"]::attr(href)',
            # Generic link patterns
            'article a::attr(href)',
            'section.product a::attr(href)',
            'li.product a::attr(href)',
        ]
        
        for selector in selectors:
            links = response.css(selector).getall()
            if links:
                product_links.extend(links)
                logger.debug(f'Found {len(links)} links using selector: {selector}')
        
        # Strategy 2: Extract all links and filter by URL pattern (more aggressive)
        if not product_links:
            logger.info('No links found with CSS selectors, trying regex extraction...')
            # Extract all <a> tags with href
            all_links = response.css('a::attr(href)').getall()
            logger.debug(f'Total <a> tags with href: {len(all_links)}')
            if all_links:
                logger.debug(f'Sample links (first 10): {all_links[:10]}')
            
            # Filter for potential product URLs
            product_patterns = [
                r'/product/',
                r'/p-',
                r'/ip/',
                r'/item/',
                r'/dp/',
                r'kmart\.com/.*product',
            ]
            for link in all_links:
                if link and any(re.search(pattern, link, re.IGNORECASE) for pattern in product_patterns):
                    product_links.append(link)
            logger.info(f'Found {len(product_links)} links using regex extraction')
        
        # Strategy 3: Extract ALL links and filter intelligently (most aggressive)
        if not product_links:
            logger.info('Trying to extract all links and filter for products...')
            all_links = response.css('a::attr(href)').getall()
            logger.debug(f'Found {len(all_links)} total links on page')
            
            if len(all_links) == 0:
                logger.warning('No <a> tags found at all! Page might be JavaScript-rendered.')
                # Try to find any href attributes in other tags
                all_hrefs = response.css('[href]::attr(href)').getall()
                logger.debug(f'Found {len(all_hrefs)} total href attributes (all tags)')
                if all_hrefs:
                    logger.debug(f'Sample hrefs (first 10): {all_hrefs[:10]}')
            
            # Filter for product-like URLs
            for link in all_links:
                if not link or len(link) < 10:  # Skip very short links
                    continue
                link_lower = link.lower()
                # Look for product indicators
                if any(indicator in link_lower for indicator in [
                    '/product/', '/p-', '/ip/', '/item/', '/dp/',
                    'product', 'item', 'detail'
                ]):
                    # But exclude non-product pages
                    if not any(skip in link_lower for skip in [
                        '/search', '/browse', '/category', '/account', 
                        '/cart', '/checkout', '/help', '/stores'
                    ]):
                        product_links.append(link)
        
        # Strategy 4: Look for links in JSON-LD or script tags
        if not product_links:
            logger.info('Trying to extract links from JSON-LD or embedded data...')
            # Look for product URLs in script tags or data attributes
            script_content = response.css('script::text').getall()
            for script in script_content:
                # Look for URLs in JSON
                url_matches = re.findall(r'https?://[^\s"\'<>]+kmart\.com[^\s"\'<>]*(?:product|/p-|/ip/)[^\s"\'<>]*', script)
                product_links.extend(url_matches)
        
        # Remove duplicates and clean links
        seen = set()
        unique_links = []
        for link in product_links:
            if not link:
                continue
            # Normalize link
            link = link.strip()
            # Remove fragments and query params for deduplication
            clean_link = link.split('?')[0].split('#')[0]
            if clean_link and clean_link not in seen:
                seen.add(clean_link)
                unique_links.append(link)
        
        logger.info(f'Found {len(unique_links)} unique product links on {response.url}')
        
        # Filter for product links with more flexible patterns
        product_count = 0
        for link in unique_links:
            if not link:
                continue
            
            # More flexible product link detection
            is_product_link = (
                '/product/' in link.lower() or
                '/p-' in link.lower() or
                '/ip/' in link.lower() or
                '/item/' in link.lower() or
                'kmart.com/product/' in link.lower() or
                re.search(r'/p-[a-z0-9-]+', link, re.IGNORECASE) or
                re.search(r'/product/[a-z0-9-]+', link, re.IGNORECASE)
            )
            
            skip_patterns = [
                '/search',
                '/browse',
                '/category',
                '/account',
                '/cart',
                '/checkout',
                '/help',
                '/stores',
                '/about',
                'javascript:',
                'mailto:',
                'tel:',
                '#',
                'void(0)',
            ]
            
            should_skip = any(pattern in link.lower() for pattern in skip_patterns)
            
            # Additional check: skip if it's clearly not a product (too short, no meaningful path)
            if len(link.split('/')) < 4:  # Very short URLs are likely not products
                should_skip = True
            
            if is_product_link and not should_skip:
                # Convert relative URLs to absolute
                if link.startswith('/'):
                    product_url = response.urljoin(link)
                elif not link.startswith('http'):
                    product_url = response.urljoin('/' + link.lstrip('/'))
                else:
                    product_url = link
                
                # Clean up URL (remove query parameters that might cause duplicates)
                if '?' in product_url:
                    product_url = product_url.split('?')[0]
                
                product_count += 1
                logger.debug(f'Yielding product request {product_count}: {product_url}')
                yield scrapy.Request(
                    url=product_url,
                    callback=self.parse_product,
                    meta={'dont_cache': False}
                )
        
        logger.info(f'Yielded {product_count} product requests from search results')
        
        # If still no products found, save HTML for debugging
        if product_count == 0 and 'page=' not in response.url:
            try:
                import os
                debug_dir = os.path.join(os.getcwd(), 'debug_html')
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, 'kmart_search_sample.html')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.warning(f'No product links found. Saved HTML sample ({len(response.text)} bytes) to {debug_file} for inspection')
                
                # Log more details about the page structure
                logger.warning(f'Response URL: {response.url}')
                logger.warning(f'Response status: {response.status}')
                logger.warning(f'Total <a> tags: {len(response.css("a").getall())}')
                logger.warning(f'Total <div> tags: {len(response.css("div").getall())}')
                logger.warning(f'Total <script> tags: {len(response.css("script").getall())}')
                logger.warning(f'Sample HTML structure (first 3000 chars):\n{response.text[:3000]}')
                
                # Check for common JavaScript framework indicators
                if 'react' in response.text.lower() or 'vue' in response.text.lower() or 'angular' in response.text.lower():
                    logger.warning('Page appears to be JavaScript-rendered (React/Vue/Angular detected)')
            except Exception as e:
                logger.warning(f'No product links found. Could not save debug HTML: {e}')
                logger.warning(f'Sample HTML structure (first 2000 chars): {response.text[:2000]}')
        
        # Follow pagination
        next_page = None
        pagination_selectors = [
            'a[aria-label="Next"]::attr(href)',
            'a.pagination-next::attr(href)',
            'a[class*="next"]::attr(href)',
            'button[aria-label*="Next"]::attr(data-href)',
        ]
        
        for selector in pagination_selectors:
            next_page = response.css(selector).get()
            if next_page:
                logger.info(f'Found next page link: {next_page}')
                break
        
        if not next_page:
            # Try URL-based pagination
            parsed = urlparse(response.url)
            params = parse_qs(parsed.query)
            current_page = int(params.get('page', ['1'])[0])
            if current_page < 50:
                next_page_num = current_page + 1
                params['page'] = [str(next_page_num)]
                new_query = urlencode(params, doseq=True)
                next_page = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, new_query, parsed.fragment
                ))
        
        if next_page:
            logger.info(f'Following pagination to: {next_page}')
            yield response.follow(next_page, callback=self.parse_search_results)
    
    def parse_product(self, response):
        """Parse Kmart product detail page"""
        logger.debug(f'Parsing product page: {response.url}')
        item = ProductItem()
        
        # Extract product ID from URL
        product_id_match = re.search(r'/product/([^/?]+)', response.url)
        if not product_id_match:
            product_id_match = re.search(r'/p-([^/?]+)', response.url)
        if not product_id_match:
            product_id_match = re.search(r'/([A-Z0-9-]{8,})', response.url)
        
        if product_id_match:
            item['product_id'] = f"kmart_{product_id_match.group(1)}"
        else:
            # Fallback: extract from page
            product_id_element = response.css('div[data-product-id]::attr(data-product-id)').get()
            if product_id_element:
                item['product_id'] = f"kmart_{product_id_element}"
            else:
                item['product_id'] = f"kmart_{response.url.split('/')[-1].split('?')[0]}"
        
        item['site'] = 'kmart'
        item['url'] = response.url
        
        # Extract product details
        item['title'] = response.css('h1.product-title::text').get() or \
                       response.css('h1[itemprop="name"]::text').get() or \
                       response.css('h1::text').get()
        
        # Brand extraction
        brand = response.css('span.brand-name::text').get() or \
                response.css('a.brand-link::text').get() or \
                response.css('div[itemprop="brand"] span::text').get()
        if brand:
            item['brand'] = brand.strip()
        
        # Model/SKU extraction
        sku = response.css('span.product-number::text').get() or \
              response.css('div[itemprop="sku"]::text').get() or \
              response.css('span.sku::text').get()
        if sku:
            item['sku'] = sku.strip()
            item['model'] = sku.strip()
        
        # Category
        category = response.css('nav.breadcrumb a::text').getall()
        if category:
            item['category'] = ' > '.join(category[-2:])  # Last 2 levels
        
        # Price extraction
        price_selectors = [
            'span.product-price::text',
            'span[itemprop="price"]::text',
            'div.price-wrapper span::text',
            'span.regular-price::text',
            'span.sale-price::text',
            'span.price-current::text',
        ]
        for selector in price_selectors:
            price = response.css(selector).get()
            if price:
                item['price'] = price
                break
        
        # Currency (Kmart US uses USD)
        item['currency'] = 'USD'
        
        # Rating
        rating = response.css('span[itemprop="ratingValue"]::text').get()
        if not rating:
            rating = response.css('div.rating-stars::attr(data-rating)').get()
        if rating:
            item['rating'] = rating
        
        # Review count
        review_count = response.css('span[itemprop="reviewCount"]::text').get()
        if not review_count:
            review_count = response.css('a.reviews-link::text').re_first(r'(\d+)')
        if review_count:
            item['review_count'] = review_count
        
        # Availability
        availability = response.css('div.availability span::text').get()
        if not availability:
            availability = response.css('span.in-stock::text').get() or \
                          response.css('span.out-of-stock::text').get()
        if availability:
            item['availability'] = availability.strip()
        
        # Description
        description_parts = response.css('div[itemprop="description"] p::text').getall()
        if not description_parts:
            description_parts = response.css('div.product-description p::text').getall()
        if description_parts:
            item['description'] = ' '.join(description_parts)
        
        # Images
        image_urls = response.css('img[itemprop="image"]::attr(src)').getall()
        if not image_urls:
            image_urls = response.css('div.product-image img::attr(src)').getall()
        if not image_urls:
            image_urls = response.css('img.product-image::attr(src)').getall()
        item['image_urls'] = image_urls
        
        # Metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['raw_html'] = response.text
        
        yield item
    
    def closed(self, reason):
        """Cleanup when spider closes"""
        self.api_discovery.close()
        logger.info(f'Kmart spider closed: {reason}')

