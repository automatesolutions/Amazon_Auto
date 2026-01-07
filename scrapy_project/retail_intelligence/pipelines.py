"""
Scrapy pipelines for retail_intelligence project
"""
import os
import logging
import json
from datetime import datetime
from urllib.parse import urlparse
from scrapy import signals
from google.cloud import storage
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class GCSRawHTMLPipeline:
    """
    Pipeline for uploading raw HTML responses to Google Cloud Storage.
    Organizes files by date/site/product_id for easy retrieval and auditing.
    """
    
    def __init__(self, gcs_bucket_name, gcs_credentials_path):
        self.gcs_bucket_name = gcs_bucket_name
        self.gcs_credentials_path = gcs_credentials_path
        self.storage_client = None
        self.bucket = None
        
        if not gcs_bucket_name:
            raise ValueError('GCS_BUCKET_NAME environment variable not set')
        
        # Initialize GCS client
        if gcs_credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gcs_credentials_path
        
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(gcs_bucket_name)
            logger.info(f'GCS Pipeline initialized. Bucket: {gcs_bucket_name}')
        except Exception as e:
            logger.error(f'Failed to initialize GCS client: {e}')
            raise
    
    @classmethod
    def from_crawler(cls, crawler):
        gcs_bucket_name = crawler.settings.get('GCS_BUCKET_NAME', '')
        gcs_credentials_path = crawler.settings.get('GOOGLE_APPLICATION_CREDENTIALS', '')
        return cls(gcs_bucket_name, gcs_credentials_path)
    
    def process_item(self, item, spider):
        """Upload raw HTML to GCS"""
        if 'raw_html' not in item or not item['raw_html']:
            logger.warning('No raw_html field in item, skipping GCS upload')
            return item
        
        try:
            # Extract metadata
            site = item.get('site', 'unknown')
            product_id = item.get('product_id', 'unknown')
            scraped_at = item.get('scraped_at', datetime.utcnow().isoformat())
            
            # Parse date from scraped_at (format: YYYY-MM-DD)
            try:
                date_str = datetime.fromisoformat(scraped_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except:
                date_str = datetime.utcnow().strftime('%Y-%m-%d')
            
            # Construct GCS path: raw/{site}/{date}/{product_id}.html
            blob_name = f'raw/{site}/{date_str}/{product_id}.html'
            
            # Upload to GCS
            blob = self.bucket.blob(blob_name)
            blob.content_type = 'text/html'
            blob.upload_from_string(item['raw_html'], content_type='text/html')
            
            logger.debug(f'Uploaded raw HTML to GCS: gs://{self.gcs_bucket_name}/{blob_name}')
            
            # Store GCS path in item metadata (optional)
            item['gcs_path'] = blob_name
            
        except Exception as e:
            logger.error(f'Failed to upload raw HTML to GCS: {e}')
            # Don't fail the item, just log the error
        
        return item


class BigQueryAnalyticsPipeline:
    """
    Pipeline for cleaning, normalizing, and streaming scraped data to BigQuery.
    Handles schema evolution and batch inserts for efficiency.
    """
    
    def __init__(self, bq_dataset, bq_table, gcs_credentials_path):
        self.bq_dataset = bq_dataset
        self.bq_table = bq_table
        self.gcs_credentials_path = gcs_credentials_path
        self.bq_client = None
        self.table_ref = None
        self.batch = []
        self.batch_size = 100  # Insert in batches
        
        if not bq_dataset or not bq_table:
            raise ValueError('BQ_DATASET and BQ_TABLE environment variables must be set')
        
        # Initialize BigQuery client
        if gcs_credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gcs_credentials_path
        
        try:
            self.bq_client = bigquery.Client()
            self.table_ref = self.bq_client.dataset(bq_dataset).table(bq_table)
            
            # Ensure table exists
            self._ensure_table_exists()
            
            logger.info(f'BigQuery Pipeline initialized. Table: {bq_dataset}.{bq_table}')
        except Exception as e:
            logger.error(f'Failed to initialize BigQuery client: {e}')
            raise
    
    @classmethod
    def from_crawler(cls, crawler):
        bq_dataset = crawler.settings.get('BQ_DATASET', '')
        bq_table = crawler.settings.get('BQ_TABLE', '')
        gcs_credentials_path = crawler.settings.get('GOOGLE_APPLICATION_CREDENTIALS', '')
        pipeline = cls(bq_dataset, bq_table, gcs_credentials_path)
        crawler.signals.connect(pipeline.close_spider, signal=signals.spider_closed)
        return pipeline
    
    def process_item(self, item, spider):
        """Clean and add item to batch for BigQuery insertion"""
        try:
            # Clean and normalize item using schema mapper
            from retail_intelligence.utils.schema_mapper import SchemaMapper
            mapper = SchemaMapper()
            normalized_item = mapper.normalize_item(item)
            
            # Add to batch
            self.batch.append(normalized_item)
            
            # Insert batch if it reaches batch_size
            if len(self.batch) >= self.batch_size:
                self._insert_batch()
            
        except Exception as e:
            logger.error(f'Failed to process item for BigQuery: {e}')
        
        return item
    
    def close_spider(self, spider):
        """Insert remaining batch items when spider closes"""
        if self.batch:
            self._insert_batch()
    
    def _ensure_table_exists(self):
        """Create table if it doesn't exist, or update schema if it exists without one"""
        try:
            table = self.bq_client.get_table(self.table_ref)
            # Check if table has schema
            if not table.schema:
                logger.warning(f'Table {self.bq_dataset}.{self.bq_table} exists but has no schema. Updating...')
                schema = self._get_table_schema()
                table.schema = schema
                table = self.bq_client.update_table(table, ['schema'])
                logger.info(f'Updated table {self.bq_dataset}.{self.bq_table} with schema')
            else:
                logger.info(f'Table {self.bq_dataset}.{self.bq_table} already exists')
        except NotFound:
            # Create table with schema
            schema = self._get_table_schema()
            table = bigquery.Table(self.table_ref, schema=schema)
            table = self.bq_client.create_table(table)
            logger.info(f'Created table {self.bq_dataset}.{self.bq_table}')
    
    def _get_table_schema(self):
        """Define BigQuery table schema"""
        return [
            bigquery.SchemaField('product_id', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('site', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('url', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('title', 'STRING'),
            bigquery.SchemaField('description', 'STRING'),
            bigquery.SchemaField('price', 'FLOAT'),
            bigquery.SchemaField('currency', 'STRING'),
            bigquery.SchemaField('rating', 'FLOAT'),
            bigquery.SchemaField('review_count', 'INTEGER'),
            bigquery.SchemaField('availability', 'STRING'),
            bigquery.SchemaField('image_urls', 'STRING', mode='REPEATED'),
            bigquery.SchemaField('scraped_at', 'TIMESTAMP', mode='REQUIRED'),
            bigquery.SchemaField('gcs_path', 'STRING'),  # Reference to raw HTML in GCS
        ]
    
    def _insert_batch(self):
        """Insert batch of items into BigQuery"""
        if not self.batch:
            return
        
        try:
            errors = self.bq_client.insert_rows_json(self.table_ref, self.batch)
            
            if errors:
                logger.error(f'BigQuery insertion errors: {errors}')
            else:
                logger.info(f'Successfully inserted {len(self.batch)} rows into BigQuery')
            
            # Clear batch
            self.batch = []
            
        except Exception as e:
            logger.error(f'Failed to insert batch into BigQuery: {e}')
            # Clear batch to prevent retry loops
            self.batch = []

