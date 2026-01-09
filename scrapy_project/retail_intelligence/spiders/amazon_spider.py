"""
Amazon spider with API discovery and product scraping.
"""
import scrapy
import logging
from datetime import datetime
from retail_intelligence.items import ProductItem
from retail_intelligence.utils.api_discovery import APIDiscovery

logger = logging.getLogger(__name__)


class AmazonSpider(scrapy.Spider):
    """
    Spider for scraping Amazon product data.
    Uses API discovery to find hidden endpoints before scraping HTML.
    
    Note: Works with scrapy-redis scheduler. start_requests() will queue URLs in Redis.
    """
    """
    Spider for scraping Amazon product data.
    Uses API discovery to find hidden endpoints before scraping HTML.
    """
    
    name = 'amazon'
    allowed_domains = ['amazon.com', 'amazon.ca', 'amazon.com.mx']
    
    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)
        self.api_discovery = APIDiscovery(browser_type='chrome110')
        self.start_urls = kwargs.get('start_urls', '').split(',') if kwargs.get('start_urls') else []
        
        # Default start URLs if none provided
        if not self.start_urls:
            self.start_urls = [
                'https://www.amazon.com/s?k=laptop',
                'https://www.amazon.com/s?k=smartphone',
            ]
    
    async def start(self):
        """Generate initial requests (async method for Scrapy 2.13+)"""
        logger.info(f'start() called with {len(self.start_urls)} URLs: {self.start_urls}')
        for url in self.start_urls:
            logger.info(f'Yielding request for: {url}')
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={'dont_cache': False}
            )
    
    def parse_search_results(self, response):
        """Parse Amazon search results page"""
        # Try API discovery first
        api_endpoints = self.api_discovery.discover_from_html(
            response.text,
            response.url,
            site='amazon'
        )
        
        # Extract product links from search results
        product_links = response.css('div[data-component-type="s-search-result"] a.a-link-normal::attr(href)').getall()
        
        for link in product_links:
            if '/dp/' in link or '/gp/product/' in link:
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
        next_page = response.css('a.s-pagination-next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_search_results)
    
    def parse_product(self, response):
        """Parse Amazon product detail page"""
        item = ProductItem()
        
        # Extract product ID from URL
        import re
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', response.url)
        if asin_match:
            item['product_id'] = asin_match.group(1)
        else:
            # Fallback: extract from page
            asin_element = response.css('input#ASIN::attr(value)').get()
            if asin_element:
                item['product_id'] = asin_element
        
        item['site'] = 'amazon'
        item['url'] = response.url
        
        # Extract product details
        item['title'] = response.css('span#productTitle::text').get() or \
                       response.css('h1.a-size-base-plus::text').get()
        
        # Price extraction
        price_selectors = [
            'span.a-price-whole::text',
            'span.a-price span.a-offscreen::text',
            'span#priceblock_ourprice::text',
            'span#priceblock_dealprice::text',
        ]
        for selector in price_selectors:
            price = response.css(selector).get()
            if price:
                item['price'] = price
                break
        
        # Currency
        currency_symbol = response.css('span.a-price-symbol::text').get()
        if currency_symbol:
            item['currency'] = currency_symbol
        
        # Rating
        rating = response.css('span.a-icon-alt::text').re_first(r'([\d.]+)')
        if rating:
            item['rating'] = rating
        
        # Review count
        review_count = response.css('span#acrCustomerReviewText::text').re_first(r'([\d,]+)')
        if review_count:
            item['review_count'] = review_count
        
        # Availability
        availability = response.css('span#availability span::text').get()
        if availability:
            item['availability'] = availability
        
        # Description
        description_parts = response.css('div#feature-bullets ul li span::text').getall()
        if description_parts:
            item['description'] = ' '.join(description_parts)
        
        # Images
        image_urls = response.css('div#main-image-container img::attr(src)').getall()
        if not image_urls:
            image_urls = response.css('div#altImages ul li img::attr(src)').getall()
        item['image_urls'] = image_urls
        
        # Metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['raw_html'] = response.text
        
        yield item
    
    def closed(self, reason):
        """Cleanup when spider closes"""
        self.api_discovery.close()
        logger.info(f'Amazon spider closed: {reason}')

