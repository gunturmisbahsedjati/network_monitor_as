CREATE DATABASE IF NOT EXISTS network_monitor;
USE network_monitor;

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(50) NOT NULL,
    last_status VARCHAR(10) DEFAULT 'UNKNOWN',
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Data Awal
INSERT INTO devices (name, ip_address) VALUES 
('Google DNS', '8.8.8.8'),
('Router Gateway', '192.168.1.1'),
('Local DB Container', 'db'); -- Kita bisa ping container database


CREATE TABLE IF NOT EXISTS device_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id INT,
                status VARCHAR(10),
                event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);