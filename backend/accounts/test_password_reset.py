"""AGROTECH — ciclo completo de recuperación de contraseña (decisión A)."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import services

User = get_user_model()
PW = "Secreta123!"
NEW = "Nueva456!Segura"
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES,
    {"login": "1000/minute", "password_reset": "1000/minute"},
)

REQ = "/api/auth/password/request/"
CONF = "/api/auth/password/confirm/"
LOGIN = "/api/auth/login/"
SESSION = "/api/auth/session/"


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


def payload(uid, token, new=NEW, confirm=NEW):
    return {
        "uid": uid,
        "token": token,
        "new_password": new,
        "new_password_confirm": confirm,
    }


@ALTA
class PasswordResetTests(TestCase):
    def setUp(self):
        make("user@test.com")

    def _request(self, email="user@test.com"):
        return services.request_password_reset(email)

    def test_1_request_existente_envia(self):
        mail.outbox = []
        c = APIClient()
        r = c.post(REQ, {"email": "user@test.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "reset_sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("uid=", mail.outbox[0].body)
        self.assertIn("token=", mail.outbox[0].body)

    def test_2_request_inexistente_neutro_sin_correo(self):
        mail.outbox = []
        c = APIClient()
        r = c.post(REQ, {"email": "nadie@test.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "reset_sent")
        self.assertEqual(len(mail.outbox), 0)

    def test_3_confirm_valido(self):
        _, uid, token, _ = self._request()
        r = APIClient().post(CONF, payload(uid, token), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "password_changed")

    def test_4_confirm_expirado(self):
        _, uid, token, _ = self._request()
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            r = APIClient().post(CONF, payload(uid, token), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "token_expired")

    def test_5_confirm_manipulado(self):
        _, uid, token, _ = self._request()
        r = APIClient().post(CONF, payload(uid, token + "x"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "token_invalid")

    def test_6_confirm_reutilizado(self):
        _, uid, token, _ = self._request()
        c = APIClient()
        self.assertEqual(c.post(CONF, payload(uid, token), format="json").status_code, 200)
        r2 = c.post(CONF, payload(uid, token), format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.data["code"], "token_invalid")

    def test_7_password_debil(self):
        _, uid, token, _ = self._request()
        r = APIClient().post(CONF, payload(uid, token, new="123", confirm="123"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "password_too_weak")
        self.assertTrue(r.data.get("messages"))

    def test_8_confirm_no_coincide(self):
        _, uid, token, _ = self._request()
        r = APIClient().post(CONF, payload(uid, token, confirm="Otra789!"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "password_mismatch")

    def test_9_cambio_exitoso_nueva_entra_vieja_no(self):
        _, uid, token, _ = self._request()
        APIClient().post(CONF, payload(uid, token), format="json")
        c = APIClient()
        self.assertEqual(
            c.post(LOGIN, {"email": "user@test.com", "password": NEW}, format="json").status_code, 200
        )
        c2 = APIClient()
        self.assertEqual(
            c2.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json").status_code, 400
        )

    def test_10_caso2_anonimo_revoca_todas(self):
        a, b = APIClient(), APIClient()
        a.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        b.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        _, uid, token, _ = self._request()
        r = APIClient().post(CONF, payload(uid, token), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(a.get(SESSION).status_code, 403)
        self.assertEqual(b.get(SESSION).status_code, 403)

    def test_11_caso1_autenticado_conserva_actual(self):
        a, b = APIClient(), APIClient()
        a.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        b.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        _, uid, token, _ = self._request()
        r = a.post(CONF, payload(uid, token), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(a.get(SESSION).status_code, 200)
        self.assertEqual(b.get(SESSION).status_code, 403)

    def test_12_sin_auto_login(self):
        _, uid, token, _ = self._request()
        c = APIClient()
        c.post(CONF, payload(uid, token), format="json")
        self.assertEqual(c.get(SESSION).status_code, 403)
