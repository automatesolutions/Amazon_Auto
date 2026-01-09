"""
Arbitrage opportunities API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.arbitrage import (
    ArbitrageOpportunitiesResponse,
    ArbitrageOpportunity,
    PriceHistoryResponse,
    PriceHistoryPoint
)
from app.services.bigquery_service import BigQueryService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter()
bq_service = BigQueryService()
cache_service = CacheService()


@router.get("/opportunities", response_model=ArbitrageOpportunitiesResponse)
async def get_arbitrage_opportunities(
    min_margin_pct: float = Query(10.0, ge=0, description="Minimum profit margin percentage"),
    min_price_diff: float = Query(5.0, ge=0, description="Minimum price difference"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
):
    """Get arbitrage opportunities"""
    try:
        # Generate cache key
        cache_key = cache_service.generate_key(
            "arbitrage",
            min_margin_pct=min_margin_pct,
            min_price_diff=min_price_diff,
            limit=limit
        )
        
        # Check cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for arbitrage opportunities: {cache_key}")
            return ArbitrageOpportunitiesResponse(**cached_result)
        
        # Query BigQuery
        opportunities = bq_service.get_arbitrage_opportunities(
            min_margin_pct=min_margin_pct,
            min_price_diff=min_price_diff,
            limit=limit
        )
        
        result = {
            "success": True,
            "data": [ArbitrageOpportunity(**opp) for opp in opportunities],
            "meta": {
                "count": len(opportunities),
                "min_margin_pct": min_margin_pct,
                "min_price_diff": min_price_diff
            }
        }
        
        # Cache result (shorter TTL for arbitrage data)
        cache_service.set(cache_key, result, ttl=180)  # 3 minutes
        
        return ArbitrageOpportunitiesResponse(**result)
    except Exception as e:
        logger.error(f"Error getting arbitrage opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-history/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history")
):
    """Get price history for a product"""
    try:
        # Generate cache key
        cache_key = cache_service.generate_key(
            "price_history",
            product_id=product_id,
            days=days
        )
        
        # Check cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            return PriceHistoryResponse(**cached_result)
        
        # Query BigQuery
        history = bq_service.get_price_history(product_id, days=days)
        
        # Get product title
        product = bq_service.get_product(product_id)
        title = product.get("title") if product else None
        
        # Format history data
        history_points = [
            PriceHistoryPoint(
                date=row["date"].strftime("%Y-%m-%d"),
                price=float(row["price"]),
                site=row["site"],
                currency=row.get("currency")
            )
            for row in history
        ]
        
        result = {
            "success": True,
            "data": [h.dict() for h in history_points],
            "product_id": product_id,
            "title": title
        }
        
        # Cache result
        cache_service.set(cache_key, result, ttl=600)  # 10 minutes
        
        return PriceHistoryResponse(**result)
    except Exception as e:
        logger.error(f"Error getting price history for {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

