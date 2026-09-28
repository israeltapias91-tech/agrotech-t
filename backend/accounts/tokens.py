"""AGROTECH accounts — tokens de verificación de email (sin JWT).

Flujo: stateless con Django TimestampSigner. El token liga pk + email,
así un cambio de correo pendiente invalida el token anterior. El uso
único se garantiza porque verify marca email_verified=True y un segundo
uso devuelve AlreadyVerified.
"""

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner


def _signer() -> TimestampSigner:
    salt = getattr(settings, "EMAIL_VERIFICATION_SALT", "agrotech-email-verify")
    return TimestampSigner(salt=salt)


def _timeout() -> int:
    return int(getattr(settings, "EMAIL_VERIFICATION_TIMEOUT_SECONDS", 86400))


def make_email_verification_token(user) -> str:
    """Genera token firmado con caducidad para el usuario."""
    value = f"{user.pk}:{user.email}"
    return _signer().sign(value)


def unsign_email_verification_token(token: str, max_age=None) -> tuple[str, str]:
    """Desfirma el token. Devuelve (user_pk, email). Lanza Bad/Expired."""
    if max_age is None:
        max_age = _timeout()
    value = _signer().unsign(token, max_age=max_age)
    user_pk, sep, email = value.partition(":")
    if not sep or not user_pk or not email:
        raise BadSignature("Token malformado")
    return user_pk, email


__all__ = [
    "make_email_verification_token",
    "unsign_email_verification_token",
    "BadSignature",
    "SignatureExpired",
]
