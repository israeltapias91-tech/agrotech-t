"""AGROTECH config — FASE 3 (Windows dev).

Stack: Python 3.13 + Django 5.2 + DRF + MariaDB 11.8 (mysqlclient).
Regla crítica: AUTH_USER_MODEL personalizado se define en FASE 4
ANTES de la primera migración. Por eso en FASE 3 NO se corre `migrate`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-fase3-cambiar-antes-de-usar")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros FASE 3
    "rest_framework",
    "corsheaders",
    # Apps AGROTECH FASE 4
    "accounts",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # debe ir arriba
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos: MariaDB 11.8 vía mysqlclient ---
# NOTA Windows: el puerto 3306 está ocupado por MySQL80 local.
# MariaDB 11.8 MSI debe instalarse en 3307 (ver docs/FASE3-mariadb.md).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "agrotech_db"),
        "USER": os.getenv("DB_USER", "agrotech"),
        "PASSWORD": os.getenv("DB_PASSWORD", "agrotech-dev"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3307"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# FASE 4: modelo de identidad oficial (UUID + email login).
AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sesiones: decisión 21 (varias sesiones + 24h, cookie Django) ---
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "86400"))  # 24h
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)  # True en prod HTTPS
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# --- CORS/CSRF para React futuro (localhost:5173 Vite / 3000 CRA) ---
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
CSRF_TRUSTED_ORIGINS = _env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

# --- DRF base (permisos concretos en fase de matriz, pendiente) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# --- Negocio configurable, PENDIENTES no inventados ---
# Duración periodo de gracia (decisión 40): sin valor definido → vacío = pendiente.
GRACE_PERIOD_DAYS = os.getenv("GRACE_PERIOD_DAYS", "")
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "14"))
