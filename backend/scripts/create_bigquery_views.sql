-- BigQuery Materialized Views for CrossRetail
-- Run this script to create optimized views for common queries

-- Latest prices per product per retailer
CREATE MATERIALIZED VIEW IF NOT EXISTS `retail_intelligence.latest_prices`
PARTITION BY DATE(scraped_at)
CLUSTER BY product_id, site
AS
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
  gcs_path,
  ROW_NUMBER() OVER (
    PARTITION BY product_id, site 
    ORDER BY scraped_at DESC
  ) as rn
FROM `retail_intelligence.products`
WHERE scraped_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
QUALIFY rn = 1;

-- Arbitrage opportunities view
CREATE MATERIALIZED VIEW IF NOT EXISTS `retail_intelligence.arbitrage_opportunities`
PARTITION BY DATE(CURRENT_TIMESTAMP())
CLUSTER BY profit_margin_pct
AS
WITH latest AS (
  SELECT * FROM `retail_intelligence.latest_prices`
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
  FROM latest
  WHERE price IS NOT NULL
  GROUP BY product_id, title
  HAVING profit_margin_pct >= 5  -- Minimum 5% margin
    AND price_diff >= 1.0  -- Minimum $1 difference
)
SELECT *
FROM price_comparison
ORDER BY profit_margin_pct DESC;

-- Price history aggregated by day
CREATE MATERIALIZED VIEW IF NOT EXISTS `retail_intelligence.price_history_aggregated`
PARTITION BY date
CLUSTER BY product_id, site
AS
SELECT 
  product_id,
  DATE(scraped_at) as date,
  site,
  AVG(price) as avg_price,
  MIN(price) as min_price,
  MAX(price) as max_price,
  MAX(currency) as currency,
  COUNT(*) as data_points
FROM `retail_intelligence.products`
WHERE price IS NOT NULL
  AND scraped_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY product_id, DATE(scraped_at), site;

-- Product brands with counts
CREATE MATERIALIZED VIEW IF NOT EXISTS `retail_intelligence.product_brands`
AS
SELECT 
  brand,
  COUNT(DISTINCT product_id) as product_count,
  COUNT(DISTINCT site) as retailer_count,
  AVG(price) as avg_price,
  MIN(price) as min_price,
  MAX(price) as max_price
FROM `retail_intelligence.latest_prices`
WHERE brand IS NOT NULL
  AND brand != ''
GROUP BY brand
ORDER BY product_count DESC;

