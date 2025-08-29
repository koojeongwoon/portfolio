SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

CREATE TABLE `brand` (
  `brand_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(200),
  `slug` VARCHAR(220),
  `status` ENUM('DRAFT','ACTIVE','ARCHIVED') DEFAULT 'DRAFT',
  PRIMARY KEY (`brand_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `category` (
  `category_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `parent_id` BIGINT UNSIGNED,
  `name` VARCHAR(200),
  `slug` VARCHAR(220),
  PRIMARY KEY (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `product` (
  `product_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `brand_id` BIGINT UNSIGNED,
  `name` VARCHAR(200),
  `slug` VARCHAR(220),
  `status` ENUM('DRAFT','ACTIVE','ARCHIVED') DEFAULT 'DRAFT',
  PRIMARY KEY (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `product_category` (
  `product_id` BIGINT UNSIGNED NOT NULL,
  `category_id` BIGINT UNSIGNED NOT NULL,
  `is_primary` VARCHAR(255),
  PRIMARY KEY (`product_id`, `category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `product_image` (
  `image_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id` BIGINT UNSIGNED,
  `url` VARCHAR(500),
  `sort_order` INT,
  PRIMARY KEY (`image_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `product_variant` (
  `variant_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id` BIGINT UNSIGNED,
  `sku` VARCHAR(80),
  `price` DECIMAL(12,2),
  `status` ENUM('DRAFT','ACTIVE','ARCHIVED') DEFAULT 'DRAFT',
  PRIMARY KEY (`variant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `inventory` (
  `variant_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `qty_on_hand` INT,
  `qty_reserved` INT,
  PRIMARY KEY (`variant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `brand` ADD INDEX `ix_brand_status` (`status`);
ALTER TABLE `product` ADD INDEX `ix_product_status` (`status`);
ALTER TABLE `product_variant` ADD INDEX `ix_product_variant_status` (`status`);
ALTER TABLE `category` ADD INDEX `ix_category_parent_id` (`parent_id`);
ALTER TABLE `product` ADD INDEX `ix_product_brand_id` (`brand_id`);
ALTER TABLE `product_category` ADD INDEX `ix_product_category_product_id` (`product_id`);
ALTER TABLE `product_category` ADD INDEX `ix_product_category_category_id` (`category_id`);
ALTER TABLE `product_image` ADD INDEX `ix_product_image_product_id` (`product_id`);
ALTER TABLE `product_variant` ADD INDEX `ix_product_variant_product_id` (`product_id`);
ALTER TABLE `inventory` ADD INDEX `ix_inventory_variant_id` (`variant_id`);

ALTER TABLE `brand` ADD CONSTRAINT `chk_brand_slug_1` CHECK (CHAR_LENGTH(`slug`) <= 220);
ALTER TABLE `category` ADD CONSTRAINT `chk_category_slug_1` CHECK (CHAR_LENGTH(`slug`) <= 220);
ALTER TABLE `product` ADD CONSTRAINT `chk_product_slug_1` CHECK (CHAR_LENGTH(`slug`) <= 220);
ALTER TABLE `product_variant` ADD CONSTRAINT `chk_product_variant_price_1` CHECK (`price` >= 0);

ALTER TABLE `category` ADD CONSTRAINT `fk_category_parent_id_category` FOREIGN KEY (`parent_id`) REFERENCES `category`(`category_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `product` ADD CONSTRAINT `fk_product_brand_id_brand` FOREIGN KEY (`brand_id`) REFERENCES `brand`(`brand_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `product_category` ADD CONSTRAINT `fk_product_category_product_id_product` FOREIGN KEY (`product_id`) REFERENCES `product`(`product_id`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `product_category` ADD CONSTRAINT `fk_product_category_category_id_category` FOREIGN KEY (`category_id`) REFERENCES `category`(`category_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `product_image` ADD CONSTRAINT `fk_product_image_product_id_product` FOREIGN KEY (`product_id`) REFERENCES `product`(`product_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `product_variant` ADD CONSTRAINT `fk_product_variant_product_id_product` FOREIGN KEY (`product_id`) REFERENCES `product`(`product_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `inventory` ADD CONSTRAINT `fk_inventory_variant_id_product_variant` FOREIGN KEY (`variant_id`) REFERENCES `product_variant`(`variant_id`) ON DELETE CASCADE ON UPDATE CASCADE;

SET FOREIGN_KEY_CHECKS=1;