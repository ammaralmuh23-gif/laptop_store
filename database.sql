CREATE DATABASE IF NOT EXISTS laptop_store CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE laptop_store;

-- 1. جدول اللابتوبات
CREATE TABLE IF NOT EXISTS laptops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specs TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول المديرين
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- 3. جدول الزبائن
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. جدول سلة المشتريات
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    laptop_id INT NOT NULL,
    quantity INT DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (laptop_id) REFERENCES laptops(id) ON DELETE CASCADE
);

-- 5. جدول الإعدادات (رقم الواتساب والبريد)
CREATE TABLE IF NOT EXISTS settings (
    id INT PRIMARY KEY,
    whatsapp_number VARCHAR(20) NOT NULL,
    admin_email VARCHAR(100) DEFAULT 'ammaralmuh23@gmail.com'
);
-- جدول الطلبات الرئيسي
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- جدول تفاصيل الطلب (المنتجات داخل الطلب)
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    laptop_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (laptop_id) REFERENCES laptops(id) ON DELETE CASCADE
);

ALTER TABLE orders ADD COLUMN is_hidden TINYINT(1) DEFAULT 0;

ALTER TABLE laptops MODIFY COLUMN image_url LONGTEXT;
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM laptops;
ALTER TABLE orders AUTO_INCREMENT = 1;
ALTER TABLE laptops AUTO_INCREMENT = 1;
-- حذف الجدول بالكامل
DROP TABLE IF EXISTS laptops;

-- إعادة إنشاء الجدول من جديد
CREATE TABLE laptops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specs TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    image_url LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- إدخال بيانات افتراضية
INSERT IGNORE INTO admins (username, password) VALUES ('admin', 'admin123');
INSERT IGNORE INTO settings (id, whatsapp_number) VALUES (1, '966500000000');

