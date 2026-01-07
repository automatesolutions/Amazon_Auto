"""
Walmart spider with API discovery and product scraping.
"""
import scrapy
import logging
from datetime import datetime
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
    
    def start_requests(self):
        """Generate initial requests"""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={'dont_cache': False}
            )
    
    def parse_search_results(self, response):
        """Parse Walmart search results page"""
        # Try API discovery first
        api_endpoints = self.api_discovery.discover_from_html(
            response.text,
            response.url,
            site='walmart'
        )
        
        # Extract product links from search results
        product_links = response.css('div[data-testid="item-stack"] a::attr(href)').getall()
        
        if not product_links:
            # Alternative selector
            product_links = response.css('a[data-testid="product-title"]::attr(href)').getall()
        
        for link in product_links:
            if '/ip/' in link:
                # Convert relative URLs to absolute
                if link.startswith('/'):
                    product_url = response.urljoin(link)
                else:
                    product_url = link
                
                yield scrapy.Request(
                    url=product_url,
                    callback=self.parse_product,
                    meta={'dont_cache': False}
                )
        
        # Follow pagination
        next_page = response.css('a[data-testid="next-page"]::attr(href)').get()
        if not next_page:
            next_page = response.css('nav[aria-label="pagination"] a[aria-label="Next"]::attr(href)').get()
        
        if next_page:
            yield response.follow(next_page, callback=self.parse_search_results)
    
    def parse_product(self, response):
        """Parse Walmart product detail page"""
        item = ProductItem()
        
        # Extract product ID from URL
        import re
        product_id_match = re.search(r'/ip/([^/]+)', response.url)
        if product_id_match:
            item['product_id'] = product_id_match.group(1)
        else:
            # Fallback: extract from page
            product_id_element = response.css('span[itemprop="productID"]::text').get()
            if product_id_element:
                item['product_id'] = product_id_element
        
        item['site'] = 'walmart'
        item['url'] = response.url
        
        # Extract product details
        item['title'] = response.css('h1[itemprop="name"]::text').get() or \
                       response.css('h1.prod-ProductTitle::text').get() or \
                       response.css('h1::text').get()
        
        # Price extraction
        price_selectors = [
            'span[itemprop="price"]::text',
            'span.price-current::text',
            'div[data-testid="price"] span::text',
            'span.price-characteristic::text',
        ]
        for selector in price_selectors:
            price = response.css(selector).get()
            if price:
                item['price'] = price
                break
        
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
        
        # Images
        image_urls = response.css('img[data-testid="product-image"]::attr(src)').getall()
        if not image_urls:
            image_urls = response.css('div[data-testid="image-gallery"] img::attr(src)').getall()
        item['image_urls'] = image_urls
        
        # Metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['raw_html'] = response.text
        
        yield item
    
    def closed(self, reason):
        """Cleanup when spider closes"""
        self.api_discovery.close()
        logger.info(f'Walmart spider closed: {reason}')

