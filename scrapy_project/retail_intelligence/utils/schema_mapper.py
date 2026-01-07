"""
Schema mapper for cleaning and normalizing scraped data.
Maps unstructured data from different sites to standardized schema.
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SchemaMapper:
    """
    Maps and normalizes scraped data to standardized schema.
    Handles data cleaning, type conversion, and validation.
    """
    
    def __init__(self):
        """Initialize schema mapper"""
        pass
    
    def normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize item to BigQuery-compatible schema.
        
        Args:
            item: Raw scraped item
        
        Returns:
            Normalized item dictionary
        """
        normalized = {
            'product_id': self._normalize_product_id(item.get('product_id')),
            'site': self._normalize_site(item.get('site')),
            'url': item.get('url', ''),
            'title': self._clean_text(item.get('title')),
            'description': self._clean_text(item.get('description')),
            'price': self._normalize_price(item.get('price')),
            'currency': self._normalize_currency(item.get('currency'), item.get('price')),
            'rating': self._normalize_rating(item.get('rating')),
            'review_count': self._normalize_review_count(item.get('review_count')),
            'availability': self._normalize_availability(item.get('availability')),
            'image_urls': self._normalize_image_urls(item.get('image_urls')),
            'scraped_at': self._normalize_timestamp(item.get('scraped_at')),
            'gcs_path': item.get('gcs_path', ''),
        }
        
        return normalized
    
    def _normalize_product_id(self, product_id):
        """Normalize product ID"""
        if not product_id:
            return None
        
        # Remove whitespace and convert to string
        product_id = str(product_id).strip()
        
        # Extract alphanumeric ID if embedded in URL or text
        match = re.search(r'[A-Z0-9]{10,}', product_id)
        if match:
            return match.group(0)
        
        return product_id
    
    def _normalize_site(self, site):
        """Normalize site name"""
        if not site:
            return 'unknown'
        
        site = str(site).lower().strip()
        
        # Standardize site names
        site_mapping = {
            'amazon': 'amazon',
            'amazon.com': 'amazon',
            'walmart': 'walmart',
            'walmart.com': 'walmart',
        }
        
        return site_mapping.get(site, site)
    
    def _clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return None
        
        if isinstance(text, list):
            text = ' '.join(str(t) for t in text if t)
        
        text = str(text).strip()
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text if text else None
    
    def _normalize_price(self, price):
        """Normalize price to float"""
        if price is None:
            return None
        
        if isinstance(price, (int, float)):
            return float(price)
        
        # Extract numeric value from string
        import re
        match = re.search(r'[\d.]+', str(price))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                pass
        
        return None
    
    def _normalize_currency(self, currency, price=None):
        """Normalize currency code"""
        if currency:
            currency = str(currency).strip().upper()
            # Extract currency symbol/code
            match = re.search(r'[A-Z]{3}|\$|€|£|¥', currency)
            if match:
                symbol = match.group(0)
                currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY'}
                return currency_map.get(symbol, symbol)
            return currency[:3] if len(currency) >= 3 else currency
        
        # Infer from price string if available
        if price:
            price_str = str(price)
            if '$' in price_str:
                return 'USD'
            elif '€' in price_str:
                return 'EUR'
            elif '£' in price_str:
                return 'GBP'
        
        return 'USD'  # Default
    
    def _normalize_rating(self, rating):
        """Normalize rating to float (0-5 scale)"""
        if rating is None:
            return None
        
        if isinstance(rating, (int, float)):
            # Ensure rating is in 0-5 range
            rating = float(rating)
            if rating > 5:
                rating = rating / 2  # Convert 10-point scale to 5-point
            return rating
        
        # Extract numeric value
        match = re.search(r'[\d.]+', str(rating))
        if match:
            try:
                rating = float(match.group(0))
                if rating > 5:
                    rating = rating / 2
                return rating
            except ValueError:
                pass
        
        return None
    
    def _normalize_review_count(self, review_count):
        """Normalize review count to integer"""
        if review_count is None:
            return None
        
        if isinstance(review_count, int):
            return review_count
        
        # Extract numeric value
        match = re.search(r'[\d,]+', str(review_count))
        if match:
            try:
                return int(match.group(0).replace(',', ''))
            except ValueError:
                pass
        
        return None
    
    def _normalize_availability(self, availability):
        """Normalize availability status"""
        if not availability:
            return None
        
        availability = str(availability).lower().strip()
        
        # Standardize availability keywords
        if any(keyword in availability for keyword in ['in stock', 'available', 'add to cart']):
            return 'in_stock'
        elif any(keyword in availability for keyword in ['out of stock', 'unavailable', 'sold out']):
            return 'out_of_stock'
        elif any(keyword in availability for keyword in ['pre-order', 'preorder']):
            return 'pre_order'
        else:
            return availability
    
    def _normalize_image_urls(self, image_urls):
        """Normalize image URLs to list"""
        if not image_urls:
            return []
        
        if isinstance(image_urls, str):
            # Split by common delimiters
            image_urls = [url.strip() for url in re.split(r'[,\s]+', image_urls) if url.strip()]
        
        if isinstance(image_urls, list):
            # Filter valid URLs
            url_pattern = re.compile(r'^https?://.+')
            return [url for url in image_urls if url_pattern.match(str(url))]
        
        return []
    
    def _normalize_timestamp(self, timestamp):
        """Normalize timestamp to ISO format"""
        if not timestamp:
            return datetime.utcnow().isoformat()
        
        if isinstance(timestamp, datetime):
            return timestamp.isoformat()
        
        # Try to parse various timestamp formats
        timestamp_str = str(timestamp)
        
        # ISO format
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.isoformat()
        except ValueError:
            pass
        
        # Common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        # Return current timestamp if parsing fails
        return datetime.utcnow().isoformat()

