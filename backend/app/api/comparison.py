"""
Product comparison API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List
import logging

from app.models.comparison import (
    ComparisonRequest,
    ComparisonResponse,
    ProductComparison,
    RetailerPrice
)
from app.services.bigquery_service import BigQueryService
from app.services.cache_service import CacheService
from app.services.gcs_service import GCSService

logger = logging.getLogger(__name__)

router = APIRouter()
bq_service = BigQueryService()
cache_service = CacheService()
gcs_service = GCSService()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_products(request: ComparisonRequest):
    """Compare products across retailers"""
    try:
        if not request.product_ids:
            raise HTTPException(status_code=400, detail="At least one product_id is required")
        
        # Generate cache key
        cache_key = cache_service.generate_key(
            "comparison",
            product_ids=",".join(sorted(request.product_ids))
        )
        
        # Check cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for comparison: {cache_key}")
            return ComparisonResponse(**cached_result)
        
        # Query BigQuery
        results = bq_service.compare_products(request.product_ids)
        
        # Group by product_id
        products_dict = {}
        for row in results:
            product_id = row["product_id"]
            
            if product_id not in products_dict:
                products_dict[product_id] = {
                    "product_id": product_id,
                    "title": row.get("title"),
                    "description": row.get("description"),
                    "image_url": row.get("image_url"),
                    "retailers": [],
                    "prices": []
                }
            
            # Add retailer price info
            price = row.get("price")
            if price is not None:
                products_dict[product_id]["prices"].append(price)
            
            products_dict[product_id]["retailers"].append(
                RetailerPrice(
                    site=row["site"],
                    price=price,
                    currency=row.get("currency"),
                    availability=row.get("availability"),
                    url=row["url"],
                    rating=row.get("rating"),
                    review_count=row.get("review_count"),
                    scraped_at=row["scraped_at"]
                )
            )
        
        # Build response with comparison metrics
        comparisons = []
        for product_id, product_data in products_dict.items():
            prices = product_data["prices"]
            min_price = min(prices) if prices else None
            max_price = max(prices) if prices else None
            price_diff = (max_price - min_price) if (min_price and max_price) else None
            
            # Find best price retailer
            best_retailer = None
            if min_price:
                for retailer in product_data["retailers"]:
                    if retailer.price == min_price:
                        best_retailer = retailer.site
                        break
            
            comparisons.append(
                ProductComparison(
                    product_id=product_id,
                    title=product_data["title"],
                    description=product_data["description"],
                    image_url=product_data["image_url"],
                    retailers=product_data["retailers"],
                    min_price=min_price,
                    max_price=max_price,
                    price_difference=price_diff,
                    best_price_retailer=best_retailer
                )
            )
        
        result = {
            "success": True,
            "data": [c.dict() for c in comparisons],
            "meta": {
                "product_count": len(comparisons)
            }
        }
        
        # Cache result
        cache_service.set(cache_key, result, ttl=300)  # 5 minutes
        
        return ComparisonResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ComparisonResponse)
async def get_product_retailers(product_id: str):
    """Get all retailers for a specific product"""
    try:
        # Use comparison endpoint with single product
        request = ComparisonRequest(product_ids=[product_id])
        return await compare_products(request)
    except Exception as e:
        logger.error(f"Error getting product retailers for {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

