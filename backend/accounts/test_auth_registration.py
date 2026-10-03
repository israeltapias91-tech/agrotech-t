"""AGROTECH — registro: crear + verificar + habilitar login (sin finca)."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import services

User = get_user_model()
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES,
    {"login": "1000/minute", "password_reset": "1000/minute", "registration": "1000/hour"},
)

REG = "/api/auth/register/"
LOGIN = "/api/auth/login/"
VERIFY = "/api/auth/email/verify/"
RESEND = "/api/auth/email/resend/"
PW = "Segura123!Fuerte"


def base(**kw):
    d = {
        "first_name": "Juan",
        "last_name": "Pérez",
        "email": "juan@test.com",
        "phone": "+57 300 123 4567",
        "password": PW,
        "password_confirm": PW,
    }
    d.update(kw)
    return d


@ALTA
class RegistrationTests(TestCase):
    def test_01_ok_201(self):
        r = APIClient().post(REG, base(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["code"], "registered")
        self.assertEqual(r.data["email"], "juan@test.com")

    def test_02_duplicado(self):
        c = APIClient()
        c.post(REG, base(), format="json")
        r = c.post(REG, base(), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "email_taken")

    def test_03_email_invalido(self):
        r = APIClient().post(REG, base(email="no-es-email"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "email_invalid")

    def test_04_faltan_campos(self):
        r = APIClient().post(REG, base(first_name="", password_confirm=""), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "fields_required")
        self.assertIn("first_name", r.data["messages"])

    def test_05_telefono_invalido(self):
        r = APIClient().post(REG, base(phone="abc"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "phone_invalid")

    def test_06_password_debil(self):
        r = APIClient().post(REG, base(password="123", password_confirm="123"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "password_too_weak")
        self.assertTrue(r.data.get("messages"))

    def test_07_confirm_no_coincide(self):
        r = APIClient().post(REG, base(password_confirm="Otra999!"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "password_mismatch")

    def test_08_creada_sin_verificar_y_hash(self):
        APIClient().post(REG, base(), format="json")
        u = User.objects.get(email="juan@test.com")
        self.assertFalse(u.email_verified)
        self.assertNotEqual(u.password, PW)
        self.assertTrue(u.check_password(PW))

    def test_09_envia_correo_verificacion(self):
        mail.outbox = []
        APIClient().post(REG, base(), format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("juan@test.com", mail.outbox[0].to)
        self.assertIn("token=", mail.outbox[0].body)

    def test_10_login_bloqueado_hasta_verificar(self):
        c = APIClient()
        c.post(REG, base(), format="json")
        r = c.post(LOGIN, {"email": "juan@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["code"], "email_not_verified")

    def test_11_reenvio_tras_registro(self):
        c = APIClient()
        c.post(REG, base(), format="json")
        mail.outbox = []
        r = c.post(RESEND, {"email": "juan@test.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_12_respuesta_sin_password(self):
        r = APIClient().post(REG, base(), format="json")
        self.assertNotIn("password", r.data)

    def test_13_cadena_registro_verifica_login(self):
        import re

        from django.core import mail as _mail

        c = APIClient()
        c.post(REG, base(), format="json")
        token, _ = services.request_verification(User.objects.get(email="juan@test.com"))
        rv = c.post(VERIFY, {"token": token}, format="json")
        self.assertEqual(rv.status_code, 200)
        rl = c.post(LOGIN, {"email": "juan@test.com", "password": PW}, format="json")
        self.assertEqual(rl.status_code, 200)
        self.assertEqual(rl.data["code"], "otp_required")  # fase 1: sin sesión aún
        code = re.search(r"(\d{6})", _mail.outbox[-1].body).group(1)
        ro = c.post("/api/auth/otp/verify/", {"challenge_id": rl.data["challenge_id"], "code": code}, format="json")
        self.assertEqual(ro.status_code, 200)
        self.assertEqual(ro.data["code"], "authenticated")

    def test_14_ok_informa_email_sent(self):
        r = APIClient().post(REG, base(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data["email_sent"])

    def test_15_smtp_falla_no_500_usuario_creado(self):
        import smtplib

        with mock.patch("accounts.services.send_mail", side_effect=smtplib.SMTPException("relay off")):
            r = APIClient().post(REG, base(), format="json")
        self.assertEqual(r.status_code, 201)  # nunca 500 por SMTP
        self.assertEqual(r.data["code"], "registered")
        self.assertFalse(r.data["email_sent"])
        u = User.objects.get(email="juan@test.com")  # creado y pendiente
        self.assertFalse(u.email_verified)
        self.assertTrue(u.check_password(PW))

    def test_16_smtp_timeout_no_bloquea(self):
        import socket

        with mock.patch("accounts.services.send_mail", side_effect=socket.timeout("colgado")):
            r = APIClient().post(REG, base(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data["email_sent"])
        self.assertFalse(User.objects.get(email="juan@test.com").email_verified)
