
USE enterprise_sales_ops;

-- ============================================
-- WEEK 0 - LESSON 7
-- HISTORICAL TIMESTAMP CORRECTION
-- Run once before beginning incremental loads
-- ============================================


-- STEP 1: CHECK CURRENT TIMESTAMPS
SELECT
    COUNT(*) AS total_orders,
    MIN(order_date) AS earliest_order,
    MAX(order_date) AS latest_order,
    MIN(created_at) AS earliest_created,
    MAX(created_at) AS latest_created,
    MIN(updated_at) AS earliest_updated,
    MAX(updated_at) AS latest_updated,
    SUM(created_at > order_date) AS created_after_order_date
FROM orders;


-- ============================================
-- STEP 2: UPDATE HISTORICAL ORDER TIMESTAMPS
-- ============================================

-- Temporarily disable safe updates for this session
SET @previous_safe_updates = @@SQL_SAFE_UPDATES;
SET SQL_SAFE_UPDATES = 0;

-- Set creation and update timestamps to order date
UPDATE orders
SET
    created_at = order_date,
    updated_at = order_date;


-- ============================================
-- STEP 3: SIMULATE HISTORICAL MODIFICATIONS
-- ============================================

-- Modify approximately 20% of orders
-- Add 1 to 7 days to their updated_at timestamp
-- Cap at the simulation cutoff: November 6, 2026

UPDATE orders
SET updated_at = LEAST(
    DATE_ADD(
        order_date,
        INTERVAL (1 + MOD(order_id, 7)) DAY
    ),
    '2026-11-06 23:59:59'
)
WHERE MOD(order_id, 5) = 0;


-- ============================================
-- STEP 4: UPDATE ORDER ITEM TIMESTAMPS
-- ============================================

-- Match order-item timestamps to parent orders

UPDATE order_items oi
JOIN orders o
    ON oi.order_id = o.order_id
SET
    oi.created_at = o.created_at,
    oi.updated_at = o.updated_at;


-- Restore the previous safe update setting
SET SQL_SAFE_UPDATES = @previous_safe_updates;


-- ============================================
-- STEP 5: VALIDATE ORDER TIMESTAMPS
-- ============================================

SELECT
    COUNT(*) AS total_orders,
    MIN(created_at) AS earliest_created,
    MAX(created_at) AS latest_created,
    MIN(updated_at) AS earliest_updated,
    MAX(updated_at) AS latest_updated,
    SUM(updated_at < created_at) AS invalid_timestamps,
    SUM(updated_at > created_at) AS modified_orders
FROM orders;


-- ============================================
-- STEP 6: VALIDATE ORDER ITEM TIMESTAMPS
-- ============================================

SELECT
    COUNT(*) AS total_order_items,
    MIN(created_at) AS earliest_created,
    MAX(created_at) AS latest_created,
    MIN(updated_at) AS earliest_updated,
    MAX(updated_at) AS latest_updated,
    SUM(updated_at < created_at) AS invalid_timestamps
FROM order_items;


-- ============================================
-- STEP 7: INSPECT SAMPLE RECORDS
-- ============================================

SELECT
    order_id,
    order_date,
    created_at,
    updated_at,
    order_status
FROM orders
ORDER BY order_id
LIMIT 20;
