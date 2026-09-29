"""AGROTECH — OTP de login por correo ligado a challenge_id."""

import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from .models import EmailOTP

User = get_user_model()
PW = "Secreta123!"
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES,
    {"login": "1000/minute", "email_otp": "1000/minute", "registration": "1000/hour"},
)

LOGIN = "/api/auth/login/"
VERIFY = "/api/auth/otp/verify/"
RESEND = "/api/auth/otp/resend/"
SESSION = "/api/auth/session/"


def make(email, **kw):
    kw.setdefault("password", PW)
    kw.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **kw)


def otp_from_mail():
    m = re.search(r"(\d{6})", mail.outbox[-1].body)
    return m.group(1)


@ALTA
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailOTPTests(TestCase):
    def setUp(self):
        mail.outbox = []
        make("user@test.com")

    def _challenge(self, email="user@test.com", password=PW):
        c = APIClient()
        r = c.post(LOGIN, {"email": email, "password": password}, format="json")
        self.assertEqual(r.status_code, 200)
        return c, r.data["challenge_id"], otp_from_mail()

    def test_01_password_ok_genera_otp(self):
        c, challenge, code = self._challenge()
        self.assertTrue(challenge)
        self.assertRegex(code, r"^\d{6}$")
        self.assertTrue(EmailOTP.objects.filter(challenge_id=challenge).exists())

    def test_02_otp_enviado_por_correo(self):
        self._challenge()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("user@test.com", mail.outbox[0].to)
        self.assertIn("vence", mail.outbox[0].body.lower())

    def test_03_correcto_crea_sesion(self):
        c, challenge, code = self._challenge()
        r = c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "authenticated")
        self.assertIn("_auth_user_id", c.session)

    def test_04_incorrecto_resta_intentos(self):
        c, challenge, _ = self._challenge()
        r = c.post(VERIFY, {"challenge_id": challenge, "code": "000000"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "otp_invalid")
        otp = EmailOTP.objects.get(challenge_id=challenge)
        self.assertEqual(otp.attempts, 1)

    def test_05_expirado(self):
        with override_settings(OTP_TIMEOUT_SECONDS=-1):
            c, challenge, code = self._challenge()
        r = c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "otp_expired")

    def test_06_reutilizado(self):
        c, challenge, code = self._challenge()
        self.assertEqual(c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json").status_code, 200)
        r2 = c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.data["code"], "otp_invalid")

    def test_07_anterior_invalidado_por_nuevo(self):
        c1, ch1, _ = self._challenge()
        c2, ch2, code2 = self._challenge()
        self.assertNotEqual(ch1, ch2)
        r = c1.post(VERIFY, {"challenge_id": ch1, "code": "000000"}, format="json")
        self.assertEqual(r.data["code"], "otp_invalid")  # superseded
        r2 = c2.post(VERIFY, {"challenge_id": ch2, "code": code2}, format="json")
        self.assertEqual(r2.status_code, 200)

    def test_08_maximo_intentos(self):
        c, challenge, code = self._challenge()
        last = None
        for _ in range(5):
            last = c.post(VERIFY, {"challenge_id": challenge, "code": "000000"}, format="json")
        self.assertEqual(last.status_code, 429)
        self.assertEqual(last.data["code"], "otp_attempts_exceeded")
        r = c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json")
        self.assertEqual(r.status_code, 429)  # ni el correcto entra ya

    def test_09_exceso_reenvios(self):
        with override_settings(OTP_RESEND_MIN_INTERVAL=0):
            _, ch, _ = self._challenge()
            c = APIClient()
            codes = [c.post(RESEND, {"challenge_id": ch}, format="json").status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 400])
        self.assertEqual(c.post(RESEND, {"challenge_id": ch}, format="json").data["code"], "otp_resend_limited")

    def test_10_sin_sesion_antes_del_otp(self):
        from django.conf import settings as dj_settings

        c = APIClient()
        r = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        self.assertEqual(r.data["code"], "otp_required")
        self.assertNotIn(dj_settings.SESSION_COOKIE_NAME, r.cookies)
        self.assertEqual(c.get(SESSION).status_code, 403)

    def test_11_sesion_despues_del_otp(self):
        c, challenge, code = self._challenge()
        c.post(VERIFY, {"challenge_id": challenge, "code": code}, format="json")
        self.assertEqual(c.get(SESSION).status_code, 200)

    def test_12_otp_nunca_en_json(self):
        c = APIClient()
        r = c.post(LOGIN, {"email": "user@test.com", "password": PW}, format="json")
        secret = otp_from_mail()
        self.assertNotIn(secret, r.content.decode())
        r2 = c.post(RESEND, {"challenge_id": r.data["challenge_id"]}, format="json")
        if r2.status_code == 200:
            self.assertNotIn(secret, r2.content.decode())

    def test_13_hash_no_plano_en_db(self):
        _, challenge, code = self._challenge()
        otp = EmailOTP.objects.get(challenge_id=challenge)
        self.assertNotEqual(otp.code_hash, code)
        self.assertTrue(otp.code_hash.startswith("pbkdf2_"))

    def test_14_suspendido_no_llega_al_otp(self):
        make("susp@test.com", account_status="SUSPENDED")
        mail.outbox = []
        c = APIClient()
        r = c.post(LOGIN, {"email": "susp@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertNotIn("challenge_id", r.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_15_sin_verificar_no_llega_al_otp(self):
        make("nuevo@test.com", email_verified=False)
        mail.outbox = []
        c = APIClient()
        r = c.post(LOGIN, {"email": "nuevo@test.com", "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertNotIn("challenge_id", r.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_16_resend_da_nuevo_challenge_y_mata_viejo(self):
        with override_settings(OTP_RESEND_MIN_INTERVAL=0):
            c, ch1, code1 = self._challenge()
            r = c.post(RESEND, {"challenge_id": ch1}, format="json")
            self.assertEqual(r.status_code, 200)
            ch2 = r.data["challenge_id"]
            self.assertNotEqual(ch1, ch2)
            code2 = otp_from_mail()
            rv = c.post(VERIFY, {"challenge_id": ch1, "code": code1}, format="json")
            self.assertEqual(rv.status_code, 400)  # viejo muerto
            ok = c.post(VERIFY, {"challenge_id": ch2, "code": code2}, format="json")
            self.assertEqual(ok.status_code, 200)

    def test_17_e2e_registro_otp_sesion_logout(self):
        from .tokens import make_email_verification_token

        c = APIClient()
        r = c.post("/api/auth/register/", {
            "first_name": "Ana", "last_name": "Luz", "email": "ana@test.com",
            "phone": "+57 300 000 0001", "password": "Fuerte123!x", "password_confirm": "Fuerte123!x",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        user = User.objects.get(email="ana@test.com")
        token = make_email_verification_token(user)
        self.assertEqual(c.post("/api/auth/email/verify/", {"token": token}, format="json").status_code, 200)
        mail.outbox = []
        rl = c.post(LOGIN, {"email": "ana@test.com", "password": "Fuerte123!x"}, format="json")
        self.assertEqual(rl.data["code"], "otp_required")
        ro = c.post(VERIFY, {"challenge_id": rl.data["challenge_id"], "code": otp_from_mail()}, format="json")
        self.assertEqual(ro.data["code"], "authenticated")
        self.assertEqual(c.get(SESSION).status_code, 200)
        self.assertEqual(c.post("/api/auth/logout/").status_code, 200)
        self.assertEqual(c.get(SESSION).status_code, 403)
