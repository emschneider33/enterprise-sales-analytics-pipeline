
SELECT
    'Orders without customers' AS quality_check,
    COUNT(*) AS failed_records
FROM orders o
LEFT JOIN customers c
    ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL

UNION ALL

SELECT
    'Order items without products',
    COUNT(*)
FROM order_items oi
LEFT JOIN products p
    ON oi.product_id = p.product_id
WHERE p.product_id IS NULL

UNION ALL

SELECT
    'Order items without orders',
    COUNT(*)
FROM order_items oi
LEFT JOIN orders o
    ON oi.order_id = o.order_id
WHERE o.order_id IS NULL

UNION ALL

SELECT
    'Invalid financial records',
    COUNT(*)
FROM order_items
WHERE quantity <= 0
   OR unit_price < 0
   OR unit_cost < 0
   OR discount_pct NOT BETWEEN 0 AND 1
   OR quantity IS NULL
   OR unit_price IS NULL
   OR unit_cost IS NULL
   OR discount_pct IS NULL;

