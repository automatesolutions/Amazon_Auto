"""
Google Cloud Storage service for CrossRetail
"""
import os
import logging
from typing import Optional
from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class GCSService:
    """Service for GCS operations"""
    
    def __init__(self):
        self.bucket_name = os.getenv('GCS_BUCKET_NAME', '')
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        
        if not self.bucket_name:
            logger.warning("GCS_BUCKET_NAME not set. GCS service disabled.")
            self.storage_client = None
            self.bucket = None
            return
        
        # Set credentials if provided
        if self.credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
        
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.bucket_name)
            logger.info(f"GCS Service initialized. Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            self.storage_client = None
            self.bucket = None
    
    def get_signed_url(self, gcs_path: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate signed URL for GCS object
        
        Args:
            gcs_path: Path to object in GCS (e.g., 'raw/amazon/2024-01-01/product123.html')
            expiration: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed URL or None if error
        """
        if not self.bucket:
            return None
        
        try:
            blob = self.bucket.blob(gcs_path)
            if not blob.exists():
                logger.warning(f"GCS object does not exist: {gcs_path}")
                return None
            
            url = blob.generate_signed_url(
                expiration=expiration,
                method='GET'
            )
            return url
        except NotFound:
            logger.warning(f"GCS object not found: {gcs_path}")
            return None
        except Exception as e:
            logger.error(f"Error generating signed URL for {gcs_path}: {e}")
            return None
    
    def get_image_url(self, gcs_path: str) -> Optional[str]:
        """Get signed URL for product image (shorter expiration)"""
        return self.get_signed_url(gcs_path, expiration=1800)  # 30 minutes
    
    def get_raw_html_url(self, gcs_path: str) -> Optional[str]:
        """Get signed URL for raw HTML (longer expiration)"""
        return self.get_signed_url(gcs_path, expiration=3600)  # 1 hour

