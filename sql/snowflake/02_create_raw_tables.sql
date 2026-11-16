
-- ============================================================
-- Enterprise Sales Data Pipeline
-- File: 02_create_raw_tables.sql
-- Purpose: Create RAW (Bronze) tables in Snowflake
--
-- Medallion Architecture:
--   Bronze = RAW       (source data from MySQL)
--   Silver = STAGING   (cleaned and validated data)
--   Gold   = ANALYTICS (business-ready reporting data)
-- ============================================================

USE DATABASE ENTERPRISE_SALES_DW;
USE SCHEMA RAW;


-- ============================================================
-- 1. RAW (Bronze): Territories
-- Source: MySQL enterprise_sales_ops.territories
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.TERRITORIES (
    TERRITORY_ID INT,
    TERRITORY_NAME VARCHAR(100),
    REGION VARCHAR(100),
    CREATED_AT TIMESTAMP_NTZ,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- 2. RAW (Bronze): Sales Representatives
-- Source: MySQL enterprise_sales_ops.sales_reps
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.SALES_REPS (
    SALES_REP_ID INT,
    FIRST_NAME VARCHAR(100),
    LAST_NAME VARCHAR(100),
    EMAIL VARCHAR(255),
    TERRITORY_ID INT,
    HIRE_DATE DATE,
    IS_ACTIVE BOOLEAN,
    CREATED_AT TIMESTAMP_NTZ,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- 3. RAW (Bronze): Customers
-- Source: MySQL enterprise_sales_ops.customers
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.CUSTOMERS (
    CUSTOMER_ID INT,
    CUSTOMER_NAME VARCHAR(255),
    CUSTOMER_TYPE VARCHAR(100),
    INDUSTRY VARCHAR(100),
    EMAIL VARCHAR(255),
    PHONE VARCHAR(50),
    CITY VARCHAR(100),
    STATE VARCHAR(50),
    ZIP_CODE VARCHAR(20),
    SALES_REP_ID INT,
    CUSTOMER_STATUS VARCHAR(50),
    CREATED_AT TIMESTAMP_NTZ,
    UPDATED_AT TIMESTAMP_NTZ,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- 4. RAW (Bronze): Product Categories
-- Source: MySQL enterprise_sales_ops.product_categories
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.PRODUCT_CATEGORIES (
    CATEGORY_ID INT,
    CATEGORY_NAME VARCHAR(100),
    CATEGORY_DESCRIPTION VARCHAR(500),
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- 5. RAW (Bronze): Products
-- Source: MySQL enterprise_sales_ops.products
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.PRODUCTS (
    PRODUCT_ID INT,
    PRODUCT_SKU VARCHAR(100),
    PRODUCT_NAME VARCHAR(255),
    CATEGORY_ID INT,
    UNIT_COST NUMBER(12,2),
    LIST_PRICE NUMBER(12,2),
    PRODUCT_STATUS VARCHAR(50),
    CREATED_AT TIMESTAMP_NTZ,
    UPDATED_AT TIMESTAMP_NTZ,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- 6. RAW (Bronze): Orders
-- Source: MySQL enterprise_sales_ops.orders
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.ORDERS (
    ORDER_ID INT,
    CUSTOMER_ID INT,
    ORDER_DATE DATE,
    ORDER_STATUS VARCHAR(50),
    ORDER_CHANNEL VARCHAR(50),
    SHIPPING_AMOUNT NUMBER(12,2),
    CREATED_AT TIMESTAMP_NTZ,
    UPDATED_AT TIMESTAMP_NTZ,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- 7. RAW (Bronze): Order Items
-- Source: MySQL enterprise_sales_ops.order_items
-- ============================================================

CREATE TABLE IF NOT EXISTS RAW.ORDER_ITEMS (
    ORDER_ITEM_ID INT,
    ORDER_ID INT,
    PRODUCT_ID INT,
    QUANTITY INT,
    UNIT_PRICE NUMBER(12,2),
    DISCOUNT_PCT NUMBER(10,4),
    UNIT_COST NUMBER(12,2),
    CREATED_AT TIMESTAMP_NTZ,
    UPDATED_AT TIMESTAMP_NTZ,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- ============================================================
-- Verification: List all RAW (Bronze) tables
-- ============================================================

SHOW TABLES IN SCHEMA ENTERPRISE_SALES_DW.RAW;
