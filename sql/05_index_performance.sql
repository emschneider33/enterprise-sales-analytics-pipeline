
USE enterprise_sales_ops;

-- Examine query performance before indexing

EXPLAIN
SELECT *
FROM orders
WHERE updated_at >= '2026-10-01'
  AND updated_at < '2026-11-01';
  

CREATE INDEX idx_orders_updated_at
ON orders(updated_at);

EXPLAIN
SELECT *
FROM orders
WHERE updated_at >= '2026-10-01'
  AND updated_at < '2026-11-01';

