"""
Kohl's spider with API discovery and product scraping.
"""
import scrapy
import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from retail_intelligence.items import ProductItem
from retail_intelligence.utils.api_discovery import APIDiscovery

logger = logging.getLogger(__name__)


class KohlsSpider(scrapy.Spider):
    """
    Spider for scraping Kohl's product data.
    Uses API discovery to find hidden endpoints before scraping HTML.
    """
    
    name = 'kohls'
    allowed_domains = ['kohls.com']
    
    def __init__(self, *args, **kwargs):
        super(KohlsSpider, self).__init__(*args, **kwargs)
        self.api_discovery = APIDiscovery(browser_type='chrome110')
        self.start_urls = kwargs.get('start_urls', '').split(',') if kwargs.get('start_urls') else []
        
        # Default start URLs if none provided
        if not self.start_urls:
            self.start_urls = [
                'https://www.kohls.com/search.jsp?submit-search=web-regular&search=laptop',
                'https://www.kohls.com/search.jsp?submit-search=web-regular&search=smartphone',
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
        """Parse Kohl's search results page"""
        logger.info(f'Parsing search results page: {response.url} (status: {response.status})')
        
        if response.status != 200:
            logger.warning(f'Non-200 status code {response.status} for {response.url}')
            return
        
        # Try API discovery first
        api_endpoints = self.api_discovery.discover_from_html(
            response.text,
            response.url,
            site='kohls'
        )
        
        # Extract product links from search results
        product_links = []
        selectors = [
            'div[data-product-id] a::attr(href)',
            'a[data-product-id]::attr(href)',
            'div.product-tile a::attr(href)',
            'a.product-tile-link::attr(href)',
            'div[class*="ProductTile"] a::attr(href)',
            'a[href*="/product/"]::attr(href)',
            'a[href*="/prd-"]::attr(href)',
        ]
        
        for selector in selectors:
            links = response.css(selector).getall()
            if links:
                product_links.extend(links)
                logger.debug(f'Found {len(links)} links using selector: {selector}')
        
        # Remove duplicates
        seen = set()
        unique_links = []
        for link in product_links:
            if link and link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        logger.info(f'Found {len(unique_links)} unique product links on {response.url}')
        
        # Filter for product links
        product_count = 0
        for link in unique_links:
            if not link:
                continue
            
            is_product_link = (
                '/product/' in link or
                '/prd-' in link or
                'kohls.com/product/' in link
            )
            
            skip_patterns = [
                '/search',
                '/browse',
                '/category',
                '/account',
                '/cart',
                'javascript:',
                '#',
            ]
            
            should_skip = any(pattern in link.lower() for pattern in skip_patterns)
            
            if is_product_link and not should_skip:
                if link.startswith('/'):
                    product_url = response.urljoin(link)
                else:
                    product_url = link
                
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
        """Parse Kohl's product detail page"""
        logger.debug(f'Parsing product page: {response.url}')
        item = ProductItem()
        
        # Extract product ID from URL
        product_id_match = re.search(r'/product/(\d+)', response.url)
        if not product_id_match:
            product_id_match = re.search(r'/prd-(\d+)', response.url)
        if not product_id_match:
            product_id_match = re.search(r'/(\d{6,})', response.url)
        
        if product_id_match:
            item['product_id'] = f"kohls_{product_id_match.group(1)}"
        else:
            # Fallback: extract from page
            product_id_element = response.css('div[data-product-id]::attr(data-product-id)').get()
            if product_id_element:
                item['product_id'] = f"kohls_{product_id_element}"
            else:
                item['product_id'] = f"kohls_{response.url.split('/')[-1].split('?')[0]}"
        
        item['site'] = 'kohls'
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
              response.css('div[itemprop="sku"]::text').get()
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
        ]
        for selector in price_selectors:
            price = response.css(selector).get()
            if price:
                item['price'] = price
                break
        
        # Currency (Kohl's US uses USD)
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
        logger.info(f'Kohl\'s spider closed: {reason}')

