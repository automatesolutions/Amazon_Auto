"""
Pydantic models for product-related requests and responses
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class ProductResponse(BaseModel):
    """Product response model"""
    product_id: str
    site: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    availability: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: Optional[List[str]] = None
    scraped_at: datetime
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None

    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    """Product search request model"""
    query: Optional[str] = Field(None, description="Search query string")
    brands: Optional[List[str]] = Field(None, description="Filter by brands")
    retailers: Optional[List[str]] = Field(None, description="Filter by retailers (amazon, walmart, kohls, kmart)")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class ProductSearchResponse(BaseModel):
    """Product search response model"""
    success: bool = True
    data: List[ProductResponse]
    meta: dict = Field(default_factory=dict)


class BrandResponse(BaseModel):
    """Brand response model"""
    brand: str
    count: int


class BrandsResponse(BaseModel):
    """Brands list response model"""
    success: bool = True
    data: List[BrandResponse]

