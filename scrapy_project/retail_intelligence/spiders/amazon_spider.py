"""
Amazon spider with API discovery and product scraping.
"""
import scrapy
import logging
import re
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
        
        # Price extraction - Amazon splits price into whole and fractional parts
        # Try to get the full price from a-offscreen first (most reliable)
        # This is usually the actual selling price, not "from" prices
        price = response.css('span.a-price span.a-offscreen::text').get()
        
        if not price:
            # Combine whole and fractional parts
            whole_part = response.css('span.a-price-whole::text').get()
            fractional_part = response.css('span.a-price-fraction::text').get()
            if whole_part and fractional_part:
                price = f"{whole_part.strip().replace(',', '')}.{fractional_part.strip()}"
            elif whole_part:
                price = whole_part.strip().replace(',', '')
        
        # Fallback to other price selectors (prioritize actual price over "from" price)
        if not price:
            price_selectors = [
                'span#priceblock_ourprice::text',  # Main price
                'span#priceblock_dealprice::text',  # Deal price
                'span.a-price::text',  # Generic price
                'span[data-a-color="price"]::text',  # Price with data attribute
            ]
            for selector in price_selectors:
                price_text = response.css(selector).get()
                if price_text:
                    # Skip "from" prices - these are usually misleading
                    if 'from' not in price_text.lower() and 'starting at' not in price_text.lower():
                        price = price_text
                        break
        
        # Clean and validate price
        if price:
            # Remove "from", "starting at", etc.
            price_clean = re.sub(r'(from|starting at|as low as)\s*', '', price, flags=re.IGNORECASE).strip()
            # Extract numeric value
            price_match = re.search(r'[\d,]+\.?\d*', price_clean.replace(',', ''))
            if price_match:
                try:
                    price_value = float(price_match.group().replace(',', ''))
                    # Validate price is reasonable
                    # For expensive items like laptops, prices below $10 are likely errors
                    # Check title for expensive item keywords
                    title_lower = (item.get('title') or '').lower()
                    expensive_keywords = ['laptop', 'computer', 'gaming', 'macbook', 'thinkpad', 'alienware', 
                                         'iphone', 'samsung', 'tablet', 'ipad', 'monitor', 'tv', 'television']
                    is_expensive_item = any(keyword in title_lower for keyword in expensive_keywords)
                    
                    if is_expensive_item and price_value < 10:
                        # Likely a price error, try alternative selectors
                        logger.warning(f'Price ${price_value} seems too low for expensive item: {item.get("title")}')
                        # Try to get price from JavaScript data
                        price_js = response.css('script').re_first(r'"price":\s*"([^"]+)"')
                        if price_js:
                            price_match_js = re.search(r'[\d,]+\.?\d*', price_js.replace(',', ''))
                            if price_match_js:
                                price_value_js = float(price_match_js.group().replace(',', ''))
                                if price_value_js >= 10:
                                    price_value = price_value_js
                                    logger.info(f'Using alternative price: ${price_value}')
                    
                    if price_value > 0:
                        item['price'] = str(price_value)
                except ValueError:
                    pass
        
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
        
        # Images - try multiple selectors and attributes
        # CRITICAL: Ensure we always get at least one image
        image_urls = []
        
        # Try data-src first (lazy-loaded images), then src
        selectors = [
            'img#landingImage::attr(data-src)',  # Primary image, lazy-loaded
            'img#landingImage::attr(src)',  # Primary image, direct
            'div#main-image-container img::attr(data-src)',
            'div#main-image-container img::attr(src)',
            'div#main-image-container img::attr(data-old-src)',
            'div#altImages ul li img::attr(data-src)',
            'div#altImages ul li img::attr(src)',
            'img[data-a-image-name="landingImage"]::attr(src)',
            'div[data-action="main-image-click"] img::attr(src)',
            'div#imgTagWrapperId img::attr(src)',  # Alternative container
            'div#imageBlock_feature_div img::attr(src)',  # Feature div
        ]
        
        for selector in selectors:
            images = response.css(selector).getall()
            for img_url in images:
                if img_url and img_url not in image_urls and (img_url.startswith('http') or img_url.startswith('//')):
                    # Skip placeholder images
                    if 'grey-pixel.gif' in img_url or 'pixel.gif' in img_url or '1x1.gif' in img_url:
                        continue
                    
                    # Clean up Amazon image URLs (remove size restrictions for better quality)
                    if 'images-na.ssl-images-amazon.com' in img_url or 'images-fe.ssl-images-amazon.com' in img_url or 'm.media-amazon.com' in img_url:
                        # Remove size parameters to get full resolution
                        if '._' in img_url:
                            img_url = img_url.split('._')[0] + '._AC_SL1500_.jpg'
                        elif '/AC_' in img_url:
                            # Update existing size parameter
                            img_url = re.sub(r'/AC_[^/]+', '/AC_SL1500', img_url)
                    # Handle protocol-relative URLs
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    image_urls.append(img_url)
                    if len(image_urls) >= 5:  # Limit to first 5 images
                        break
            if len(image_urls) >= 5:
                break
        
        # If no images found, try extracting from JavaScript/JSON data
        if not image_urls:
            # Try to extract from JSON-LD or script tags
            script_data = response.css('script[type="application/ld+json"]::text').getall()
            for script in script_data:
                try:
                    import json
                    data = json.loads(script)
                    if isinstance(data, dict) and 'image' in data:
                        if isinstance(data['image'], list):
                            image_urls.extend([img for img in data['image'] if img.startswith('http')])
                        elif isinstance(data['image'], str) and data['image'].startswith('http'):
                            image_urls.append(data['image'])
                except:
                    pass
        
        # Final fallback: try to extract from page source directly
        if not image_urls:
            # Look for image URLs in the raw HTML
            img_pattern = re.compile(r'https?://[^"\s]+\.(jpg|jpeg|png|gif|webp)', re.IGNORECASE)
            found_images = img_pattern.findall(response.text)
            for img_match in img_pattern.finditer(response.text):
                img_url = img_match.group(0)
                if 'amazon' in img_url and 'grey-pixel' not in img_url and 'pixel.gif' not in img_url:
                    if img_url not in image_urls:
                        image_urls.append(img_url)
                        if len(image_urls) >= 3:
                            break
        
        if not image_urls:
            logger.warning(f'No images found for product {item.get("product_id")} at {response.url}')
        
        item['image_urls'] = image_urls
        
        # Metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['raw_html'] = response.text
        
        yield item
    
    def closed(self, reason):
        """Cleanup when spider closes"""
        self.api_discovery.close()
        logger.info(f'Amazon spider closed: {reason}')

