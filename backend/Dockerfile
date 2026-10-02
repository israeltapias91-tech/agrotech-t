# AGROTECH backend — Django 5.2 + Python 3.13 + MariaDB (mysqlclient).
# No contiene secretos: toda configuración via variables de entorno.
FROM python:3.13-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# mysqlclient: necesita cliente MariaDB en compilación y en runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    libmariadb3 \
 && rm -rf /var/lib/apt/lists/*

# Dependencias pinneadas del proyecto + servidor WSGI de producción.
COPY requirements.lock.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt \
 && pip install --no-cache-dir "gunicorn==23.0.0"

COPY . .

# Usuario no root para ejecución. Normaliza fin de línea del entrypoint
# (el repo se edita en Windows) y lo hace ejecutable.
RUN useradd -m -u 10001 appuser \
 && mkdir -p /app/staticfiles \
 && sed -i 's/\r$//' /app/docker-entrypoint.sh \
 && chmod +x /app/docker-entrypoint.sh \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
