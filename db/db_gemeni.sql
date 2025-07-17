-- SQL Schema for the Train Tracking Application
-- Generated based on the provided Flask-SQLAlchemy models.

-- Drop tables in reverse order of creation to avoid foreign key constraints
DROP TABLE IF EXISTS `report_validations`;
DROP TABLE IF EXISTS `calculated_times`;
DROP TABLE IF EXISTS `user_reports`;
DROP TABLE IF EXISTS `operations`;
DROP TABLE IF EXISTS `rewards`;
DROP TABLE IF EXISTS `user_favourite_trains`;
DROP TABLE IF EXISTS `user_notification_settings`;
DROP TABLE IF EXISTS `user_reliability`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `refresh_tokens`;
DROP TABLE IF EXISTS `routes`;
DROP TABLE IF EXISTS `trains`;
DROP TABLE IF EXISTS `stations`;
DROP TABLE IF EXISTS `users`;


-- Table: users
CREATE TABLE `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(255) NOT NULL UNIQUE,
    `email` VARCHAR(255) NOT NULL UNIQUE,
    `phone_number` VARCHAR(255) NOT NULL UNIQUE,
    `is_active` BOOLEAN DEFAULT TRUE,
    `date_joined` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `last_login` DATETIME,
    PRIMARY KEY (`id`)
);

-- Table: stations
CREATE TABLE `stations` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name_en` VARCHAR(255) NOT NULL,
    `name_ar` VARCHAR(255) NOT NULL,
    `code` VARCHAR(50),
    `location_lat` DECIMAL(9, 6),
    `location_long` DECIMAL(9, 6),
    PRIMARY KEY (`id`)
);

-- Table: trains
CREATE TABLE `trains` (
    `train_number` BIGINT NOT NULL,
    `train_type` VARCHAR(50),
    `departure_station_id` INT NOT NULL,
    `arrival_station_id` INT NOT NULL,
    `scheduled_departure_time` TIME NOT NULL,
    `scheduled_arrival_time` TIME NOT NULL,
    PRIMARY KEY (`train_number`),
    FOREIGN KEY(`departure_station_id`) REFERENCES `stations` (`id`),
    FOREIGN KEY(`arrival_station_id`) REFERENCES `stations` (`id`)
);

-- Table: routes
CREATE TABLE `routes` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `train_number` BIGINT NOT NULL,
    `station_id` INT NOT NULL,
    `sequence_number` INT NOT NULL,
    `scheduled_arrival_time` TIME,
    `scheduled_departure_time` TIME,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`train_number`) REFERENCES `trains` (`train_number`),
    FOREIGN KEY(`station_id`) REFERENCES `stations` (`id`)
);

-- Table: refresh_tokens
CREATE TABLE `refresh_tokens` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `token` VARCHAR(255) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`)
);

-- Table: notifications
CREATE TABLE `notifications` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `train_number` BIGINT,
    `title` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_read` BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`),
    FOREIGN KEY(`train_number`) REFERENCES `trains` (`train_number`)
);

-- Table: user_reliability
CREATE TABLE `user_reliability` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL UNIQUE,
    `reliability_score` FLOAT DEFAULT 0.6,
    `total_reports` INT DEFAULT 0,
    `accurate_reports` INT DEFAULT 0,
    `flagged_reports` INT DEFAULT 0,
    `spam_reports` INT DEFAULT 0,
    `last_updated` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `user_type` ENUM('admin', 'verified', 'regular', 'new', 'flagged') DEFAULT 'new',
    PRIMARY KEY (`id`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`)
);

-- Table: user_notification_settings
CREATE TABLE `user_notification_settings` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL UNIQUE,
    `notification_enabled` BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`)
);

-- Table: user_favourite_trains
CREATE TABLE `user_favourite_trains` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `train_number` BIGINT NOT NULL,
    `added_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE (`user_id`, `train_number`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`),
    FOREIGN KEY(`train_number`) REFERENCES `trains` (`train_number`)
);

-- Table: rewards
CREATE TABLE `rewards` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `points` INT NOT NULL,
    `date_awarded` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `description` VARCHAR(255),
    PRIMARY KEY (`id`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`)
);

