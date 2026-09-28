"""AGROTECH accounts — servicios de verificación de email.

Verificar un correo significa: probar que quien pidió la cuenta controla
el buzón. No autentica (no crea sesión), solo flipa email_verified.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import base36_to_int, urlsafe_base64_decode, urlsafe_base64_encode

import datetime

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


class LoginError(Exception):
    code = "login_error"


class InvalidCredentials(LoginError):
    code = "invalid_credentials"


class AccountSuspended(LoginError):
    code = "account_suspended"


class AccountDeactivated(LoginError):
    code = "account_deactivated"


class EmailNotVerified(LoginError):
    code = "email_not_verified"


def authenticate_for_login(email: str, password: str):
    """Puertas del login (mismas que el flujo, orden seguro Django).

    Orden: credenciales (hash) -> cuenta activa -> correo verificado.
    Se verifica la contraseña ANTES de revelar estado, para no enumerar
    cuentas suspendidas/sin verificar con cualquier contraseña. Las
    puertas son las mismas, solo cambia el orden de evaluación.
    """
    User = _user_model()
    email = User.objects.normalize_email(email or "")
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist as exc:
        raise InvalidCredentials("Correo o contraseña inválidos") from exc

    if not user.check_password(password or ""):
        raise InvalidCredentials("Correo o contraseña inválidos")
    if user.account_status == User.AccountStatus.SUSPENDED:
        raise AccountSuspended("Cuenta suspendida, contacta soporte")
    if user.account_status == User.AccountStatus.DEACTIVATED:
        raise AccountDeactivated("Cuenta desactivada, contacta soporte")
    if not user.email_verified:
        raise EmailNotVerified("Debes verificar tu correo antes de entrar")
    return user


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


# --- Sesiones (feature/auth-session-security) ---

SESSION_KEY = "_auth_user_id"


def _decode_session(session) -> str | None:
    try:
        return str(session.get_decoded().get(SESSION_KEY))
    except Exception:
        return None


def active_session_keys(user, exclude_key: str | None = None) -> list[str]:
    """Keys de sesiones vivas del usuario (para matriz PC/celular/tablet)."""
    from django.contrib.sessions.models import Session

    keys = []
    for s in Session.objects.filter(expire_date__gt=timezone.now()):
        if _decode_session(s) == str(user.pk) and s.session_key != exclude_key:
            keys.append(s.session_key)
    return keys


def keep_only_current_session(request) -> int:
    """Cierra TODAS las sesiones del usuario excepto la actual.

    Decisión: el cierre global excluye la invocante (no te expulsa).
    Devuelve cuántas cerró.
    """
    from django.contrib.sessions.models import Session

    current = request.session.session_key
    doomed = active_session_keys(request.user, exclude_key=current)
    if doomed:
        Session.objects.filter(session_key__in=doomed).delete()
    return len(doomed)


def rotate_on_password_change(request, user) -> None:
    """Política tras cambiar contraseña: actual viva, demás muertas.

    Decisión: cerrar las demás. `update_session_auth_hash` rota el hash
    en la sesión actual (la mantiene) e invalida las demás porque el
    session auth hash ya no coincide. Reutilizar en password-reset.

    Nota Django 5.2: la función ya no persiste (`save` desapareció) y
    solo rota el hash si `request.user == user`. Guardamos explícito
    para no depender del middleware al final del response.
    """
    from django.contrib.auth import update_session_auth_hash

    update_session_auth_hash(request, user)
    request.session.save()
    keep_only_current_session(request)


# --- Password reset (feature/auth-password-reset) ---
# Tokens nativos Django: ligan pk + hash + last_login + email + timestamp.
# Cambiar la clave invalida el token (reutilizar -> TokenInvalid).
# Decisión A: tras recuperar NO se crea sesión, se re-loguea normal.


class PasswordResetError(Exception):
    code = "password_reset_error"


class ResetTokenInvalid(PasswordResetError):
    code = "token_invalid"


class ResetTokenExpired(PasswordResetError):
    code = "token_expired"


class PasswordMismatch(PasswordResetError):
    code = "password_mismatch"


class PasswordTooWeak(PasswordResetError):
    code = "password_too_weak"


def _uid(user) -> str:
    return urlsafe_base64_encode(force_bytes(str(user.pk)))


def _user_from_uid(uid: str):
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        return _user_model().objects.get(pk=pk)
    except Exception as exc:
        raise ResetTokenInvalid("Enlace inválido o alterado") from exc


def _check_reset_token(user, token: str) -> None:
    """Distingue expirado de manipulado (el generador solo da False)."""
    if default_token_generator.check_token(user, token):
        return
    try:
        ts_b36, _ = token.split("-")
        # Época del generador Django: 2001-01-01 (NO unix). Ver
        # PasswordResetTokenGenerator._num_seconds.
        made = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(
            seconds=base36_to_int(ts_b36)
        )
        age = (timezone.now() - made).total_seconds()
        if age > int(getattr(settings, "PASSWORD_RESET_TIMEOUT", 86400)):
            raise ResetTokenExpired("El enlace expiró, pide uno nuevo")
    except PasswordResetError:
        raise
    except Exception:
        pass
    raise ResetTokenInvalid("Enlace inválido o alterado")


def build_password_reset_link(uid: str, token: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/reset-password?uid={uid}&token={token}"


def request_password_reset(email: str):
    """Siempre neutro: devuelve (uid, token, link) o None. No enumera."""
    User = _user_model()
    try:
        user = User.objects.get(email__iexact=User.objects.normalize_email(email or ""))
    except User.DoesNotExist:
        return None
    if user.account_status != User.AccountStatus.ACTIVE:
        return None
    uid = _uid(user)
    token = default_token_generator.make_token(user)
    link = build_password_reset_link(uid, token)
    send_mail(
        "AGROTECH — recupera tu contraseña",
        f"Hola,\n\nRestablece tu contraseña aquí (válido "
        f"{int(getattr(settings, 'PASSWORD_RESET_TIMEOUT', 86400)) // 3600} h):\n{link}\n\n"
        "Si no lo pediste, ignora este mensaje.",
        getattr(settings, "DEFAULT_FROM_EMAIL", "AGROTECH <no-reply@agrotech.local>"),
        [user.email],
        fail_silently=False,
    )
    return user, uid, token, link


def confirm_password_reset(uid: str, token: str, new_password: str, confirm: str):
    """Valida token + política Django y guarda el nuevo hash. Sin sesión (A)."""
    user = _user_from_uid(uid)
    _check_reset_token(user, token)
    if not new_password or new_password != confirm:
        raise PasswordMismatch("Las contraseñas no coinciden")
    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        err = PasswordTooWeak("Contraseña demasiado débil")
        err.messages = list(exc.messages)
        raise err from exc
    user.set_password(new_password)
    user.save()
    return user


def revoke_all_sessions(user) -> int:
    """CASO 2 (anónimo): no hay sesión actual, mueren TODAS ya mismo."""
    from django.contrib.sessions.models import Session

    doomed = active_session_keys(user)
    if doomed:
        Session.objects.filter(session_key__in=doomed).delete()
    return len(doomed)


# --- Registro (feature/auth-registration) ---
# Fuente única de verificación: request_verification(). Sin finca,
# sin roles, sin suscripción (eso es multi-finca, no esta feature).

import re

PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


class RegistrationError(Exception):
    code = "registration_error"


class EmailInvalid(RegistrationError):
    code = "email_invalid"


class FieldsRequired(RegistrationError):
    code = "fields_required"


class PhoneInvalid(RegistrationError):
    code = "phone_invalid"


def register_user(first_name="", last_name="", email="", phone="",
                  password="", password_confirm=""):
    """Crea la cuenta sin verificar y dispara la verificación existente."""
    from django.core.validators import validate_email as _validate_email

    missing = [f for f, v in (
        ("first_name", first_name), ("last_name", last_name),
        ("email", email), ("password", password),
        ("password_confirm", password_confirm),
    ) if not (v or "").strip()]
    if missing:
        err = FieldsRequired(f"Faltan: {', '.join(missing)}")
        err.messages = missing
        raise err

    User = _user_model()
    email = User.objects.normalize_email(email.strip())
    try:
        _validate_email(email)
    except DjangoValidationError as exc:
        raise EmailInvalid("Correo inválido") from exc
    if User.objects.filter(email__iexact=email).exists():
        raise EmailTaken("Ese correo ya está registrado")
    if phone and not PHONE_RE.match(phone.strip()):
        raise PhoneInvalid("Teléfono inválido")
    if password != password_confirm:
        raise PasswordMismatch("Las contraseñas no coinciden")

    user = User(
        email=email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=(phone or "").strip(),
        email_verified=False,
    )
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        err = PasswordTooWeak("Contraseña demasiado débil")
        err.messages = list(exc.messages)
        raise err from exc
    user.set_password(password)  # hash, nunca plano
    user.save()
    token, link = request_verification(user)  # única fuente de verdad
    return user, token, link
