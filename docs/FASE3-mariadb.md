# FASE 3 — MariaDB 11.8 en Windows (MSI oficial)

## Conflicto detectado
Servicio `MySQL80` corriendo en puerto `3306`. No tocarlo.

## Instalación MariaDB
1. Descargar MSI MariaDB 11.8 64-bit.
2. Puerto: **3307** (no 3306).
3. Charset: `utf8mb4`, collation `utf8mb4_unicode_ci`.
4. Incluir HeidiSQL + C Connector (lo usa `mysqlclient`).
5. Verificar servicio `MariaDB` en `services.msc` corriendo.

## Crear DB
Ejecutar `docs/agrotech_db-init.sql` en HeidiSQL contra `127.0.0.1:3307` como root,
o ajustar `DB_PASSWORD` en `backend/.env` si cambias la clave.

## Verificar desde Django (solo cuando MariaDB esté arriba)
```powershell
backend\.venv\Scripts\Activate.ps1
python backend\manage.py dbshell -- -e "SELECT VERSION();"
```
En FASE 3 basta `manage.py check` (no requiere DB viva). `migrate` PROHIBIDO hasta FASE 4.
