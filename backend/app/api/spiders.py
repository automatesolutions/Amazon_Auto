"""
Spider trigger API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging
import subprocess
import uuid
import os
from datetime import datetime

from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter()
cache_service = CacheService()


class SpiderTriggerRequest(BaseModel):
    """Request to trigger a spider"""
    spider_name: str  # amazon, walmart, kohls, kmart
    start_urls: Optional[List[str]] = None


class SpiderStatusResponse(BaseModel):
    """Spider job status response"""
    job_id: str
    spider_name: str
    status: str  # pending, running, completed, failed
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


def run_spider(spider_name: str, start_urls: List[str], job_id: str):
    """Run spider in background"""
    try:
        # Update status to running
        cache_service.set(
            f"spider_job:{job_id}",
            {
                "job_id": job_id,
                "spider_name": spider_name,
                "status": "running",
                "created_at": datetime.utcnow().isoformat()
            },
            ttl=3600
        )
        
        # Build scrapy command
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        scrapy_dir = os.path.join(project_root, "scrapy_project")
        
        cmd = ["scrapy", "crawl", spider_name]
        if start_urls:
            urls_str = ",".join(start_urls)
            cmd.extend(["-a", f"start_urls={urls_str}"])
        
        # Run spider
        result = subprocess.run(
            cmd,
            cwd=scrapy_dir,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        # Update status
        status_data = {
            "job_id": job_id,
            "spider_name": spider_name,
            "status": "completed" if result.returncode == 0 else "failed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": result.stderr if result.returncode != 0 else None
        }
        cache_service.set(f"spider_job:{job_id}", status_data, ttl=86400)  # 24 hours
        
    except subprocess.TimeoutExpired:
        status_data = {
            "job_id": job_id,
            "spider_name": spider_name,
            "status": "failed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": "Spider execution timeout"
        }
        cache_service.set(f"spider_job:{job_id}", status_data, ttl=86400)
    except Exception as e:
        logger.error(f"Error running spider {spider_name}: {e}", exc_info=True)
        status_data = {
            "job_id": job_id,
            "spider_name": spider_name,
            "status": "failed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        cache_service.set(f"spider_job:{job_id}", status_data, ttl=86400)


@router.post("/trigger", response_model=SpiderStatusResponse)
async def trigger_spider(request: SpiderTriggerRequest, background_tasks: BackgroundTasks):
    """Trigger a scraping job"""
    valid_spiders = ["amazon", "walmart", "kohls", "kmart"]
    
    if request.spider_name not in valid_spiders:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid spider name. Must be one of: {', '.join(valid_spiders)}"
        )
    
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Default start URLs if not provided
        start_urls = request.start_urls or []
        
        # Create initial job status
        status_data = {
            "job_id": job_id,
            "spider_name": request.spider_name,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        cache_service.set(f"spider_job:{job_id}", status_data, ttl=86400)
        
        # Add background task
        background_tasks.add_task(
            run_spider,
            request.spider_name,
            start_urls,
            job_id
        )
        
        return SpiderStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Error triggering spider: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=SpiderStatusResponse)
async def get_spider_status(job_id: str):
    """Get spider job status"""
    try:
        status_data = cache_service.get(f"spider_job:{job_id}")
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return SpiderStatusResponse(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spider status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

