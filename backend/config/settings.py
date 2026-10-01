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
# feature/auth-session-security: dev vs prod vía env. En prod HTTPS:
# SESSION_COOKIE_SECURE=True + CSRF_COOKIE_SECURE=True + SameSite=Lax.
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "86400"))  # 24h
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)  # True en prod HTTPS
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# --- CSRF (feature/auth-session-security): espejo de sesión ---
# csrftoken debe leerlo JS para el header X-CSRFToken -> HttpOnly=False.
# Secure/SameSite iguales que la sesión para no romper React en prod.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_SAMESITE", os.getenv("SESSION_SAMESITE", "Lax"))
CSRF_COOKIE_SECURE = _env_bool(
    "CSRF_COOKIE_SECURE", os.getenv("SESSION_COOKIE_SECURE", "False")
)

# --- CORS/CSRF para React futuro (localhost:5173 Vite / 3000 CRA) ---
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
CSRF_TRUSTED_ORIGINS = _env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

# --- DRF base (permisos concretos en fase de matriz, pendiente) ---
# Throttling: solo el login lo usa (scope 'login'). Primera capa contra
# fuerza bruta; NO la única (falta backoff/captcha/WAF en fases posteriores).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("LOGIN_THROTTLE_RATE", "5/minute"),
        "password_reset": os.getenv("PASSWORD_RESET_THROTTLE_RATE", "5/minute"),
        "registration": os.getenv("REGISTRATION_THROTTLE_RATE", "10/hour"),
        "email_otp": os.getenv("EMAIL_OTP_THROTTLE_RATE", "10/minute"),
    },
}

# --- Negocio configurable, PENDIENTES no inventados ---
# Duración periodo de gracia (decisión 40): sin valor definido → vacío = pendiente.
GRACE_PERIOD_DAYS = os.getenv("GRACE_PERIOD_DAYS", "")
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "14"))

# --- Email + verificación (feature/auth-email-verification, sin JWT) ---
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", False)
# FASE 5 email-real (opción B): SSL implícito para puerto 465.
# Mutuamente excluyente con TLS: usa uno u otro, nunca ambos.
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "AGROTECH <no-reply@agrotech.local>")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
EMAIL_VERIFICATION_SALT = os.getenv("EMAIL_VERIFICATION_SALT", "agrotech-email-verify")
EMAIL_VERIFICATION_TIMEOUT_SECONDS = int(os.getenv("EMAIL_VERIFICATION_TIMEOUT_SECONDS", "86400"))

# --- Password reset (feature/auth-password-reset, tokens nativos Django) ---
# Tokens: PasswordResetTokenGenerator (ligan pk + hash + login + email).
# Expiración nativa vía PASSWORD_RESET_TIMEOUT (segundos).
PASSWORD_RESET_TIMEOUT = int(os.getenv("PASSWORD_RESET_TIMEOUT_SECONDS", "86400"))

# --- OTP login por correo (feature/auth-email-otp) ---
# Verificación en dos pasos pragmática. Desafío por challenge_id, hash
# con make_password, 6 dígitos / 10 min / 5 intentos / 3 reenvíos 15 min.
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_TIMEOUT_SECONDS = int(os.getenv("OTP_TIMEOUT_SECONDS", "600"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_LIMIT = int(os.getenv("OTP_RESEND_LIMIT", "3"))
OTP_RESEND_WINDOW_SECONDS = int(os.getenv("OTP_RESEND_WINDOW_SECONDS", "900"))
OTP_RESEND_MIN_INTERVAL = int(os.getenv("OTP_RESEND_MIN_INTERVAL", "60"))
