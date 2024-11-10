DROP Database traindb2;
CREATE DATABASE IF NOT EXISTS traindb2;

USE traindb2;

DROP Table IF EXISTS Users;
CREATE TABLE IF NOT EXISTS Users (
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

DROP Table IF EXISTS Stations;

CREATE TABLE IF NOT EXISTS Stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name_en VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    location_lat DECIMAL(9,6),
    location_long DECIMAL(9,6),
    INDEX (name_en),
    INDEX (code)
);


DROP Table IF EXISTS Trains;
CREATE TABLE IF NOT EXISTS Trains (
    train_number BIGINT PRIMARY KEY,
    train_type VARCHAR(50),
    departure_station_id INT NOT NULL,
    arrival_station_id INT NOT NULL,
    scheduled_departure_time TIME NOT NULL,
    scheduled_arrival_time TIME NOT NULL,
    CONSTRAINT fk_departure_station
        FOREIGN KEY (departure_station_id) REFERENCES Stations(id),
    CONSTRAINT fk_arrival_station
        FOREIGN KEY (arrival_station_id) REFERENCES Stations(id),
    INDEX idx_scheduled_departure_time (scheduled_departure_time),
    INDEX idx_scheduled_arrival_time (scheduled_arrival_time)
);

DROP Table IF EXISTS Routes;
CREATE TABLE IF NOT EXISTS Routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number BIGINT NOT NULL,
    station_id INT NOT NULL,
    sequence_number INT NOT NULL,
    scheduled_arrival_time TIME,
    scheduled_departure_time TIME,
    FOREIGN KEY (train_number) REFERENCES Trains(train_number),
    FOREIGN KEY (station_id) REFERENCES Stations(id),
    INDEX (train_number),
    INDEX (station_id),
    INDEX (sequence_number)
);

DROP Table IF EXISTS UserReports;
CREATE TABLE UserReports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_number BIGINT NOT NULL,
    station_id INT NOT NULL,
    report_type ENUM('arrival', 'departure', 'onboard', 'offboard') NOT NULL,
    reported_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (train_number) REFERENCES Trains(train_number),
    FOREIGN KEY (station_id) REFERENCES Stations(id),
    INDEX (train_number),
    INDEX (station_id),
    INDEX (report_type),
    INDEX (reported_time)
);

DROP Table IF EXISTS CalculatedTimes;
CREATE TABLE CalculatedTimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number BIGINT NOT NULL,
    station_id INT NOT NULL,
    calculated_arrival_time DATETIME,
    calculated_departure_time DATETIME,
    number_of_reports INT DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (train_number) REFERENCES Trains(train_number),
    FOREIGN KEY (station_id) REFERENCES Stations(id),
    INDEX (train_number, station_id)
);

DROP Table IF EXISTS Notifications;
CREATE TABLE Notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_number BIGINT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    time DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (train_number) REFERENCES Trains(train_number),
    INDEX (user_id),
    INDEX (train_number)
);

DROP Table IF EXISTS  Rewards ;
CREATE TABLE Rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    points INT NOT NULL,
    date_awarded DATETIME DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    INDEX (user_id),
    INDEX (date_awarded)
);

DROP Table IF EXISTS  UserFavouriteTrains;
CREATE TABLE UserFavouriteTrains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_number BIGINT NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (train_number) REFERENCES Trains(train_number),
    UNIQUE KEY (user_id, train_number),
    INDEX (user_id),
    INDEX (train_number)
);

DROP Table IF EXISTS  UserNotificationSettings ;
CREATE TABLE UserNotificationSettings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    UNIQUE KEY (user_id)
);