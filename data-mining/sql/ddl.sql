USE db1;

-- Table: users (Updated with user_type and reliability_score)
DROP TABLE IF EXISTS users;
CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    device_token VARCHAR(255) NULL,
    user_type ENUM('admin', 'verified', 'regular', 'new', 'flagged') DEFAULT 'new' NOT NULL,
    reliability_score FLOAT DEFAULT 0.5 NOT NULL,
    INDEX (username),
    INDEX (email)
);

-- Table: stations (No changes)
DROP TABLE IF EXISTS stations;
CREATE TABLE IF NOT EXISTS stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name_en VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    location_lat DECIMAL(9,6),
    location_long DECIMAL(9,6),
    INDEX (name_en),
    INDEX (code)
);

-- Table: trains (Updated)
DROP TABLE IF EXISTS trains;
CREATE TABLE IF NOT EXISTS trains (
    train_number VARCHAR(255) PRIMARY KEY,
    train_type VARCHAR(50),
    departure_station_id INT NOT NULL,
    arrival_station_id INT NOT NULL,
    scheduled_departure_time TIME NOT NULL,
    scheduled_arrival_time TIME NOT NULL,
    CONSTRAINT fk_departure_station FOREIGN KEY (departure_station_id) REFERENCES stations(id),
    CONSTRAINT fk_arrival_station FOREIGN KEY (arrival_station_id) REFERENCES stations(id)
);

-- Table: routes (Updated)
DROP TABLE IF EXISTS routes;
CREATE TABLE IF NOT EXISTS routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number VARCHAR(255) NOT NULL,
    station_id INT NOT NULL,
    sequence_number INT NOT NULL,
    scheduled_arrival_time TIME,
    scheduled_departure_time TIME,
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (station_id) REFERENCES stations(id)
);

-- Table: operations (Updated)
DROP TABLE IF EXISTS operations;
CREATE TABLE operations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    train_number VARCHAR(255) NOT NULL,
    operational_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'on time',
    total_delay INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (train_number) REFERENCES trains(train_number)
);

-- Table: user_reports (Updated)
DROP TABLE IF EXISTS user_reports;
CREATE TABLE user_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    train_number VARCHAR(255) NOT NULL,
    operation_id INT NOT NULL,
    station_id INT NOT NULL,
    report_type ENUM('arrival', 'departure', 'onboard', 'offboard', 'delay', 'cancelled', 'passed_station') NOT NULL,
    reported_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT FALSE,
    report_location_lat DECIMAL(9, 6),
    report_location_long DECIMAL(9, 6),
    confidence_score FLOAT DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (operation_id) REFERENCES operations(id),
    FOREIGN KEY (station_id) REFERENCES stations(id)
);

-- Table: calculated_times (Updated)
DROP TABLE IF EXISTS calculated_times;
CREATE TABLE calculated_times (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number VARCHAR(255) NOT NULL,
    station_id INT NOT NULL,
    calculated_arrival_time DATETIME,
    calculated_departure_time DATETIME,
    number_of_reports INT DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (station_id) REFERENCES stations(id),
    INDEX (train_number, station_id)
);

-- Table: notifications (Updated)
DROP TABLE IF EXISTS notifications;
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    train_number VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    `time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (train_number) REFERENCES trains(train_number)
);

-- Table: rewards (No changes)
DROP TABLE IF EXISTS rewards;
CREATE TABLE rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    points INT NOT NULL,
    date_awarded DATETIME DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table: user_favourite_trains (Updated)
DROP TABLE IF EXISTS user_favourite_trains;
CREATE TABLE user_favourite_trains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    train_number VARCHAR(255) NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    UNIQUE KEY (user_id, train_number)
);

-- Table: user_notification_settings (No changes)
DROP TABLE IF EXISTS user_notification_settings;
CREATE TABLE user_notification_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    notification_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY (user_id)
);

-- Table: refresh_tokens (No changes)
DROP TABLE IF EXISTS refresh_tokens;
CREATE TABLE refresh_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(255) NOT NULL UNIQUE,
    user_id CHAR(36) NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
