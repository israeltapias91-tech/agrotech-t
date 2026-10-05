"""AGROTECH — configuración TLS de la base de datos (DB_SSL_MODE).

Caso A: DB_SSL_MODE=REQUIRED -> OPTIONS["ssl_mode"] == "REQUIRED".
Caso B: ausente/vacío -> no se fuerza ssl_mode (local sin SSL intacto).
Sin conexión real: solo recarga del módulo de settings con env simulado.
"""

import importlib
import os
from unittest import mock

from django.test import SimpleTestCase


def _reload_settings():
    import config.settings as s

    return importlib.reload(s)


class DbSslModeTests(SimpleTestCase):
    def tearDown(self):
        _reload_settings()  # restaura settings según el .env real

    def test_a_required_activa_ssl_mode(self):
        with mock.patch.dict(os.environ, {"DB_SSL_MODE": "REQUIRED"}):
            s = _reload_settings()
        self.assertEqual(s.DATABASES["default"]["OPTIONS"].get("ssl_mode"), "REQUIRED")

    def test_b_ausente_no_fuerza_ssl(self):
        env = {k: v for k, v in os.environ.items() if k != "DB_SSL_MODE"}
        with mock.patch.dict(os.environ, env, clear=True):
            s = _reload_settings()
        self.assertNotIn("ssl_mode", s.DATABASES["default"]["OPTIONS"])

    def test_b_vacio_no_fuerza_ssl(self):
        with mock.patch.dict(os.environ, {"DB_SSL_MODE": ""}):
            s = _reload_settings()
        self.assertNotIn("ssl_mode", s.DATABASES["default"]["OPTIONS"])
