-- AGROTECH FASE 3 — ejecutar DESPUÉS de instalar MariaDB 11.8 MSI en puerto 3307
-- (3306 ocupado por servicio MySQL80 local existente)
CREATE DATABASE IF NOT EXISTS agrotech_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'agrotech'@'127.0.0.1' IDENTIFIED BY 'agrotech-dev';
GRANT ALL PRIVILEGES ON agrotech_db.* TO 'agrotech'@'127.0.0.1';
FLUSH PRIVILEGES;
