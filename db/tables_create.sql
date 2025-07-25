DROP Database traindb2;
CREATE DATABASE IF NOT EXISTS traindb2;

USE traindb2;

DROP Table IF EXISTS users;
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    INDEX (username),
    INDEX (email)
);

DROP Table IF EXISTS stations;

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


DROP Table IF EXISTS trains;
CREATE TABLE IF NOT EXISTS trains (
    train_number BIGINT PRIMARY KEY,
    train_type VARCHAR(50),
    departure_station_id INT NOT NULL,
    arrival_station_id INT NOT NULL,
    scheduled_departure_time TIME NOT NULL,
    scheduled_arrival_time TIME NOT NULL,
    CONSTRAINT fk_departure_station
        FOREIGN KEY (departure_station_id) REFERENCES stations(id),
    CONSTRAINT fk_arrival_station
        FOREIGN KEY (arrival_station_id) REFERENCES stations(id),
    INDEX idx_scheduled_departure_time (scheduled_departure_time),
    INDEX idx_scheduled_arrival_time (scheduled_arrival_time)
);

DROP Table IF EXISTS routes;
CREATE TABLE IF NOT EXISTS routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number BIGINT NOT NULL,
    station_id INT NOT NULL,
    sequence_number INT NOT NULL,
    scheduled_arrival_time TIME,
    scheduled_departure_time TIME,
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (station_id) REFERENCES stations(id),
    INDEX (train_number),
    INDEX (station_id),
    INDEX (sequence_number)
);

DROP Table IF EXISTS userreports;
CREATE TABLE user_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_number BIGINT NOT NULL,
    operation_id INT NOT NULL,
    station_id INT NOT NULL,
    report_type ENUM('arrival', 'departure', 'onboard', 'offboard') NOT NULL,
    reported_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (operation_id) REFERENCES operations(id),
    FOREIGN KEY (station_id) REFERENCES stations(id),
    INDEX (train_number),
    INDEX (station_id),
    INDEX (report_type),
    INDEX (reported_time)
);

DROP Table IF EXISTS calculatedtimes;
CREATE TABLE calculatedtimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number BIGINT NOT NULL,
    station_id INT NOT NULL,
    calculated_arrival_time DATETIME,
    calculated_departure_time DATETIME,
    number_of_reports INT DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (station_id) REFERENCES stations(id),
    INDEX (train_number, station_id)
);

DROP Table IF EXISTS notifications;
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_number BIGINT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    time DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    INDEX (user_id),
    INDEX (train_number)
);

DROP Table IF EXISTS  rewards ;
CREATE TABLE rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    points INT NOT NULL,
    date_awarded DATETIME DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX (user_id),
    INDEX (date_awarded)
);

DROP Table IF EXISTS  userfavouritetrains;
CREATE TABLE userfavouritetrains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_number BIGINT NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    UNIQUE KEY (user_id, train_number),
    INDEX (user_id),
    INDEX (train_number)
);

DROP Table IF EXISTS  usernotificationsettings ;
CREATE TABLE usernotificationsettings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY (user_id)
);

DROP TABLE IF EXISTS operations;
CREATE TABLE operations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    train_number BIGINT NOT NULL,
    operational_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'on time',
    total_delay INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (train_number) REFERENCES trains(train_number)
);