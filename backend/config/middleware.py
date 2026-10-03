"""AGROTECH config — middleware propio mínimo (FASE 4).

Solo cabeceras seguras que no rompen React+Django en dev HTTP.
HSTS/redirect se gobiernan por env (apagados en dev).
"""

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


CSP_REPORT_ONLY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if getattr(settings, "CSP_REPORT_ONLY", True):
            # Report-Only: no bloquea (HMR de Vite y estilos inline siguen
            # funcionando); las violaciones salen por consola. Graduar a
            # enforce solo tras probar en staging con mismo origen+TLS.
            response.headers.setdefault("Content-Security-Policy-Report-Only", CSP_REPORT_ONLY)
        return response
