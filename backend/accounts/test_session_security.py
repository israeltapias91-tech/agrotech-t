"""AGROTECH — seguridad de sesiones (decisión 21 + feature/auth-session-security).

Matriz: PC + celular + tablet. Logout-1 mata 1. Logout-all mata las
demás y deja la invocante. Cambio de clave: actual viva, demás muertas.
"""

from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import services

User = get_user_model()
PW = "Secreta123!"
ALTA = mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "1000/minute"})

LOGIN = "/api/auth/login/"
SESSION = "/api/auth/session/"
LOGOUT = "/api/auth/logout/"
LOGOUT_ALL = "/api/auth/logout-all/"
CSRF = "/api/auth/csrf/"


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


@ALTA
class SessionSecurityTests(TestCase):
    def setUp(self):
        make("user@test.com")

    def _login(self):
        c = APIClient()
        r = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 200)
        return c, r

    def test_matriz_tres_sesiones(self):
        pc, _ = self._login()
        cel, _ = self._login()
        tab, _ = self._login()
        keys = {pc.session.session_key, cel.session.session_key, tab.session.session_key}
        self.assertEqual(len(keys), 3)
        for c in (pc, cel, tab):
            self.assertEqual(c.get(SESSION).status_code, 200)

    def test_logout_uno_deja_dos(self):
        pc, _ = self._login()
        cel, _ = self._login()
        tab, _ = self._login()
        self.assertEqual(pc.post(LOGOUT).status_code, 200)
        self.assertEqual(pc.get(SESSION).status_code, 403)
        self.assertEqual(cel.get(SESSION).status_code, 200)
        self.assertEqual(tab.get(SESSION).status_code, 200)

    def test_logout_all_deja_invocante(self):
        pc, _ = self._login()
        cel, _ = self._login()
        tab, _ = self._login()
        r = tab.post(LOGOUT_ALL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "all_closed")
        self.assertEqual(pc.get(SESSION).status_code, 403)
        self.assertEqual(cel.get(SESSION).status_code, 403)
        self.assertEqual(tab.get(SESSION).status_code, 200)

    def test_fixation_key_rota_en_login(self):
        c = APIClient()
        antes = c.session.session_key
        c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        despues = c.session.session_key
        self.assertIsNotNone(despues)
        self.assertNotEqual(antes, despues)

    def test_cookie_flags_y_edad(self):
        _, r = self._login()
        jar = r.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(jar)
        self.assertTrue(jar["httponly"])
        self.assertEqual(jar["samesite"].lower(), "lax")
        self.assertEqual(int(jar["max-age"]), 86400)
        # DEV HTTP: sin Secure. En prod debe ir True (ver .env.example).
        self.assertFalse(jar["secure"])

    def test_csrf_flujo_react(self):
        c = APIClient(enforce_csrf_checks=True)
        r = c.get(CSRF)
        self.assertEqual(r.status_code, 200)
        self.assertIn("csrftoken", r.cookies)
        # Login pre-auth no exige CSRF (sin sesión aún), pero rota el token.
        self.assertEqual(
            c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json").status_code,
            200,
        )
        token = c.cookies["csrftoken"].value
        # Logout SIN token -> 403.
        self.assertEqual(c.post(LOGOUT).status_code, 403)
        # Logout CON token vigente -> 200.
        self.assertEqual(c.post(LOGOUT, HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_cambio_clave_actual_viva_demas_muertas(self):
        pc, _ = self._login()
        cel, _ = self._login()
        user = User.objects.get(email="user@test.com")
        user.set_password("Nueva123!")
        user.save()
        req = RequestFactory().post("/x/")
        req.session = pc.session
        req.user = user
        services.rotate_on_password_change(req, user)
        pc.cookies[settings.SESSION_COOKIE_NAME] = req.session.session_key
        self.assertEqual(pc.get(SESSION).status_code, 200)
        self.assertEqual(cel.get(SESSION).status_code, 403)
        # Nueva clave entra; vieja ya no.
        c = APIClient()
        self.assertEqual(
            c.post(LOGIN, {"email": "user@test.com", "password": "Nueva123!"}, format="json").status_code,
            200,
        )
        c2 = APIClient()
        self.assertEqual(
            c2.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json").status_code,
            400,
        )
