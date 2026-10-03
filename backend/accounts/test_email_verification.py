"""AGROTECH — pruebas de verificación de email (sin JWT, TimestampSigner)."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.signing import SignatureExpired as DjangoExpired
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import services
from .tokens import make_email_verification_token

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="nuevo@test.com", password="Secreta123!")

    def test_token_roundtrip_verifica(self):
        token = make_email_verification_token(self.user)
        user = services.verify_email(token)
        self.assertTrue(user.email_verified)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_uso_unico_segundo_uso_da_already(self):
        token = make_email_verification_token(self.user)
        services.verify_email(token)
        with self.assertRaises(services.AlreadyVerified):
            services.verify_email(token)

    def test_token_alterado_invalido(self):
        token = make_email_verification_token(self.user) + "x"
        with self.assertRaises(services.TokenInvalid):
            services.verify_email(token)

    def test_token_expirado(self):
        token = make_email_verification_token(self.user)
        with self.assertRaises(DjangoExpired):
            services.unsign_email_verification_token(token, max_age=-1)
        with override_settings(EMAIL_VERIFICATION_TIMEOUT_SECONDS=-1):
            with self.assertRaises(services.TokenExpired):
                services.verify_email(token)

    def test_resend_envia_correo(self):
        mail.outbox = []
        user, token, link = services.resend_verification("nuevo@test.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)
        self.assertIn("token=", link)

    def test_resend_ya_verificado(self):
        services.verify_email(make_email_verification_token(self.user))
        with self.assertRaises(services.AlreadyVerified):
            services.resend_verification("nuevo@test.com")

    def test_change_pendiente_invalida_token_viejo(self):
        old_token = make_email_verification_token(self.user)
        user, new_token, _ = services.change_pending_email(old_token, "otro@test.com")
        self.assertEqual(user.email, "otro@test.com")
        self.assertFalse(user.email_verified)
        with self.assertRaises(services.TokenInvalid):
            services.verify_email(old_token)  # viejo liga email anterior
        services.verify_email(new_token)  # nuevo sí verifica
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_change_email_tomado(self):
        User.objects.create_user(email="tengo@test.com", password="x")
        token = make_email_verification_token(self.user)
        with self.assertRaises(services.EmailTaken):
            services.change_pending_email(token, "tengo@test.com")

    def test_endpoint_verify_ok_y_reuso(self):
        c = APIClient()
        token = make_email_verification_token(self.user)
        r = c.post("/api/auth/email/verify/", {"token": token}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "verified")
        r2 = c.post("/api/auth/email/verify/", {"token": token}, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.data["code"], "already_verified")

    def test_endpoint_verify_expirado(self):
        c = APIClient()
        token = make_email_verification_token(self.user)
        with override_settings(EMAIL_VERIFICATION_TIMEOUT_SECONDS=-1):
            r = c.post("/api/auth/email/verify/", {"token": token}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "token_expired")

    def test_endpoint_resend_y_change(self):
        c = APIClient()
        r = c.post("/api/auth/email/resend/", {"email": "nuevo@test.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        token = make_email_verification_token(self.user)
        r2 = c.post(
            "/api/auth/email/change/",
            {"token": token, "new_email": "final@test.com"},
            format="json",
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["email"], "final@test.com")
