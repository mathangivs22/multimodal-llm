-- Run once as the MySQL root user, e.g.:
--   mysql -u root -p < setup_mysql.sql
-- Change the password here and in your .env file.
CREATE DATABASE IF NOT EXISTS meetingiq
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'meetingiq'@'localhost' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON meetingiq.* TO 'meetingiq'@'localhost';
FLUSH PRIVILEGES;
