"""
CrossRetail FastAPI Application
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

# Load environment variables from .env file
# Look for .env in project root (2 levels up from backend/app/)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

from app.api import products, comparison, arbitrage, spiders

logger = logging.getLogger(__name__)

# CORS configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    logger.info("Starting CrossRetail API...")
    yield
    # Shutdown
    logger.info("Shutting down CrossRetail API...")


app = FastAPI(
    title="CrossRetail API",
    description="Multi-Retailer Price Intelligence & Arbitrage Analytics API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc)
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CrossRetail API"
    }


# Include routers
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(comparison.router, prefix="/api/comparison", tags=["comparison"])
app.include_router(arbitrage.router, prefix="/api/arbitrage", tags=["arbitrage"])
app.include_router(spiders.router, prefix="/api/spiders", tags=["spiders"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

