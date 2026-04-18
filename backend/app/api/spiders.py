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
    items_scraped: Optional[int] = 0  # Number of items scraped so far
    last_scraped_at: Optional[str] = None  # Timestamp of last item scraped


def run_spider(spider_name: str, start_urls: List[str], job_id: str):
    """Run spider in background"""
    from app.services.bigquery_service import BigQueryService
    bq_service = BigQueryService()
    
    # Record start time for tracking items scraped since start
    start_time = datetime.utcnow()
    # Get initial count of products for this site (before scraping starts)
    initial_count = bq_service.count_products_by_site(spider_name)
    
    try:
        # Update status to running
        cache_service.set(
            f"spider_job:{job_id}",
            {
                "job_id": job_id,
                "spider_name": spider_name,
                "status": "running",
                "created_at": datetime.utcnow().isoformat(),
                "items_scraped": 0,
                "initial_count": initial_count,
            },
            ttl=3600
        )
        
        # Build scrapy command
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        scrapy_dir = os.path.join(project_root, "scrapy_project")
        
        # Try to find Python executable with scrapy installed
        # Check root venv first (where scrapy is likely installed), then backend venv, then system Python
        import sys
        import platform
        
        python_executable = None
        
        # Try root venv first (most likely location for scrapy on Windows)
        if platform.system() == 'Windows':
            root_venv_python = os.path.join(project_root, "venv", "Scripts", "python.exe")
            if os.path.exists(root_venv_python):
                python_executable = root_venv_python
                logger.info(f"Found root venv Python: {python_executable}")
        
        # If not found, try checking if scrapy is available in current Python
        if not python_executable:
            try:
                check_result = subprocess.run(
                    [sys.executable, "-m", "scrapy", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if check_result.returncode == 0:
                    python_executable = sys.executable
                    logger.info(f"Scrapy found in current Python: {python_executable}")
            except:
                pass
        
        # If still not found, try root venv (Linux/Mac style)
        if not python_executable:
            root_venv_python = os.path.join(project_root, "venv", "bin", "python")
            if os.path.exists(root_venv_python):
                python_executable = root_venv_python
                logger.info(f"Found root venv Python (Unix): {python_executable}")
        
        # Fallback to system Python
        if not python_executable:
            python_executable = sys.executable
            logger.warning(f"Using system Python, scrapy may not be installed: {python_executable}")
        
        # Build command: python -m scrapy crawl spider_name
        cmd = [python_executable, "-m", "scrapy", "crawl", spider_name]
        if start_urls:
            urls_str = ",".join(start_urls)
            cmd.extend(["-a", f"start_urls={urls_str}"])
        
        logger.info(f"Running spider command: {' '.join(cmd)} in directory: {scrapy_dir}")
        logger.info(f"Python executable: {python_executable}")
        logger.info(f"Working directory exists: {os.path.exists(scrapy_dir)}")
        
        # Verify scrapy_project directory exists
        if not os.path.exists(scrapy_dir):
            raise FileNotFoundError(f"Scrapy project directory not found: {scrapy_dir}")
        
        # Verify scrapy.cfg exists
        scrapy_cfg = os.path.join(scrapy_dir, "scrapy.cfg")
        if not os.path.exists(scrapy_cfg):
            raise FileNotFoundError(f"scrapy.cfg not found in: {scrapy_dir}")
        
        # Verify scrapy is available in the selected Python
        try:
            check_result = subprocess.run(
                [python_executable, "-m", "scrapy", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if check_result.returncode != 0:
                raise FileNotFoundError(
                    f"Scrapy not found in {python_executable}. "
                    f"Please install scrapy in the root venv or ensure it's accessible."
                )
            logger.info(f"Scrapy version check passed: {check_result.stdout.strip()}")
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.warning(f"Could not verify scrapy installation: {e}")
        
        # Prepare environment variables for subprocess
        env = os.environ.copy()
        # Ensure .env file path is set so scrapy can load it
        env_path = os.path.join(project_root, "config", ".env")
        if os.path.exists(env_path):
            env["ENV_FILE_PATH"] = env_path
        
        # Run spider
        result = subprocess.run(
            cmd,
            cwd=scrapy_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            shell=False  # Don't use shell on Windows
        )
        
        # Log output for debugging
        if result.stdout:
            logger.info(f"Spider stdout: {result.stdout[:500]}")  # First 500 chars
        if result.stderr:
            logger.warning(f"Spider stderr: {result.stderr[:500]}")  # First 500 chars
        
        # Get final item count (products scraped since job started)
        final_count = bq_service.count_products_by_site(spider_name, since=start_time)
        # Calculate items scraped in this job session
        items_scraped = max(0, final_count)
        
        # Update status
        status_data = {
            "job_id": job_id,
            "spider_name": spider_name,
            "status": "completed" if result.returncode == 0 else "failed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": result.stderr if result.returncode != 0 else None,
            "items_scraped": items_scraped,
            "last_scraped_at": datetime.utcnow().isoformat() if items_scraped > 0 else None
        }
        cache_service.set(f"spider_job:{job_id}", status_data, ttl=86400)  # 24 hours
        
    except subprocess.TimeoutExpired:
        # Get item count before timeout (items scraped since job started)
        final_count = bq_service.count_products_by_site(spider_name, since=start_time)
        items_scraped = max(0, final_count)
        status_data = {
            "job_id": job_id,
            "spider_name": spider_name,
            "status": "failed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": "Spider execution timeout",
            "items_scraped": items_scraped,
            "last_scraped_at": datetime.utcnow().isoformat() if items_scraped > 0 else None
        }
        cache_service.set(f"spider_job:{job_id}", status_data, ttl=86400)
    except Exception as e:
        logger.error(f"Error running spider {spider_name}: {e}", exc_info=True)
        # Get item count before error (items scraped since job started)
        try:
            final_count = bq_service.count_products_by_site(spider_name, since=start_time)
            items_scraped = max(0, final_count)
        except:
            items_scraped = 0
        status_data = {
            "job_id": job_id,
            "spider_name": spider_name,
            "status": "failed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "items_scraped": items_scraped,
            "last_scraped_at": datetime.utcnow().isoformat() if items_scraped > 0 else None
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
    """Get spider job status with real-time item count"""
    try:
        status_data = cache_service.get(f"spider_job:{job_id}")
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # If spider is running, update items_scraped count in real-time
        if status_data.get("status") == "running":
            from app.services.bigquery_service import BigQueryService
            bq_service = BigQueryService()
            
            try:
                # Calculate items scraped since job started
                start_time_str = status_data.get("created_at")
                initial_count = status_data.get("initial_count", 0)
                
                if start_time_str:
                    from datetime import datetime
                    try:
                        # Parse start time (handle both with and without timezone)
                        start_time_str_clean = start_time_str.replace('Z', '+00:00')
                        if '+' not in start_time_str_clean and start_time_str_clean.count(':') == 2:
                            # No timezone, assume UTC
                            start_time = datetime.fromisoformat(start_time_str_clean)
                        else:
                            start_time = datetime.fromisoformat(start_time_str_clean)
                        
                        # Count products scraped since job started (not total, just in this session)
                        current_count = bq_service.count_products_by_site(status_data["spider_name"], since=start_time)
                        items_scraped = max(0, current_count)
                        
                        status_data["items_scraped"] = items_scraped
                        if items_scraped > 0:
                            status_data["last_scraped_at"] = datetime.utcnow().isoformat()
                        
                        # Update cache with latest count
                        cache_service.set(f"spider_job:{job_id}", status_data, ttl=3600)
                    except Exception as parse_error:
                        logger.warning(f"Could not parse start time for progress tracking: {parse_error}")
            except Exception as e:
                logger.warning(f"Could not update item count for job {job_id}: {e}")
        
        return SpiderStatusResponse(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spider status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

