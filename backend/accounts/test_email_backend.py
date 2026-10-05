"""AGROTECH — adaptador Resend HTTP (FASE AUTH EMAIL API).

Cubre: éxito, error API, timeout/red, y preservación de contratos
(registro 201+email_sent False, OTP sin sesión, reset neutro,
OTP anterior usable si el nuevo falla). Sin keys reales, todo mock.
"""

import re
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from . import email_backend
from .models import EmailOTP

PW = "Segura123!Fuerte"
ALTA = mock.patch.dict(
    ScopedRateThrottle.THROTTLE_RATES,
    {
        "login": "1000/minute",
        "password_reset": "1000/minute",
        "registration": "1000/hour",
        "email_otp": "1000/minute",
    },
)

RESEND_OK = {
    "RESEND_API_KEY": "re_test_key",
    "EMAIL_FROM": "AGROTECH <no-reply@test.local>",
}


class _FakeResp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen_ok(req, timeout=None):
    return _FakeResp()


@ALTA
class EmailBackendTests(TestCase):
    def test_01_post_exitoso_usa_bearer_sin_fugar_key(self):
        import urllib.request

        with override_settings(**RESEND_OK):
            with mock.patch.object(
                urllib.request, "urlopen", side_effect=_urlopen_ok
            ) as m:
                email_backend._post("a@test.com", "s", "cuerpo")
            req = m.call_args[0][0]
            self.assertIn("api.resend.com", req.full_url)
            auth = req.get_header("Authorization")
            self.assertTrue(auth.startswith("Bearer "))
            self.assertIn("re_test_key", auth)  # header, nunca en body/logs
            body = m.call_args[0][0].data.decode()
            self.assertNotIn("re_test_key", body)
            # Hallazgo prueba real: sin User-Agent, Cloudflare responde 403/1010.
            self.assertEqual(req.get_header("User-agent"), "AGROTECH-T/1.0")

    def test_02_error_api_401_lanza_EmailSendError(self):
        import urllib.error
        import urllib.request

        err = urllib.error.HTTPError(
            "https://api.resend.com/emails", 401, "Unauthorized", {}, None
        )
        with override_settings(**RESEND_OK):
            with mock.patch.object(urllib.request, "urlopen", side_effect=err):
                with self.assertRaises(email_backend.EmailSendError):
                    email_backend._post("a@test.com", "s", "c")

    def test_03_timeout_red_lanza_EmailSendError(self):
        import urllib.error
        import urllib.request

        with override_settings(**RESEND_OK):
            with mock.patch.object(
                urllib.request, "urlopen",
                side_effect=urllib.error.URLError("colgado"),
            ):
                with self.assertRaises(email_backend.EmailSendError):
                    email_backend._post("a@test.com", "s", "c")

    def test_04_registro_fallo_envio_201_sin_500(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        with mock.patch(
            "accounts.email_backend._post",
            side_effect=email_backend.EmailSendError("down"),
        ):
            r = APIClient().post(
                "/api/auth/register/",
                {
                    "first_name": "Juan",
                    "last_name": "Pérez",
                    "email": "juan@test.com",
                    "phone": "+57 300 123 4567",
                    "password": PW,
                    "password_confirm": PW,
                },
                format="json",
            )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["code"], "registered")
        self.assertFalse(r.data["email_sent"])
        u = User.objects.get(email="juan@test.com")
        self.assertFalse(u.email_verified)

    def test_05_login_fallo_envio_sin_sesion_ni_otp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user(
            email="user@test.com", password=PW, email_verified=True
        )
        c = APIClient()
        with mock.patch(
            "accounts.email_backend._post",
            side_effect=email_backend.EmailSendError("down"),
        ):
            r = c.post(
                "/api/auth/login/",
                {"email": "user@test.com", "password": PW},
                format="json",
            )
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.data["code"], "email_send_failed")
        self.assertNotIn("challenge_id", r.data)
        self.assertNotRegex(r.content.decode(), r"\d{6}")
        self.assertEqual(c.get("/api/auth/session/").status_code, 403)

    def test_06_reset_fallo_envio_neutro_sin_tokens(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user(
            email="user@test.com", password=PW, email_verified=True
        )
        c = APIClient()
        with mock.patch(
            "accounts.email_backend._post",
            side_effect=email_backend.EmailSendError("down"),
        ):
            r1 = c.post(
                "/api/auth/password/request/",
                {"email": "user@test.com"},
                format="json",
            )
            r2 = c.post(
                "/api/auth/password/request/",
                {"email": "nadie@test.com"},
                format="json",
            )
        for r in (r1, r2):
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data["code"], "reset_sent")
            self.assertNotIn("uid", r.data)
            self.assertNotIn("token", r.data)

    def test_07_otp_anterior_sigue_valido_si_nuevo_falla(self):
        """§15: el anterior solo se invalida tras envío exitoso del nuevo."""
        from django.contrib.auth import get_user_model

        from . import services

        User = get_user_model()
        user = User.objects.create_user(
            email="user@test.com", password=PW, email_verified=True
        )
        mail.outbox = []
        otp1 = services.issue_login_otp(user)  # fallback dev → locmem
        code1 = re.search(r"(\d{6})", mail.outbox[-1].body).group(1)
        n_before = EmailOTP.objects.filter(user=user).count()
        with mock.patch(
            "accounts.email_backend._post",
            side_effect=email_backend.EmailSendError("down"),
        ):
            with self.assertRaises(email_backend.EmailSendError):
                services.issue_login_otp(user)
        # El intento fallido no dejó desafío nuevo colgado…
        actives = EmailOTP.objects.filter(
            user=user, used_at__isnull=True, superseded_at__isnull=True
        )
        self.assertEqual(actives.count(), 1)
        self.assertEqual(actives.first().pk, otp1.pk)
        self.assertEqual(EmailOTP.objects.filter(user=user).count(), n_before)
        # …y el anterior sigue verificable (crea sesión real).
        c = APIClient()
        r = c.post(
            "/api/auth/otp/verify/",
            {"challenge_id": str(otp1.challenge_id), "code": code1},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["code"], "authenticated")
