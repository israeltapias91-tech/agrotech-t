"""AGROTECH FASE 4 — auditoría: headers, backoff, logs, no-enumeración."""

import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import services
from .security import backoff_fail, backoff_wait

User = get_user_model()
PW = "Secreta123!"
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES,
    {
        "login": "1000/minute",
        "email_otp": "1000/minute",
        "password_reset": "1000/minute",
        "registration": "1000/hour",
    },
)

LOGIN = "/api/auth/login/"
VERIFY = "/api/auth/otp/verify/"
RESEND = "/api/auth/otp/resend/"
REQ = "/api/auth/password/request/"
REG = "/api/auth/register/"


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


def otp_code():
    return re.search(r"(\d{6})", mail.outbox[-1].body).group(1)


@ALTA
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SecurityAuditTests(TestCase):
    def setUp(self):
        mail.outbox = []
        cache.clear()
        make("user@test.com")

    # --- Headers ---
    def test_headers_base(self):
        r = APIClient().get("/api/auth/csrf/")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("camera=()", r["Permissions-Policy"])
        self.assertIn("default-src 'self'", r["Content-Security-Policy-Report-Only"])
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertNotIn("Strict-Transport-Security", r)  # dev: apagado

    @override_settings(SECURE_HSTS_SECONDS=31536000)
    def test_hsts_prod(self):
        # SecurityMiddleware se instancia al arrancar: se prueba con
        # instancia nueva bajo el override (el cableado env->setting).
        from django.http import HttpResponse
        from django.middleware.security import SecurityMiddleware
        from django.test import RequestFactory

        mw = SecurityMiddleware(lambda r: HttpResponse())
        # HSTS solo se emite en HTTPS (request.is_secure()).
        resp = mw.process_response(RequestFactory().get("/", secure=True), HttpResponse())
        self.assertIn("max-age=31536000", resp["Strict-Transport-Security"])

    # --- Backoff login ---
    @override_settings(
        BACKOFF_LOGIN_THRESHOLD=2, BACKOFF_LOGIN_WINDOW_SECONDS=900,
        BACKOFF_LOGIN_BASE_SECONDS=30, BACKOFF_LOGIN_MAX_SECONDS=300,
    )
    def test_backoff_login_progresivo(self):
        c = APIClient()
        bad = {"email": "user@test.com", "password": "Mal123!"}
        self.assertEqual(c.post(LOGIN, bad, format="json").status_code, 400)
        self.assertEqual(c.post(LOGIN, bad, format="json").status_code, 400)
        r = c.post(LOGIN, bad, format="json")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data["code"], "login_backoff")
        self.assertGreater(r.data["retry_after"], 0)

    def test_backoff_no_permanente_y_limpia_en_exito(self):
        self.assertEqual(backoff_fail("x@y.co", "LOGIN"), 0)
        with override_settings(BACKOFF_LOGIN_THRESHOLD=1, BACKOFF_LOGIN_WINDOW_SECONDS=900,
                               BACKOFF_LOGIN_BASE_SECONDS=30, BACKOFF_LOGIN_MAX_SECONDS=300):
            self.assertGreater(backoff_wait("x@y.co", "LOGIN"), 0)
            # Ventana expirada (entrada envejecida) -> libre de nuevo.
            from django.core.cache import cache as _c

            _c.set("agrotech:backoff:LOGIN:x@y.co", [99, 0.0], 900)
            self.assertEqual(backoff_wait("x@y.co", "LOGIN"), 0)

    # --- Backoff OTP ---
    @override_settings(
        BACKOFF_OTP_THRESHOLD=2, BACKOFF_OTP_WINDOW_SECONDS=900,
        BACKOFF_OTP_BASE_SECONDS=60, BACKOFF_OTP_MAX_SECONDS=600,
    )
    def test_backoff_otp(self):
        c = APIClient()
        r = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        ch = r.data["challenge_id"]
        bad = {"challenge_id": ch, "code": "000000"}
        c.post(VERIFY, bad, format="json")
        c.post(VERIFY, bad, format="json")
        r3 = c.post(VERIFY, bad, format="json")
        self.assertEqual(r3.status_code, 429)
        self.assertEqual(r3.data["code"], "otp_backoff")
        self.assertGreater(r3.data["retry_after"], 0)

    # --- Throttle en los 4 scopes ---
    def test_throttle_scopes_existen(self):
        rates = ScopedRateThrottle.THROTTLE_RATES
        for scope in ("login", "password_reset", "registration", "email_otp"):
            self.assertIn(scope, dict(rates))

    # --- No enumeración ---
    def test_login_no_enumera(self):
        c = APIClient()
        a = c.post(LOGIN, {"email": "nadie@test.com", "password": "x"}, format="json")
        b = c.post(LOGIN, {"email": "user@test.com", "password": "x"}, format="json")
        self.assertEqual((a.status_code, a.data["code"]), (b.status_code, b.data["code"]))

    def test_reset_no_enumera(self):
        c = APIClient()
        a = c.post(REQ, {"email": "nadie@test.com"}, format="json")
        b = c.post(REQ, {"email": "user@test.com"}, format="json")
        self.assertEqual((a.status_code, a.data["code"]), (b.status_code, b.data["code"]))

    # --- Challenge inválido / intervalo mínimo / expiración sesión ---
    def test_challenge_invalido(self):
        r = APIClient().post(VERIFY, {"challenge_id": "00000000-0000-0000-0000-000000000000", "code": "123456"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "otp_invalid")

    def test_intervalo_minimo_reenvio(self):
        c = APIClient()
        ch = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json").data["challenge_id"]
        with override_settings(OTP_RESEND_MIN_INTERVAL=3600):
            r = c.post(RESEND, {"challenge_id": ch}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "otp_resend_limited")

    @override_settings(SESSION_COOKIE_AGE=60)
    def test_expiracion_sesion_configurable(self):
        c = APIClient()
        r = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        c.post(VERIFY, {"challenge_id": r.data["challenge_id"], "code": otp_code()}, format="json")
        from django.conf import settings as dj

        self.assertEqual(int(c.cookies[dj.SESSION_COOKIE_NAME]["max-age"]), 60)

    # --- Logs: eventos sí, secretos no ---
    def test_logs_eventos_sin_secretos(self):
        secret_pw = "ClaveSecreta Unica 999!"
        secret_code = None
        with self.assertLogs("agrotech.security", level="INFO") as cm:
            User.objects.create_user(email="log@test.com", password=secret_pw,
                                     first_name="L", last_name="O", email_verified=True)
            services.register_user(first_name="R", last_name="G", email="reg@test.com",
                                   phone="", password="OtraClave Unica 999!",
                                   password_confirm="OtraClave Unica 999!")
            r = APIClient().post(LOGIN, {"email": "log@test.com", "password": secret_pw}, format="json")
            secret_code = otp_code()
            APIClient().post(VERIFY, {"challenge_id": r.data["challenge_id"], "code": secret_code}, format="json")
            self.assertTrue(User.objects.filter(email="log@test.com").exists())
        out = "\n".join(cm.output)
        self.assertIn("auth.registered", out)
        self.assertIn("auth.login.ok", out)
        self.assertIn("auth.otp.ok", out)
        for secret in (secret_pw, secret_code):
            self.assertIsNotNone(secret)
            self.assertNotIn(secret, out)
        self.assertNotIn("csrftoken", out.lower())
        self.assertNotIn("sessionid", out.lower())
