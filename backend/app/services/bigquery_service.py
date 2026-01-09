"""
BigQuery service for CrossRetail
"""
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class BigQueryService:
    """Service for BigQuery operations"""
    
    def __init__(self):
        self.dataset = os.getenv('BQ_DATASET', 'retail_intelligence')
        self.table = os.getenv('BQ_TABLE', 'products')
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        
        # Set credentials if provided
        if self.credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
        
        try:
            self.client = bigquery.Client()
            logger.info(f"BigQuery Service initialized. Dataset: {self.dataset}, Table: {self.table}")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    def search_products(
        self,
        query: Optional[str] = None,
        brands: Optional[List[str]] = None,
        retailers: Optional[List[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Search products with filters
        
        Returns:
            Dict with 'data' (list of products) and 'meta' (pagination info)
        """
        offset = (page - 1) * per_page
        
        sql = f"""
        SELECT DISTINCT
          product_id,
          site,
          url,
          title,
          description,
          price,
          currency,
          rating,
          review_count,
          availability,
          CASE 
            WHEN ARRAY_LENGTH(image_urls) > 0 THEN image_urls[OFFSET(0)]
            ELSE NULL
          END as image_url,
          image_urls,
          scraped_at,
          brand,
          model,
          category,
          sku
        FROM `{self.dataset}.{self.table}`
        WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if query:
            sql += " AND LOWER(title) LIKE LOWER(@query)"
            params.append(bigquery.ScalarQueryParameter("query", "STRING", f"%{query}%"))
        
        if brands and len(brands) > 0:
            sql += " AND brand IN UNNEST(@brands)"
            params.append(bigquery.ArrayQueryParameter("brands", "STRING", brands))
        
        if retailers and len(retailers) > 0:
            sql += " AND site IN UNNEST(@retailers)"
            params.append(bigquery.ArrayQueryParameter("retailers", "STRING", retailers))
        
        if min_price is not None:
            sql += " AND price >= @min_price"
            params.append(bigquery.ScalarQueryParameter("min_price", "FLOAT", min_price))
        
        if max_price is not None:
            sql += " AND price <= @max_price"
            params.append(bigquery.ScalarQueryParameter("max_price", "FLOAT", max_price))
        
        # Get total count
        count_sql = f"SELECT COUNT(DISTINCT product_id) as total FROM ({sql})"
        
        # Add ordering and pagination
        sql += " ORDER BY price ASC NULLS LAST, scraped_at DESC"
        sql += f" LIMIT @limit OFFSET @offset"
        params.extend([
            bigquery.ScalarQueryParameter("limit", "INT64", per_page),
            bigquery.ScalarQueryParameter("offset", "INT64", offset)
        ])
        
        try:
            # Execute count query
            count_job_config = bigquery.QueryJobConfig(query_parameters=params[:-2])
            count_query_job = self.client.query(count_sql, job_config=count_job_config)
            count_result = list(count_query_job.result())[0]
            total = count_result.total
            
            # Execute main query
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = self.client.query(sql, job_config=job_config)
            results = [dict(row) for row in query_job]
            
            return {
                "data": results,
                "meta": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page
                }
            }
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            raise
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get single product by ID"""
        sql = f"""
        SELECT 
          product_id,
          site,
          url,
          title,
          description,
          price,
          currency,
          rating,
          review_count,
          availability,
          image_urls,
          scraped_at,
          brand,
          model,
          category,
          sku,
          gcs_path
        FROM `{self.dataset}.{self.table}`
        WHERE product_id = @product_id
        ORDER BY scraped_at DESC
        LIMIT 1
        """
        
        params = [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)]
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            query_job = self.client.query(sql, job_config=job_config)
            results = list(query_job.result())
            if results:
                return dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            raise
    
    def compare_products(self, product_ids: List[str]) -> List[Dict]:
        """
        Compare products across retailers
        
        Returns list of products with retailer information
        """
        sql = f"""
        WITH latest_prices AS (
          SELECT 
            product_id,
            site,
            url,
            title,
            description,
            price,
            currency,
            rating,
            review_count,
            availability,
            CASE 
              WHEN ARRAY_LENGTH(image_urls) > 0 THEN image_urls[OFFSET(0)]
              ELSE NULL
            END as image_url,
            scraped_at,
            brand,
            model,
            ROW_NUMBER() OVER (PARTITION BY product_id, site ORDER BY scraped_at DESC) as rn
          FROM `{self.dataset}.{self.table}`
          WHERE product_id IN UNNEST(@product_ids)
        )
        SELECT 
          product_id,
          site,
          url,
          title,
          description,
          price,
          currency,
          rating,
          review_count,
          availability,
          image_url,
          scraped_at,
          brand,
          model
        FROM latest_prices
        WHERE rn = 1
        ORDER BY product_id, price ASC NULLS LAST
        """
        
        params = [bigquery.ArrayQueryParameter("product_ids", "STRING", product_ids)]
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            query_job = self.client.query(sql, job_config=job_config)
            return [dict(row) for row in query_job]
        except Exception as e:
            logger.error(f"Error comparing products: {e}")
            raise
    
    def get_arbitrage_opportunities(
        self,
        min_margin_pct: float = 10.0,
        min_price_diff: float = 5.0,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get arbitrage opportunities
        
        Uses a view if available, otherwise calculates on the fly
        """
        # Try to use materialized view first
        view_sql = f"""
        SELECT *
        FROM `{self.dataset}.arbitrage_opportunities`
        WHERE profit_margin_pct >= @min_margin
          AND price_diff >= @min_diff
        ORDER BY profit_margin_pct DESC
        LIMIT @limit
        """
        
        params = [
            bigquery.ScalarQueryParameter("min_margin", "FLOAT", min_margin_pct),
            bigquery.ScalarQueryParameter("min_diff", "FLOAT", min_price_diff),
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        ]
        
        try:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = self.client.query(view_sql, job_config=job_config)
            results = [dict(row) for row in query_job]
            
            # If view doesn't exist or returns no results, calculate on the fly
            if not results:
                return self._calculate_arbitrage_opportunities(
                    min_margin_pct, min_price_diff, limit
                )
            
            return results
        except NotFound:
            # View doesn't exist, calculate on the fly
            logger.info("Arbitrage opportunities view not found, calculating on the fly")
            return self._calculate_arbitrage_opportunities(
                min_margin_pct, min_price_diff, limit
            )
        except Exception as e:
            logger.error(f"Error getting arbitrage opportunities: {e}")
            raise
    
    def _calculate_arbitrage_opportunities(
        self,
        min_margin_pct: float,
        min_price_diff: float,
        limit: int
    ) -> List[Dict]:
        """Calculate arbitrage opportunities on the fly"""
        sql = f"""
        WITH latest_prices AS (
          SELECT 
            product_id,
            title,
            site,
            price,
            ROW_NUMBER() OVER (PARTITION BY product_id, site ORDER BY scraped_at DESC) as rn
          FROM `{self.dataset}.{self.table}`
          WHERE price IS NOT NULL
            AND scraped_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        ),
        price_comparison AS (
          SELECT 
            product_id,
            title,
            MIN(price) as min_price,
            MAX(price) as max_price,
            MAX(price) - MIN(price) as price_diff,
            (MAX(price) - MIN(price)) / MIN(price) * 100 as profit_margin_pct,
            COUNT(DISTINCT site) as retailer_count,
            ARRAY_AGG(site ORDER BY price LIMIT 1)[OFFSET(0)] as cheapest_retailer,
            ARRAY_AGG(site ORDER BY price DESC LIMIT 1)[OFFSET(0)] as expensive_retailer
          FROM latest_prices
          WHERE rn = 1
          GROUP BY product_id, title
          HAVING profit_margin_pct >= @min_margin
            AND price_diff >= @min_diff
        )
        SELECT *
        FROM price_comparison
        ORDER BY profit_margin_pct DESC
        LIMIT @limit
        """
        
        params = [
            bigquery.ScalarQueryParameter("min_margin", "FLOAT", min_margin_pct),
            bigquery.ScalarQueryParameter("min_diff", "FLOAT", min_price_diff),
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = self.client.query(sql, job_config=job_config)
        return [dict(row) for row in query_job]
    
    def get_price_history(
        self,
        product_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Get price history for a product"""
        sql = f"""
        SELECT 
          DATE(scraped_at) as date,
          site,
          AVG(price) as price,
          MAX(currency) as currency
        FROM `{self.dataset}.{self.table}`
        WHERE product_id = @product_id
          AND price IS NOT NULL
          AND scraped_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        GROUP BY DATE(scraped_at), site
        ORDER BY date ASC, site ASC
        """
        
        params = [
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("days", "INT64", days)
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            query_job = self.client.query(sql, job_config=job_config)
            return [dict(row) for row in query_job]
        except Exception as e:
            logger.error(f"Error getting price history for {product_id}: {e}")
            raise
    
    def get_brands(self) -> List[Dict]:
        """Get distinct brands with counts"""
        sql = f"""
        SELECT 
          brand,
          COUNT(DISTINCT product_id) as count
        FROM `{self.dataset}.{self.table}`
        WHERE brand IS NOT NULL
          AND brand != ''
        GROUP BY brand
        ORDER BY count DESC, brand ASC
        LIMIT 100
        """
        
        try:
            query_job = self.client.query(sql)
            return [dict(row) for row in query_job]
        except Exception as e:
            logger.error(f"Error getting brands: {e}")
            raise