-- Table: operations
CREATE TABLE `operations` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `train_number` BIGINT NOT NULL,
    `operational_date` DATE NOT NULL,
    `status` VARCHAR(50) DEFAULT 'on time',
    `total_delay` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`train_number`) REFERENCES `trains` (`train_number`)
);

-- Table: user_reports
CREATE TABLE `user_reports` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `train_number` BIGINT NOT NULL,
    `operation_id` INT NOT NULL,
    `station_id` INT NOT NULL,
    `report_type` ENUM('arrival', 'departure', 'onboard', 'offboard', 'passing', 'delayed', 'cancelled', 'no_show', 'early_arrival', 'breakdown') NOT NULL,
    `reported_time` DATETIME NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_valid` BOOLEAN DEFAULT TRUE,
    `confidence_score` FLOAT DEFAULT 0.5,
    `weight_factor` FLOAT DEFAULT 0.6,
    `validation_status` ENUM('pending', 'validated', 'rejected', 'flagged') DEFAULT 'pending',
    `reported_lat` DECIMAL(9, 6),
    `reported_long` DECIMAL(9, 6),
    `location_accuracy` FLOAT,
    `delay_minutes` INT,
    `notes` TEXT,
    `is_intermediate_station` BOOLEAN DEFAULT FALSE,
    `admin_verified` BOOLEAN DEFAULT FALSE,
    `admin_notes` TEXT,
    `verified_by` INT,
    `verified_at` DATETIME,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`user_id`) REFERENCES `users` (`id`),
    FOREIGN KEY(`operation_id`) REFERENCES `operations` (`id`),
    FOREIGN KEY(`station_id`) REFERENCES `stations` (`id`),
    FOREIGN KEY(`verified_by`) REFERENCES `users` (`id`)
);

-- Table: calculated_times
CREATE TABLE `calculated_times` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `train_number` BIGINT NOT NULL,
    `station_id` INT NOT NULL,
    `calculated_arrival_time` DATETIME,
    `calculated_departure_time` DATETIME,
    `scheduled_arrival_time` DATETIME,
    `scheduled_departure_time` DATETIME,
    `previous_arrival_time` DATETIME,
    `previous_departure_time` DATETIME,
    `number_of_reports` INT DEFAULT 0,
    `confidence_level` FLOAT DEFAULT 0.5,
    `weighted_reports` FLOAT DEFAULT 0.0,
    `status` ENUM('scheduled', 'estimated', 'confirmed', 'passed', 'cancelled', 'delayed') DEFAULT 'scheduled',
    `delay_minutes` INT DEFAULT 0,
    `last_updated` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `last_report_time` DATETIME,
    `update_count` INT DEFAULT 0,
    `admin_override` BOOLEAN DEFAULT FALSE,
    `admin_time` DATETIME,
    `admin_notes` TEXT,
    `overridden_by` INT,
    `overridden_at` DATETIME,
    PRIMARY KEY (`id`),
    FOREIGN KEY(`train_number`) REFERENCES `trains` (`train_number`),
    FOREIGN KEY(`station_id`) REFERENCES `stations` (`id`),
    FOREIGN KEY(`overridden_by`) REFERENCES `users` (`id`)
);

-- Table: report_validations
CREATE TABLE `report_validations` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `report_id` INT NOT NULL,
    `validation_type` ENUM('time_check', 'location_check', 'consistency_check', 'pattern_check', 'route_check', 'admin_review', 'rate_limit_check', 'duplicate_check') NOT NULL,
    `status` ENUM('passed', 'failed', 'warning') NOT NULL,
    `score` FLOAT NOT NULL,
    `weight` FLOAT DEFAULT 1.0,
    `details` TEXT,
    `error_message` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `processed_by` VARCHAR(100),
    PRIMARY KEY (`id`),
    FOREIGN KEY(`report_id`) REFERENCES `user_reports` (`id`)
);