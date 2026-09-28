"""AGROTECH — pruebas de login/logout/sesión.

Puertas: existe -> hash -> activa -> verificada -> sesión.
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from unittest import mock

User = get_user_model()
PW = "Secreta123!"
# DRF fija THROTTLE_RATES al importar: override_settings no lo mueve.
ALTA = mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "1000/minute"})
BAJA = mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "3/minute"})


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


@ALTA
class AuthLoginTests(TestCase):

    def setUp(self):
        self.ok = make("ok@test.com")
        self.unverified = make("nuevo@test.com", email_verified=False)
        self.suspended = make("susp@test.com", account_status="SUSPENDED")
        self.deactivated = make("deac@test.com", account_status="DEACTIVATED")

    def test_login_ok_crea_sesion(self):
        c = APIClient()
        r = c.post("/api/auth/login/", {"email": "ok@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "authenticated")
        self.assertIn("_auth_user_id", c.session)
        r2 = c.get("/api/auth/session/")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["email"], "ok@test.com")

    def test_password_mal_e_inexistente_mismo_codigo(self):
        c = APIClient()
        r1 = c.post("/api/auth/login/", {"email": "ok@test.com", "password": "Mal123!"}, format="json")
        r2 = c.post("/api/auth/login/", {"email": "nadie@test.com", "password": "Mal123!"}, format="json")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r1.data["code"], "invalid_credentials")
        self.assertEqual(r2.data["code"], "invalid_credentials")

    def test_sin_verificar_bloqueado(self):
        c = APIClient()
        r = c.post("/api/auth/login/", {"email": "nuevo@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["code"], "email_not_verified")

    def test_suspendida_y_desactivada_bloqueadas(self):
        c = APIClient()
        r1 = c.post("/api/auth/login/", {"email": "susp@test.com", "password": PW}, format="json")
        r2 = c.post("/api/auth/login/", {"email": "deac@test.com", "password": PW}, format="json")
        self.assertEqual(r1.status_code, 403)
        self.assertEqual(r1.data["code"], "account_suspended")
        self.assertEqual(r2.status_code, 403)
        self.assertEqual(r2.data["code"], "account_deactivated")

    def test_sesiones_multiples_y_logout_parcial(self):
        c1, c2 = APIClient(), APIClient()
        c1.post("/api/auth/login/", {"email": "ok@test.com", "password": PW}, format="json")
        c2.post("/api/auth/login/", {"email": "ok@test.com", "password": PW}, format="json")
        self.assertNotEqual(c1.session.session_key, c2.session.session_key)
        c1.post("/api/auth/logout/")
        self.assertEqual(c1.get("/api/auth/session/").status_code, 403)
        self.assertEqual(c2.get("/api/auth/session/").status_code, 200)

    def test_logout_sin_sesion_rechazado(self):
        c = APIClient()
        self.assertEqual(c.post("/api/auth/logout/").status_code, 403)

    @BAJA
    def test_throttle_login(self):
        cache.clear()
        c = APIClient()
        codes = [
            c.post("/api/auth/login/", {"email": "ok@test.com", "password": "Mal!",}, format="json").status_code
            for _ in range(4)
        ]
        self.assertEqual(codes, [400, 400, 400, 429])
