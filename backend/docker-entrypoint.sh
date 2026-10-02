#!/bin/sh
# Entrypoint backend: espera MariaDB, aplica migraciones existentes,
# recolecta estáticos y ejecuta el CMD (gunicorn). No genera ni borra nada.
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"

echo "Esperando MariaDB en ${DB_HOST}:${DB_PORT}..."
python - <<'PY'
import os, socket, sys, time
host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "3306"))
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("MariaDB disponible.")
            sys.exit(0)
    except OSError:
        time.sleep(2)
print("MariaDB no disponible tras 120s.", file=sys.stderr)
sys.exit(1)
PY

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Recolectando estaticos..."
python manage.py collectstatic --noinput

echo "Iniciando: $*"
exec "$@"
