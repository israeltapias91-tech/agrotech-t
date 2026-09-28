"""AGROTECH accounts — endpoints de verificación (pre-auth, AllowAny)."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .services import EmailVerificationError


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
