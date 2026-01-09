"""
Pydantic models for product comparison
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.product import ProductResponse


class RetailerPrice(BaseModel):
    """Price information for a single retailer"""
    site: str
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    url: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    scraped_at: datetime


class ProductComparison(BaseModel):
    """Product comparison across retailers"""
    product_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    retailers: List[RetailerPrice]
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_difference: Optional[float] = None
    best_price_retailer: Optional[str] = None


class ComparisonRequest(BaseModel):
    """Request to compare products"""
    product_ids: List[str] = Field(..., min_items=1, description="List of product IDs to compare")


class ComparisonResponse(BaseModel):
    """Comparison response model"""
    success: bool = True
    data: List[ProductComparison]
    meta: dict = Field(default_factory=dict)

