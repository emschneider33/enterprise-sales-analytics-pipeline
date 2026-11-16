
CREATE TABLE territories (
    territory_id INT AUTO_INCREMENT PRIMARY KEY,
    territory_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_reps (
    sales_rep_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(150) UNIQUE,
    territory_id INT NOT NULL,
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sales_rep_territory
        FOREIGN KEY (territory_id)
        REFERENCES territories(territory_id)
);

INSERT INTO territories (territory_name, region)
VALUES
    ('Charlotte Metro', 'Southeast'),
    ('Atlanta Metro', 'Southeast'),
    ('New York Metro', 'Northeast'),
    ('Dallas Metro', 'South Central');

INSERT INTO sales_reps
    (first_name, last_name, email, territory_id, hire_date)
VALUES
    ('John', 'Smith', 'john.smith@example.com', 1, '2022-03-15'),
    ('Sarah', 'Johnson', 'sarah.johnson@example.com', 1, '2021-06-01'),
    ('Michael', 'Brown', 'michael.brown@example.com', 2, '2023-01-10');
    
    
    

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    customer_type VARCHAR(50),
    industry VARCHAR(100),
    email VARCHAR(150),
    phone VARCHAR(30),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(15),
    sales_rep_id INT,
    customer_status VARCHAR(20) DEFAULT 'Active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_customer_sales_rep
        FOREIGN KEY (sales_rep_id)
        REFERENCES sales_reps(sales_rep_id)
);


CREATE TABLE product_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    category_description VARCHAR(255)
);

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL,
    list_price DECIMAL(12,2) NOT NULL,
    product_status VARCHAR(20) DEFAULT 'Active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id)
        REFERENCES product_categories(category_id)
);


CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    order_channel VARCHAR(30),
    shipping_amount DECIMAL(12,2) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);


CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    discount_pct DECIMAL(5,4) DEFAULT 0,
    unit_cost DECIMAL(12,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_item_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT fk_order_item_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);

