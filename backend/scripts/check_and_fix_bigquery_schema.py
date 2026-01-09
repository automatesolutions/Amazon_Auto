"""
Check and fix BigQuery table schema
This script verifies the table has all required columns and adds missing ones.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

def main():
    # Get configuration
    project_id = os.getenv('GCP_PROJECT_ID', 'scrapy-retail-intelligence')
    dataset_id = os.getenv('BQ_DATASET', 'retail_intelligence')
    table_id = os.getenv('BQ_TABLE', 'products')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
    
    if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)
    table_ref = client.dataset(dataset_id).table(table_id)
    
    # Expected schema
    expected_schema = [
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
        bigquery.SchemaField('gcs_path', 'STRING'),
        bigquery.SchemaField('brand', 'STRING'),
        bigquery.SchemaField('model', 'STRING'),
        bigquery.SchemaField('category', 'STRING'),
        bigquery.SchemaField('sku', 'STRING'),
    ]
    
    try:
        # Get current table
        table = client.get_table(table_ref)
        print(f"[OK] Table {dataset_id}.{table_id} exists")
        print(f"\nCurrent schema has {len(table.schema)} fields:")
        current_field_names = [field.name for field in table.schema]
        for field in table.schema:
            print(f"  - {field.name} ({field.field_type})")
        
        # Check for missing fields
        expected_field_names = [field.name for field in expected_schema]
        missing_fields = [f for f in expected_field_names if f not in current_field_names]
        
        if missing_fields:
            print(f"\n[WARNING] Missing fields: {', '.join(missing_fields)}")
            print("\nAdding missing fields...")
            
            # Add missing fields
            new_fields = [f for f in expected_schema if f.name in missing_fields]
            table.schema = list(table.schema) + new_fields
            table = client.update_table(table, ['schema'])
            
            print(f"[OK] Added {len(missing_fields)} field(s) to the table")
        else:
            print("\n[OK] All required fields are present!")
        
        # Verify final schema
        table = client.get_table(table_ref)
        print(f"\nFinal schema has {len(table.schema)} fields:")
        for field in table.schema:
            print(f"  - {field.name} ({field.field_type})")
        
    except NotFound:
        print(f"[ERROR] Table {dataset_id}.{table_id} does not exist!")
        print("\nCreating table with full schema...")
        
        # Create table with full schema
        table = bigquery.Table(table_ref, schema=expected_schema)
        table = client.create_table(table)
        print(f"[OK] Created table {dataset_id}.{table_id}")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

