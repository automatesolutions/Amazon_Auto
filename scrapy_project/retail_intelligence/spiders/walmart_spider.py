"""
Walmart spider with API discovery and product scraping.
"""
import scrapy
import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from retail_intelligence.items import ProductItem
from retail_intelligence.utils.api_discovery import APIDiscovery

logger = logging.getLogger(__name__)


class WalmartSpider(scrapy.Spider):
    """
    Spider for scraping Walmart product data.
    Uses API discovery to find hidden endpoints before scraping HTML.
    """
    
    name = 'walmart'
    allowed_domains = ['walmart.com', 'walmart.ca']
    
    def __init__(self, *args, **kwargs):
        super(WalmartSpider, self).__init__(*args, **kwargs)
        self.api_discovery = APIDiscovery(browser_type='chrome110')
        self.start_urls = kwargs.get('start_urls', '').split(',') if kwargs.get('start_urls') else []
        
        # Default start URLs if none provided
        if not self.start_urls:
            self.start_urls = [
                'https://www.walmart.com/search?q=laptop',
                'https://www.walmart.com/search?q=smartphone',
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
        """Parse Walmart search results page"""
        logger.info(f'Parsing search results page: {response.url} (status: {response.status})')
        
        # Check if we got a valid response
        if response.status != 200:
            logger.warning(f'Non-200 status code {response.status} for {response.url}')
            return
        
        # Log response size for debugging
        logger.debug(f'Response size: {len(response.text)} bytes')
        
        # Try API discovery first
        api_endpoints = self.api_discovery.discover_from_html(
            response.text,
            response.url,
            site='walmart'
        )
        
        # Extract product links from search results - try ALL selectors and combine
        product_links = []
        
        # Try various selectors for Walmart product links (try ALL, don't break early)
        selectors = [
            'div[data-testid="item-stack"] a::attr(href)',
            'a[data-testid="product-title"]::attr(href)',
            'div[data-automation-id="product-title"] a::attr(href)',
            'a[href*="/ip/"]::attr(href)',
            'div[class*="search-result"] a[href*="/ip/"]::attr(href)',
            'div[class*="ProductTile"] a::attr(href)',
            'div[class*="product-tile"] a::attr(href)',
            'a[href*="/product/"]::attr(href)',
            'div[data-testid*="product"] a::attr(href)',
            'div[class*="item"] a[href*="/ip/"]::attr(href)',
        ]
        
        for selector in selectors:
            links = response.css(selector).getall()
            if links:
                product_links.extend(links)
                logger.debug(f'Found {len(links)} links using selector: {selector}')
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in product_links:
            if link and link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        logger.info(f'Found {len(unique_links)} unique product links on {response.url}')
        
        # Filter for product links - Walmart product URLs typically contain /ip/ or /product/
        product_count = 0
        filtered_out = 0
        
        for link in unique_links:
            if not link:
                continue
                
            # Check if this looks like a product link
            # Walmart product URLs: /ip/ProductName/123456 or /product/...
            is_product_link = (
                '/ip/' in link or 
                '/product/' in link or
                link.startswith('/ip/') or
                'walmart.com/ip/' in link
            )
            
            # Skip non-product links (like search, category, etc.)
            skip_patterns = [
                '/search',
                '/browse',
                '/category',
                '/c/',
                '/cp/',
                '/account',
                '/cart',
                '/checkout',
                'javascript:',
                '#',
            ]
            
            should_skip = any(pattern in link.lower() for pattern in skip_patterns)
            
            if is_product_link and not should_skip:
                # Convert relative URLs to absolute
                if link.startswith('/'):
                    product_url = response.urljoin(link)
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
            else:
                filtered_out += 1
                logger.debug(f'Filtered out non-product link: {link[:80]}...')
        
        logger.info(f'Yielded {product_count} product requests from search results (filtered out {filtered_out} non-product links)')
        
        # Follow pagination - try multiple selectors and patterns
        next_page = None
        pagination_selectors = [
            'a[data-testid="next-page"]::attr(href)',
            'nav[aria-label="pagination"] a[aria-label="Next"]::attr(href)',
            'a[aria-label="Next"]::attr(href)',
            'a[data-automation-id="pagination-next"]::attr(href)',
            'a.paginator-btn[aria-label="Next"]::attr(href)',
            'a[aria-label*="Next"]::attr(href)',
            'button[aria-label*="Next"]::attr(data-href)',
            'a[class*="next"]::attr(href)',
            'a[class*="pagination-next"]::attr(href)',
        ]
        
        for selector in pagination_selectors:
            next_page = response.css(selector).get()
            if next_page:
                logger.info(f'Found next page link using selector "{selector}": {next_page}')
                break
        
        # Also try to find pagination in URL parameters (page=2, etc.)
        if not next_page:
            # Check current page number
            parsed = urlparse(response.url)
            params = parse_qs(parsed.query)
            current_page = int(params.get('page', ['1'])[0])
            next_page_num = current_page + 1
            
            # Try to construct next page URL
            params['page'] = [str(next_page_num)]
            new_query = urlencode(params, doseq=True)
            next_page_url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))
            
            # Only use constructed URL if we're on a reasonable page number
            if current_page < 50:  # Reasonable limit
                next_page = next_page_url
                logger.info(f'Constructed next page URL: {next_page}')
        
        if next_page:
            logger.info(f'Following pagination to: {next_page}')
            yield response.follow(next_page, callback=self.parse_search_results)
        else:
            logger.info('No pagination link found - reached end of results')
    
    def parse_product(self, response):
        """Parse Walmart product detail page"""
        logger.debug(f'Parsing product page: {response.url}')
        item = ProductItem()
        
        # Extract product ID from URL - handle multiple URL patterns
        product_id_match = re.search(r'/ip/([^/?]+)', response.url)
        if not product_id_match:
            # Try /product/ pattern
            product_id_match = re.search(r'/product/([^/?]+)', response.url)
        if not product_id_match:
            # Try to extract any product identifier
            product_id_match = re.search(r'/([A-Z0-9]{8,})', response.url)
        
        if product_id_match:
            item['product_id'] = product_id_match.group(1)
        else:
            # Fallback: extract from page
            product_id_element = response.css('span[itemprop="productID"]::text').get()
            if product_id_element:
                item['product_id'] = product_id_element
            else:
                # Last resort: use URL as product ID
                item['product_id'] = response.url.split('/')[-1].split('?')[0]
        
        item['site'] = 'walmart'
        item['url'] = response.url
        
        # Extract product details
        item['title'] = response.css('h1[itemprop="name"]::text').get() or \
                       response.css('h1.prod-ProductTitle::text').get() or \
                       response.css('h1::text').get()
        
        # Price extraction - prioritize actual selling price
        price = None
        price_selectors = [
            'span[itemprop="price"]::text',
            'span.price-current::text',
            'div[data-testid="price"] span::text',
            'span.price-characteristic::text',
            'span[data-automation-id="product-price"]::text',
        ]
        for selector in price_selectors:
            price_text = response.css(selector).get()
            if price_text:
                # Skip "from" prices
                if 'from' not in price_text.lower() and 'starting at' not in price_text.lower():
                    price = price_text
                    break
        
        # Validate price is reasonable
        if price:
            price_match = re.search(r'[\d,]+\.?\d*', price.replace(',', ''))
            if price_match:
                try:
                    price_value = float(price_match.group().replace(',', ''))
                    # Check if price seems too low for expensive items
                    title_lower = (item.get('title') or '').lower()
                    expensive_keywords = ['laptop', 'computer', 'gaming', 'macbook', 'thinkpad', 
                                         'iphone', 'samsung', 'tablet', 'ipad', 'monitor', 'tv']
                    is_expensive_item = any(keyword in title_lower for keyword in expensive_keywords)
                    
                    if is_expensive_item and price_value < 10:
                        logger.warning(f'Price ${price_value} seems too low for expensive item: {item.get("title")}')
                        # Try alternative price selectors
                        alt_price = response.css('span[data-testid="price"]::text').get()
                        if alt_price:
                            alt_match = re.search(r'[\d,]+\.?\d*', alt_price.replace(',', ''))
                            if alt_match:
                                alt_value = float(alt_match.group().replace(',', ''))
                                if alt_value >= 10:
                                    price_value = alt_value
                                    price = str(price_value)
                                    logger.info(f'Using alternative price: ${price_value}')
                    
                    if price_value > 0:
                        item['price'] = str(price_value)
                except ValueError:
                    pass
        
        # Currency (Walmart US uses USD)
        item['currency'] = 'USD'
        
        # Rating
        rating = response.css('span[itemprop="ratingValue"]::text').get()
        if rating:
            item['rating'] = rating
        
        # Review count
        review_count = response.css('span[itemprop="reviewCount"]::text').get()
        if review_count:
            item['review_count'] = review_count
        
        # Availability
        availability = response.css('span.prod-ProductOffer-availability::text').get()
        if not availability:
            availability = response.css('div[data-testid="availability"] span::text').get()
        if availability:
            item['availability'] = availability
        
        # Description
        description_parts = response.css('div[itemprop="description"] p::text').getall()
        if not description_parts:
            description_parts = response.css('div.about-desc p::text').getall()
        if description_parts:
            item['description'] = ' '.join(description_parts)
        
        # Images - try multiple selectors, ensure we get at least one
        image_urls = []
        selectors = [
            'img[data-testid="product-image"]::attr(data-src)',  # Lazy-loaded
            'img[data-testid="product-image"]::attr(src)',
            'div[data-testid="image-gallery"] img::attr(data-src)',
            'div[data-testid="image-gallery"] img::attr(src)',
            'img.prod-hero-image-image::attr(src)',
            'img[itemprop="image"]::attr(src)',
            'div.prod-hero-image img::attr(src)',
            'div[class*="product-image"] img::attr(src)',
            'div[class*="hero-image"] img::attr(src)',
        ]
        
        for selector in selectors:
            images = response.css(selector).getall()
            for img_url in images:
                if img_url and img_url.startswith('http') and img_url not in image_urls:
                    # Skip placeholder images
                    if 'placeholder' in img_url.lower() or 'pixel.gif' in img_url.lower():
                        continue
                    image_urls.append(img_url)
                    if len(image_urls) >= 5:
                        break
            if len(image_urls) >= 5:
                break
        
        # Fallback: extract from page source if no images found
        if not image_urls:
            img_pattern = re.compile(r'https?://[^"\s]+walmart[^"\s]+\.(jpg|jpeg|png|gif|webp)', re.IGNORECASE)
            for img_match in img_pattern.finditer(response.text):
                img_url = img_match.group(0)
                if 'placeholder' not in img_url.lower() and img_url not in image_urls:
                    image_urls.append(img_url)
                    if len(image_urls) >= 3:
                        break
        
        if not image_urls:
            logger.warning(f'No images found for product {item.get("product_id")} at {response.url}')
        
        item['image_urls'] = image_urls[:5]  # Limit to first 5 images
        
        # Metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['raw_html'] = response.text
        
        yield item
    
    def closed(self, reason):
        """Cleanup when spider closes"""
        self.api_discovery.close()
        logger.info(f'Walmart spider closed: {reason}')

