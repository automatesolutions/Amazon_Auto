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
        
        # Price extraction - Kohl's has multiple price formats
        price = None
        
        # Try multiple selectors and formats
        price_selectors = [
            'span.product-price::text',
            'span[itemprop="price"]::text',
            'span[itemprop="price"]::attr(content)',
            'div.price-wrapper span::text',
            'span.regular-price::text',
            'span.sale-price::text',
            'span.price::text',
            'div.product-price::text',
            'span.current-price::text',
            'div.current-price span::text',
        ]
        
        for selector in price_selectors:
            price_text = response.css(selector).get()
            if price_text:
                price_text = price_text.strip()
                # Skip "from" prices
                if 'from' not in price_text.lower() and 'starting at' not in price_text.lower():
                    # Check if it contains a valid price pattern
                    if re.search(r'\$?\d+\.?\d*', price_text):
                        price = price_text
                        break
        
        # If still no price, try extracting from structured data
        if not price:
            # Try JSON-LD structured data
            json_ld = response.css('script[type="application/ld+json"]::text').getall()
            for script in json_ld:
                try:
                    import json
                    data = json.loads(script)
                    if isinstance(data, dict) and 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, dict) and 'price' in offers:
                            price = str(offers['price'])
                            break
                        elif isinstance(offers, list) and len(offers) > 0 and 'price' in offers[0]:
                            price = str(offers[0]['price'])
                            break
                except:
                    continue
        
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
                        # Don't set price if it's clearly wrong
                    elif price_value > 0:
                        item['price'] = str(price_value)
                except ValueError:
                    pass
            else:
                item['price'] = price
        
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
        
        # Images - try multiple selectors for Kohl's, ensure we get at least one
        image_urls = []
        selectors = [
            'img[itemprop="image"]::attr(data-src)',  # Lazy-loaded
            'img[itemprop="image"]::attr(src)',
            'img[itemprop="image"]::attr(data-lazy-src)',
            'div.product-image img::attr(data-src)',
            'div.product-image img::attr(src)',
            'div.product-image img::attr(data-lazy-src)',
            'img.product-image::attr(data-src)',
            'img.product-image::attr(src)',
            'div[data-product-image] img::attr(src)',
            'div.ImageWrapper img::attr(src)',
            'div.product-hero-image img::attr(data-src)',
            'div.product-hero-image img::attr(src)',
            'img.main-product-image::attr(src)',
            'img[class*="product"]::attr(src)',
            'img[class*="Product"]::attr(src)',
        ]
        
        for selector in selectors:
            images = response.css(selector).getall()
            for img_url in images:
                if not img_url:
                    continue
                # Skip placeholder images
                if 'placeholder' in img_url.lower() or 'pixel.gif' in img_url.lower():
                    continue
                # Handle protocol-relative URLs
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                # Only add valid HTTP(S) URLs
                if img_url.startswith('http') and img_url not in image_urls:
                    # Clean up Kohl's image URLs to get full resolution
                    if 'kohls.com' in img_url and '?' in img_url:
                        # Remove size parameters
                        img_url = img_url.split('?')[0]
                    image_urls.append(img_url)
                    if len(image_urls) >= 5:  # Limit to first 5 images
                        break
            if len(image_urls) >= 5:
                break
        
        # Fallback: extract from page source if no images found
        if not image_urls:
            img_pattern = re.compile(r'https?://[^"\s]+kohls[^"\s]+\.(jpg|jpeg|png|gif|webp)', re.IGNORECASE)
            for img_match in img_pattern.finditer(response.text):
                img_url = img_match.group(0)
                if 'placeholder' not in img_url.lower() and img_url not in image_urls:
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
        logger.info(f'Kohl\'s spider closed: {reason}')

