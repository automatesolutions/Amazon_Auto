"""
Scrapy items for retail_intelligence project
"""
import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from w3lib.html import remove_tags


def clean_price(value):
    """Extract numeric price from string"""
    if not value:
        return None
    # Remove currency symbols and whitespace
    import re
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def clean_rating(value):
    """Extract numeric rating from string"""
    if not value:
        return None
    import re
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def clean_review_count(value):
    """Extract numeric review count from string"""
    if not value:
        return None
    import re
    # Handle formats like "1,234 reviews" or "1234"
    cleaned = re.sub(r'[^\d]', '', str(value))
    try:
        return int(cleaned)
    except ValueError:
        return None


def clean_text(value):
    """Clean HTML tags and normalize whitespace"""
    if not value:
        return None
    text = remove_tags(str(value))
    return ' '.join(text.split())


class ProductItem(scrapy.Item):
    """Standardized product item schema"""
    # Identifiers
    product_id = scrapy.Field(output_processor=TakeFirst())
    site = scrapy.Field(output_processor=TakeFirst())
    url = scrapy.Field(output_processor=TakeFirst())
    
    # Basic Info
    title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    description = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join(' ')
    )
    
    # Pricing
    price = scrapy.Field(
        input_processor=MapCompose(clean_price),
        output_processor=TakeFirst()
    )
    currency = scrapy.Field(output_processor=TakeFirst())
    
    # Ratings & Reviews
    rating = scrapy.Field(
        input_processor=MapCompose(clean_rating),
        output_processor=TakeFirst()
    )
    review_count = scrapy.Field(
        input_processor=MapCompose(clean_review_count),
        output_processor=TakeFirst()
    )
    
    # Availability
    availability = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # Images
    image_urls = scrapy.Field()
    
    # Metadata
    scraped_at = scrapy.Field(output_processor=TakeFirst())
    
    # Raw HTML for archival (stored separately in GCS)
    raw_html = scrapy.Field()
    
    # GCS path reference (added by pipeline)
    gcs_path = scrapy.Field(output_processor=TakeFirst())

