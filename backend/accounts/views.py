"""AGROTECH accounts — verificación (pre-auth) + login/logout/sesión."""

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .services import EmailVerificationError, LoginError


def _error(exc: EmailVerificationError, http_status):
    return Response({"code": exc.code, "detail": str(exc)}, status=http_status)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "")
        if not token:
            return Response(
                {"code": "token_required", "detail": "Token requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = services.verify_email(token)
        except services.TokenExpired as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        except services.AlreadyVerified as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        except EmailVerificationError as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        return Response(
            {"code": "verified", "detail": "Correo verificado", "email": user.email},
            status=status.HTTP_200_OK,
        )


class EmailResendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        if not email:
            return Response(
                {"code": "email_required", "detail": "Email requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            services.resend_verification(email)
        except services.AlreadyVerified as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        except services.UserNotFound:
            # No enumerar: respuesta genérica OK.
            pass
        return Response(
            {"code": "resent", "detail": "Si la cuenta existe, reenviamos el correo"},
            status=status.HTTP_200_OK,
        )


class EmailChangeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "")
        new_email = request.data.get("new_email", "")
        if not token or not new_email:
            return Response(
                {"code": "fields_required", "detail": "token y new_email requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user, _, _ = services.change_pending_email(token, new_email)
        except EmailVerificationError as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "code": "changed",
                "detail": "Correo actualizado, revisa tu nuevo buzón",
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    """Correo + contraseña -> sesión Django (cookie HttpOnly, 24h).

    Throttling ScopedRateThrottle (scope 'login') = primera capa anti
    fuerza bruta. NO es la única defensa: falta backoff por cuenta,
    captcha y WAF/fail2ban en fases posteriores.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        if not email or not password:
            return Response(
                {"code": "fields_required", "detail": "email y password requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = services.authenticate_for_login(email, password)
        except services.InvalidCredentials as exc:
            return Response(
                {"code": exc.code, "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except LoginError as exc:
            return Response(
                {"code": exc.code, "detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        django_login(request, user)  # crea sesión nueva, las anteriores siguen vivas
        return Response(
            {
                "code": "authenticated",
                "detail": "Sesión creada",
                "email": user.email,
                "account_status": user.account_status,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """Cierra SOLO la sesión actual (las demás siguen vivas)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        django_logout(request)
        return Response(
            {"code": "logged_out", "detail": "Sesión cerrada"},
            status=status.HTTP_200_OK,
        )


class SessionView(APIView):
    """Quién soy (para React + pruebas de sesiones múltiples)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "authenticated": True,
                "email": request.user.email,
                "account_status": request.user.account_status,
                "email_verified": request.user.email_verified,
            },
            status=status.HTTP_200_OK,
        )
