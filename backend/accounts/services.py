"""AGROTECH accounts — servicios de verificación de email.

Verificar un correo significa: probar que quien pidió la cuenta controla
el buzón. No autentica (no crea sesión), solo flipa email_verified.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .tokens import (
    BadSignature,
    SignatureExpired,
    make_email_verification_token,
    unsign_email_verification_token,
)


class EmailVerificationError(Exception):
    code = "verification_error"


class TokenInvalid(EmailVerificationError):
    code = "token_invalid"


class TokenExpired(EmailVerificationError):
    code = "token_expired"


class AlreadyVerified(EmailVerificationError):
    code = "already_verified"


class UserNotFound(EmailVerificationError):
    code = "user_not_found"


class EmailTaken(EmailVerificationError):
    code = "email_taken"


def _user_model():
    return get_user_model()


def build_verification_link(token: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/verify-email?token={token}"


def send_verification_email(user, token: str) -> str:
    """Envía el correo. Devuelve el link (útil en dev/tests)."""
    link = build_verification_link(token)
    subject = "AGROTECH — verifica tu correo"
    body = (
        f"Hola,\n\nConfirma tu correo pulsando este enlace "
        f"(válido {int(getattr(settings, 'EMAIL_VERIFICATION_TIMEOUT_SECONDS', 86400)) // 3600} h):\n{link}\n\n"
        "Si no creaste esta cuenta, ignora este mensaje."
    )
    send_mail(
        subject,
        body,
        getattr(settings, "DEFAULT_FROM_EMAIL", "AGROTECH <no-reply@agrotech.local>"),
        [user.email],
        fail_silently=False,
    )
    return link


def request_verification(user) -> tuple[str, str]:
    """Genera token + envía correo. Devuelve (token, link)."""
    token = make_email_verification_token(user)
    link = send_verification_email(user, token)
    return token, link


def verify_email(token: str):
    """Valida token y marca email_verified=True. Uso único: segundo uso -> AlreadyVerified."""
    try:
        user_pk, token_email = unsign_email_verification_token(token)
    except SignatureExpired as exc:
        raise TokenExpired("El enlace expiró, pide uno nuevo") from exc
    except BadSignature as exc:
        raise TokenInvalid("Enlace inválido o alterado") from exc

    try:
        user = _user_model().objects.get(pk=user_pk)
    except _user_model().DoesNotExist as exc:
        raise TokenInvalid("Cuenta no encontrada") from exc

    if user.email_verified:
        raise AlreadyVerified("El correo ya fue verificado")
    if user.email != token_email:
        # El correo pendiente cambió después de emitir el token.
        raise TokenInvalid("El correo cambió, pide un nuevo enlace")
    user.email_verified = True
    user.save(update_fields=["email_verified", "is_active", "updated_at"])
    return user


def resend_verification(email: str):
    """Reenvía el correo si la cuenta existe y sigue sin verificar."""
    email = _user_model().objects.normalize_email(email)
    try:
        user = _user_model().objects.get(email__iexact=email)
    except _user_model().DoesNotExist as exc:
        raise UserNotFound("Si la cuenta existe, reenviamos el correo") from exc
    if user.email_verified:
        raise AlreadyVerified("El correo ya fue verificado")
    return user, *request_verification(user)


def change_pending_email(token: str, new_email: str):
    """Cambia el correo pendiente (con token vigente del correo anterior).

    Invalida el token viejo porque el nuevo token liga el email nuevo.
    """
    try:
        user_pk, token_email = unsign_email_verification_token(token)
    except SignatureExpired as exc:
        raise TokenExpired("El enlace expiró, pide uno nuevo") from exc
    except BadSignature as exc:
        raise TokenInvalid("Enlace inválido o alterado") from exc

    try:
        user = _user_model().objects.get(pk=user_pk)
    except _user_model().DoesNotExist as exc:
        raise TokenInvalid("Cuenta no encontrada") from exc

    if user.email_verified:
        raise AlreadyVerified("El correo ya fue verificado, usa tu cuenta")
    if user.email != token_email:
        raise TokenInvalid("El enlace ya no es vigente")

    User = _user_model()
    new_email = User.objects.normalize_email(new_email)
    if not new_email:
        raise TokenInvalid("Nuevo correo inválido")
    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        raise EmailTaken("Ese correo ya está en uso")

    user.email = new_email
    user.email_verified = False
    user.save(update_fields=["email", "email_verified", "is_active", "updated_at"])
    new_token, link = request_verification(user)
    return user, new_token, link
