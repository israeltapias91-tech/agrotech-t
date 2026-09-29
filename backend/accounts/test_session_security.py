"""AGROTECH — seguridad de sesiones (decisión 21 + feature/auth-session-security).

Matriz: PC + celular + tablet. Logout-1 mata 1. Logout-all mata las
demás y deja la invocante. Cambio de clave: actual viva, demás muertas.
"""

from unittest import mock

import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import services

User = get_user_model()
PW = "Secreta123!"
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES, {"login": "1000/minute", "email_otp": "1000/minute"}
)

LOGIN = "/api/auth/login/"
VERIFY = "/api/auth/otp/verify/"
SESSION = "/api/auth/session/"
LOGOUT = "/api/auth/logout/"
LOGOUT_ALL = "/api/auth/logout-all/"
CSRF = "/api/auth/csrf/"


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


def full_login(c, email="user@test.com", password=PW):
    """Login completo en 2 fases (código leído del buzón)."""
    r = c.post(LOGIN, {"email": email, "password": password}, format="json")
    assert r.status_code == 200, r.data
    code = re.search(r"(\d{6})", mail.outbox[-1].body).group(1)
    r2 = c.post(VERIFY, {"challenge_id": r.data["challenge_id"], "code": code}, format="json")
    assert r2.status_code == 200, r2.data
    return c, r2


@ALTA
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SessionSecurityTests(TestCase):
    def setUp(self):
        mail.outbox = []
        make("user@test.com")

    def _login(self):
        c = APIClient()
        return full_login(c)

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
        r = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        self.assertEqual(r.data["code"], "otp_required")
        # Fase 1: el servidor NO fija cookie de sesión (leer c.session la
        # crearía en el cliente de pruebas: Client.session guarda sola).
        self.assertNotIn(settings.SESSION_COOKIE_NAME, r.cookies)
        self.assertEqual(c.get(SESSION).status_code, 403)
        code = re.search(r"(\d{6})", mail.outbox[-1].body).group(1)
        c.post(VERIFY, {"challenge_id": r.data["challenge_id"], "code": code}, format="json")
        first = c.session.session_key
        self.assertIsNotNone(first)
        # Segundo login completo -> key distinta (rotación anti-fixation).
        c.post(LOGOUT)
        r2 = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        code2 = re.search(r"(\d{6})", mail.outbox[-1].body).group(1)
        c.post(VERIFY, {"challenge_id": r2.data["challenge_id"], "code": code2}, format="json")
        self.assertNotEqual(first, c.session.session_key)

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
        # Fase 1 pre-auth no exige CSRF (sin sesión aún).
        r1 = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        self.assertEqual(r1.status_code, 200)
        # Fase 2 tampoco (sigue sin sesión); django_login rota el CSRF.
        code = re.search(r"(\d{6})", mail.outbox[-1].body).group(1)
        self.assertEqual(
            c.post(VERIFY, {"challenge_id": r1.data["challenge_id"], "code": code}, format="json").status_code,
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
