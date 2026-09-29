"""AGROTECH — login en 2 fases + logout/sesión.

Fase 1: puertas (existe -> hash -> activa -> verificada) -> otp_required.
Fase 2: OTP -> sesión. Sin OTP no hay sesión.
"""

import re

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from unittest import mock

User = get_user_model()
PW = "Secreta123!"
# DRF fija THROTTLE_RATES al importar: override_settings no lo mueve.
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES,
    {"login": "1000/minute", "email_otp": "1000/minute"},
)
BAJA = mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "3/minute"})

LOGIN = "/api/auth/login/"
VERIFY = "/api/auth/otp/verify/"
SESSION = "/api/auth/session/"
LOGOUT = "/api/auth/logout/"


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


def phase1(c, email, password):
    """Fase 1 + extrae el código del buzón (canal real)."""
    from django.core import mail

    r = c.post(LOGIN, {"email": email, "password": password}, format="json")
    code = None
    if r.status_code == 200 and r.data.get("code") == "otp_required":
        m = re.search(r"(\d{6})", mail.outbox[-1].body)
        code = m.group(1) if m else None
    return r, r.data.get("challenge_id"), code


def full_login(c, email, password):
    r, challenge, code = phase1(c, email, password)
    assert r.status_code == 200, r.data
    r2 = c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json")
    assert r2.status_code == 200, r2.data
    return r2


@ALTA
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthLoginTests(TestCase):

    def setUp(self):
        from django.core import mail

        mail.outbox = []
        self.ok = make("ok@test.com")
        self.unverified = make("nuevo@test.com", email_verified=False)
        self.suspended = make("susp@test.com", account_status="SUSPENDED")
        self.deactivated = make("deac@test.com", account_status="DEACTIVATED")

    def test_fase1_ok_devuelve_challenge_sin_sesion(self):
        c = APIClient()
        r, challenge, code = phase1(c, "ok@test.com", PW)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "otp_required")
        self.assertTrue(challenge)
        self.assertTrue(code)
        self.assertNotIn("_auth_user_id", c.session)  # SIN sesión aún
        self.assertEqual(c.get(SESSION).status_code, 403)

    def test_fase2_ok_crea_sesion(self):
        c = APIClient()
        full_login(c, "ok@test.com", PW)
        self.assertIn("_auth_user_id", c.session)
        r2 = c.get(SESSION)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["email"], "ok@test.com")

    def test_password_mal_e_inexistente_mismo_codigo(self):
        c = APIClient()
        r1 = c.post(LOGIN, {"email": "ok@test.com", "password": "Mal123!"}, format="json")
        r2 = c.post(LOGIN, {"email": "nadie@test.com", "password": "Mal123!"}, format="json")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r1.data["code"], "invalid_credentials")
        self.assertEqual(r2.data["code"], "invalid_credentials")

    def test_sin_verificar_bloqueado(self):
        c = APIClient()
        r = c.post(LOGIN, {"email": "nuevo@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["code"], "email_not_verified")

    def test_suspendida_y_desactivada_bloqueadas(self):
        c = APIClient()
        r1 = c.post(LOGIN, {"email": "susp@test.com", "password": PW}, format="json")
        r2 = c.post(LOGIN, {"email": "deac@test.com", "password": PW}, format="json")
        self.assertEqual(r1.status_code, 403)
        self.assertEqual(r1.data["code"], "account_suspended")
        self.assertEqual(r2.status_code, 403)
        self.assertEqual(r2.data["code"], "account_deactivated")

    def test_sesiones_multiples_y_logout_parcial(self):
        c1, c2 = APIClient(), APIClient()
        full_login(c1, "ok@test.com", PW)
        full_login(c2, "ok@test.com", PW)
        self.assertNotEqual(c1.session.session_key, c2.session.session_key)
        c1.post(LOGOUT)
        self.assertEqual(c1.get(SESSION).status_code, 403)
        self.assertEqual(c2.get(SESSION).status_code, 200)

    def test_logout_sin_sesion_rechazado(self):
        c = APIClient()
        self.assertEqual(c.post(LOGOUT).status_code, 403)

    @BAJA
    def test_throttle_login(self):
        cache.clear()
        c = APIClient()
        codes = [
            c.post(LOGIN, {"email": "ok@test.com", "password": "Mal!",}, format="json").status_code
            for _ in range(4)
        ]
        self.assertEqual(codes, [400, 400, 400, 429])
