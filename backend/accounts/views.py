"""AGROTECH accounts — verificación + login/logout/sesión/CSRF."""

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .services import EmailVerificationError, LoginError, PasswordResetError, RegistrationError


def _error(exc, http_status):
    body = {"code": exc.code, "detail": str(exc)}
    if getattr(exc, "messages", None):
        body["messages"] = list(exc.messages)
    return Response(body, status=http_status)


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
    """Fase 1: correo + contraseña -> desafío OTP (SIN sesión todavía).

    La sesión definitiva nace solo en OtpVerifyView. Throttling
    ScopedRateThrottle (scope 'login') = primera capa anti fuerza
    bruta; el OTP suma sus propias capas (intentos, expiración, reenvíos).
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
        otp = services.issue_login_otp(user)  # sin django_login() aquí
        return Response(
            {
                "code": "otp_required",
                "detail": "Revisa tu correo e introduce el código",
                "challenge_id": str(otp.challenge_id),
            },
            status=status.HTTP_200_OK,
        )


class OtpVerifyView(APIView):
    """Fase 2: challenge_id + code -> sesión Django definitiva."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_otp"

    def post(self, request):
        challenge_id = request.data.get("challenge_id", "")
        code = request.data.get("code", "")
        if not challenge_id or not code:
            return Response(
                {"code": "fields_required", "detail": "challenge_id y code requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = services.verify_login_otp(challenge_id, code)
        except services.OTPExpired as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        except services.OTPAttemptsExceeded as exc:
            return _error(exc, status.HTTP_429_TOO_MANY_REQUESTS)
        except services.OTPError as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        django_login(request, user)  # aquí sí: sesión nueva, anteriores vivas
        return Response(
            {
                "code": "authenticated",
                "detail": "Sesión creada",
                "email": user.email,
                "account_status": user.account_status,
            },
            status=status.HTTP_200_OK,
        )


class OtpResendView(APIView):
    """Reenvío ligado al desafío (que ya pasó la contraseña)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_otp"

    def post(self, request):
        challenge_id = request.data.get("challenge_id", "")
        if not challenge_id:
            return Response(
                {"code": "fields_required", "detail": "challenge_id requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            otp = services.resend_login_otp(challenge_id)
        except services.OTPError as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "code": "otp_resent",
                "detail": "Nuevo código enviado, el anterior quedó inválido",
                "challenge_id": str(otp.challenge_id),
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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Setea csrftoken para React (GET previo al login)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"code": "csrf_set", "detail": "CSRF cookie lista"}, status=status.HTTP_200_OK)


class LogoutAllView(APIView):
    """Cierra TODAS las sesiones del usuario excepto la actual."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        closed = services.keep_only_current_session(request)
        return Response(
            {"code": "all_closed", "detail": f"Se cerraron {closed} sesiones (actual viva)"},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """Siempre neutra (no enumera): mismo 200 exista o no la cuenta."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = request.data.get("email", "")
        if not email:
            return Response(
                {"code": "email_required", "detail": "Email requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.request_password_reset(email)
        return Response(
            {"code": "reset_sent", "detail": "Si la cuenta existe, enviamos el enlace"},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Valida token + política Django, guarda hash. Decisión A: sin sesión.

    Sesiones: CASO 1 (autenticado como el dueño) -> actual viva, demás
    muertas. CASO 2 (anónimo) -> mueren TODAS ya mismo.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")
        confirm = request.data.get("new_password_confirm", "")
        if not uid or not token or not new_password:
            return Response(
                {"code": "fields_required", "detail": "uid, token y new_password requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = services.confirm_password_reset(uid, token, new_password, confirm)
        except PasswordResetError as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        if request.user.is_authenticated and str(request.user.pk) == str(user.pk):
            services.rotate_on_password_change(request, user)  # CASO 1
        else:
            services.revoke_all_sessions(user)  # CASO 2
        return Response(
            {"code": "password_changed", "detail": "Contraseña actualizada, inicia sesión"},
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    """Crea cuenta sin verificar + dispara verificación. Sin auto-login."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration"

    def post(self, request):
        try:
            user, _, _ = services.register_user(
                first_name=request.data.get("first_name", ""),
                last_name=request.data.get("last_name", ""),
                email=request.data.get("email", ""),
                phone=request.data.get("phone", ""),
                password=request.data.get("password", ""),
                password_confirm=request.data.get("password_confirm", ""),
            )
        except (RegistrationError, EmailVerificationError, PasswordResetError) as exc:
            return _error(exc, status.HTTP_400_BAD_REQUEST)
        body = {"code": "registered", "detail": "Cuenta creada, verifica tu correo", "email": user.email}
        return Response(body, status=status.HTTP_201_CREATED)
