"""AGROTECH accounts — adaptador correo transaccional HTTP (sin SMTP).

Responsabilidad única: transporte vía API HTTP (Resend).
La lógica de negocio (tokens, OTP, links, expiración, reintentos,
sesiones) vive en services.py.

Reglas:
- Nunca loguear códigos OTP, tokens, links con token ni API keys.
- Credenciales solo desde variables de entorno (vía settings).
- Sin SDK externo: urllib stdlib para mantener cero dependencias nuevas.
"""

import json
import urllib.error
import urllib.request


# User-Agent neutro obligatorio: sin él, el borde (Cloudflare) responde
# 403/error 1010 y la petición nunca llega a Resend (validado en prueba real).
USER_AGENT = "AGROTECH-T/1.0"


class EmailSendError(Exception):
    code = "email_send_failed"


def _cfg():
    from django.conf import settings

    return {
        "api_key": getattr(settings, "RESEND_API_KEY", ""),
        "sender": getattr(
            settings, "EMAIL_FROM", getattr(settings, "DEFAULT_FROM_EMAIL", "")
        ),
        "url": getattr(
            settings, "RESEND_API_URL", "https://api.resend.com/emails"
        ),
        "timeout": int(getattr(settings, "EMAIL_API_TIMEOUT_SECONDS", 10)),
    }


def _post(to_email: str, subject: str, text: str) -> None:
    """POST al endpoint Resend. Lanza EmailSendError ante cualquier fallo.

    Fallback dev/test (sin key): usa django.core.mail (console/locmem) para
    no exigir Resend en local y preservar `mail.outbox` en tests existentes.
    En producción (RESEND_API_KEY configurado) siempre va por HTTP, nunca SMTP.
    """
    cfg = _cfg()
    if not cfg["api_key"]:
        from django.core.mail import send_mail as django_send_mail

        try:
            django_send_mail(subject, text, cfg["sender"], [to_email], fail_silently=False)
        except Exception as exc:
            raise EmailSendError(
                f"No se pudo enviar el correo: {type(exc).__name__}"
            ) from exc
        return
    if not cfg["sender"]:
        raise EmailSendError("Remitente no configurado")
    payload = json.dumps(
        {"from": cfg["sender"], "to": [to_email], "subject": subject, "text": text}
    ).encode("utf-8")
    req = urllib.request.Request(
        cfg["url"],
        data=payload,
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            status = getattr(resp, "status", 200)
            if status not in (200, 201, 202):
                raise EmailSendError(f"Proveedor respondió {status}")
    except EmailSendError:
        raise
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise EmailSendError(
            f"No se pudo enviar el correo: {type(exc).__name__}"
        ) from exc


def send_verification(to_email: str, link: str, hours: int) -> None:
    _post(
        to_email,
        "AGROTECH — verifica tu correo",
        f"Hola,\n\nConfirma tu correo pulsando este enlace "
        f"(válido {hours} h):\n{link}\n\n"
        "Si no creaste esta cuenta, ignora este mensaje.",
    )


def send_login_otp(to_email: str, code: str, minutes: int) -> None:
    _post(
        to_email,
        "AGROTECH — tu código de inicio de sesión",
        f"Hola,\n\nTu código para iniciar sesión es:\n\n{code}\n\n"
        f"Vence en {minutes} minutos. Si no intentaste entrar, ignora este mensaje.",
    )


def send_password_reset(to_email: str, link: str, hours: int) -> None:
    _post(
        to_email,
        "AGROTECH — recupera tu contraseña",
        f"Hola,\n\nRestablece tu contraseña aquí (válido {hours} h):\n{link}\n\n"
        "Si no lo pediste, ignora este mensaje.",
    )
