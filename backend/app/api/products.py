"""
Product API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from app.models.product import (
    ProductSearchRequest,
    ProductSearchResponse,
    ProductResponse,
    BrandsResponse,
    BrandResponse
)
from app.services.bigquery_service import BigQueryService
from app.services.cache_service import CacheService
from app.services.gcs_service import GCSService

logger = logging.getLogger(__name__)

router = APIRouter()
bq_service = BigQueryService()
cache_service = CacheService()
gcs_service = GCSService()


@router.get("/search", response_model=ProductSearchResponse)
async def search_products(
    query: Optional[str] = Query(None, description="Search query string"),
    brands: Optional[str] = Query(None, description="Comma-separated list of brands"),
    retailers: Optional[str] = Query(None, description="Comma-separated list of retailers"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Search products with filters"""
    try:
        # Parse comma-separated lists
        brands_list = [b.strip() for b in brands.split(",")] if brands else None
        retailers_list = [r.strip() for r in retailers.split(",")] if retailers else None
        
        # Generate cache key
        cache_key = cache_service.generate_key(
            "product_search",
            query=query,
            brands=",".join(brands_list) if brands_list else None,
            retailers=",".join(retailers_list) if retailers_list else None,
            min_price=min_price,
            max_price=max_price,
            page=page,
            per_page=per_page
        )
        
        # Check cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for product search: {cache_key}")
            return ProductSearchResponse(**cached_result)
        
        # Query BigQuery
        result = bq_service.search_products(
            query=query,
            brands=brands_list,
            retailers=retailers_list,
            min_price=min_price,
            max_price=max_price,
            page=page,
            per_page=per_page
        )
        
        # Process image URLs
        for product in result["data"]:
            if product.get("image_urls") and len(product["image_urls"]) > 0:
                product["image_url"] = product["image_urls"][0]
            # Generate signed URL if gcs_path exists
            if product.get("gcs_path"):
                signed_url = gcs_service.get_image_url(product["gcs_path"])
                if signed_url:
                    product["image_url"] = signed_url
        
        # Cache result
        cache_service.set(cache_key, result, ttl=300)  # 5 minutes
        
        return ProductSearchResponse(
            success=True,
            data=[ProductResponse(**p) for p in result["data"]],
            meta=result["meta"]
        )
    except Exception as e:
        logger.error(f"Error searching products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get single product by ID"""
    try:
        cache_key = cache_service.generate_key("product", product_id=product_id)
        
        # Check cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            return ProductResponse(**cached_result)
        
        # Query BigQuery
        product = bq_service.get_product(product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Process image URLs
        if product.get("image_urls") and len(product["image_urls"]) > 0:
            product["image_url"] = product["image_urls"][0]
        
        # Cache result
        cache_service.set(cache_key, product, ttl=600)  # 10 minutes
        
        return ProductResponse(**product)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brands/list", response_model=BrandsResponse)
async def get_brands():
    """Get list of available brands"""
    try:
        cache_key = cache_service.generate_key("brands")
        
        # Check cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            return BrandsResponse(**cached_result)
        
        # Query BigQuery
        brands = bq_service.get_brands()
        
        result = {
            "success": True,
            "data": [BrandResponse(brand=b["brand"], count=b["count"]) for b in brands]
        }
        
        # Cache result (longer TTL for brands)
        cache_service.set(cache_key, result, ttl=3600)  # 1 hour
        
        return BrandsResponse(**result)
    except Exception as e:
        logger.error(f"Error getting brands: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

