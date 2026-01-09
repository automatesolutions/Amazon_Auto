"""
Pydantic models for arbitrage opportunities
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity model"""
    product_id: str
    title: Optional[str] = None
    min_price: float
    max_price: float
    price_diff: float
    profit_margin_pct: float
    retailer_count: int
    cheapest_retailer: Optional[str] = None
    expensive_retailer: Optional[str] = None


class ArbitrageOpportunitiesResponse(BaseModel):
    """Arbitrage opportunities response model"""
    success: bool = True
    data: List[ArbitrageOpportunity]
    meta: dict = Field(default_factory=dict)


class PriceHistoryPoint(BaseModel):
    """Price history data point"""
    date: str
    price: float
    site: str
    currency: Optional[str] = None


class PriceHistoryResponse(BaseModel):
    """Price history response model"""
    success: bool = True
    data: List[PriceHistoryPoint]
    product_id: str
    title: Optional[str] = None

