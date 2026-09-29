# AGROTECH — OTP de login por correo (verificación en dos pasos)

## Qué es (y qué no es)

Elegimos **OTP por correo como verificación en dos pasos para esta
versión**: la plataforma es online, ya teníamos infraestructura de
correo, y evitamos dependencias de telefonía (SMS/WhatsApp).

**No lo presentamos como el MFA más fuerte posible.** NIST no
considera el correo un canal aceptable para autenticación fuera de
banda (no demuestra posesión de un dispositivo específico).
Evolución futura: TOTP, passkeys/WebAuthn u otro factor independiente.

## Flujo

```text
login (email + password) -> otp_required + challenge_id (SIN sesión)
otp/verify (challenge_id + code) -> authenticated + sesión HttpOnly
otp/resend (challenge_id) -> nuevo challenge_id, anterior inválido
```

El `challenge_id` (UUID) liga el código a UN intento que ya pasó la
contraseña. Resend y verify nunca aceptan un email suelto.

## Parámetros (env)

```text
OTP_LENGTH=6  OTP_TIMEOUT_SECONDS=600  OTP_MAX_ATTEMPTS=5
OTP_RESEND_LIMIT=3  OTP_RESEND_WINDOW_SECONDS=900
OTP_RESEND_MIN_INTERVAL=60  EMAIL_OTP_THROTTLE_RATE=10/minute
```

## Garantías probadas (68 tests)

Hash con `make_password` (nunca plano ni en logs ni en JSON), un solo
uso, expiración, 5 intentos, anterior invalidado, 3 reenvíos/15 min,
sin sesión antes del OTP, suspendidos/sin verificar no llegan al OTP.
