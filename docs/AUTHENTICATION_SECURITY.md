# AGROTECH-T — Seguridad del módulo de autenticación (FASE 4)

## 1. Arquitectura

```text
React (fetch, sin JWT, sin storage) → DRF SessionAuthentication
→ accounts (User UUID + EmailOTP) → MariaDB
Sesión Django en DB + cookie `sessionid` HttpOnly 24h + CSRF.
```

## 2. Registro

`POST register/` (201): nombre, apellido, email único, teléfono
opcional con regex, password con validadores Django + confirmación.
Crea con `email_verified=False`, dispara verificación, sin auto-login.
Throttle `registration` 10/hora.

## 3. Verificación de correo

Token `TimestampSigner` stateless (`pk:email`, 24h). Endpoints
`verify/resend/change`. Reuso → `already_verified`; cambio de correo
invalida el anterior. Resend neutro (no enumera).

## 4. Login en dos fases

Fase 1 valida credenciales → estado → verificación → emite OTP
(`otp_required` + `challenge_id`, SIN sesión). Fase 2 valida OTP →
`django_login()` (rota `session_key` anti-fixation). Orden interno:
hash antes de revelar estado (no enumerar suspendidos/sin verificar).

## 5. OTP por correo

6 dígitos (`secrets`), 10 min, 5 intentos/código, 3 reenvíos/15 min,
intervalo 60 s. Hash `make_password`; plano solo en memoria para el
correo; nunca en JSON/logs. `challenge_id` UUID por desafío; reenvío
crea desafío nuevo e invalida el anterior. Reutilizar → inválido.

### Por qué correo (decisión contextual, honesta)

Zonas rurales con señal celular limitada; SMS indeseado como
dependencia; WhatsApp exige infraestructura/API y puede costar; ya
existe infraestructura de correo centralizada y escalable. **No se
presenta como el MFA más fuerte**: NIST no avala el email como canal
fuera de banda. Evolución futura: TOTP, WebAuthn/passkeys (no ahora).

## 6. Sesiones

Django Sessions, sin JWT. Múltiples vivas; `logout` cierra una,
`logout-all` las demás. Cambio de clave: actual viva, demás muertas
(`update_session_auth_hash` + borrado explícito). Reset anónimo:
mueren todas ya mismo. Fixation mitigada por rotación en login.

## 7. Cookies

`sessionid`: HttpOnly, Lax, Secure por env (False dev / True prod),
24h, sobrevive al cierre. `csrftoken`: legible por JS (header
`X-CSRFToken`), mismo Secure/SameSite. Nombres por defecto Django.

## 8. CSRF

Activo siempre. `GET csrf/` (AllowAny, `ensure_csrf_cookie`).
Pre-auth (login/OTP/register/reset) no lo exige; mutaciones con
sesión sí. Probado con cliente CSRF-estricto.

## 9. Rate limiting

Scopes: `login` 5/min, `password_reset` 5/min (solo request),
`registration` 10/hora, `email_otp` 10/min. 429 DRF estándar.
Primera capa, no única.

## 10. Backoff progresivo

Segunda capa (FASE 4), por clave en caché, ventana deslizante:
espera = `base * 2^(fallos-umbral)`, tope `max`. Login por email
(5/15min, 30s→5min); OTP por usuario (10/15min, 60s→10min).
Respuestas 429 `{code: login_backoff|otp_backoff, retry_after}`.
**Nunca permanente**: al expirar la ventana se reintenta; el éxito
limpia. Caché locmem en dev (un proceso); en prod multinstancia
usar Redis/caché compartida (pendiente de infraestructura).

## 11. Recuperación

`PasswordResetTokenGenerator` nativo (liga pk+hash+login+email;
cambiar clave lo invalida). Request neutro 200 siempre; confirm
valida política Django; decisión A (sin auto-login).

## 12. No enumeración

Mismo código+HTTP para existente/inexistente en login
(`invalid_credentials`), reset (`reset_sent`) y resend email
(`resent`). Orden hash-primero en login.

## 13. Logs y sanitización

Logger `agrotech.security` (consola, formato sin secretos).
Eventos: `auth.registered`, `auth.email.verified/changed`,
`auth.login.ok/fail`, `auth.otp.issued/ok/fail`,
`auth.session.logout_all`, `auth.password.changed/reset`.
Jamás: passwords, OTP, tokens, uid, cookies, SECRET_KEY.
Probado: eventos presentes y secretos ausentes.

## 14. Auditoría de acciones sensibles

Los eventos §13 SON la pista de auditoría actual (cambio de correo
y contraseña, logout-all, verificación, registro). No se registra
cada clic. Retención: PENDIENTE (depende de infra de producción).

## 15. Headers

Siempre: `X-Content-Type-Options: nosniff` (setting),
`Referrer-Policy: strict-origin-when-cross-origin` (setting),
`X-Frame-Options: DENY` (middleware Django),
`Permissions-Policy: camera=(), microphone=(), geolocation=(),
payment=()` (middleware propio) y `Content-Security-Policy-Report-Only`
(middleware propio, §16).

## 16. CSP

Report-Only primero: `default-src 'self'; script-src 'self';
style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src
'self'; frame-ancestors 'none'` (sin `report-uri`: va a consola).
Graduar a enforce solo tras probar en staging con mismo origen+TLS.
HSTS progresivo: `SECURE_HSTS_SECONDS=0` en dev; en prod activar
tras comprobar HTTPS (`includeSubDomains`/preload después).

## 17. Dev vs prod

| Ajuste | Dev | Prod |
|---|---|---|
| `DEBUG` | True | False |
| `SECRET_KEY` | `.env` | gestor de secretos |
| `ALLOWED_HOSTS` | 127.0.0.1,localhost | dominios reales (nunca `*`) |
| CORS | solo `:5173` locales | dominio real frontend |
| `SESSION/CSR F_SECURE` | False | True |
| `SECURE_SSL_REDIRECT` | False | True (con HTTPS verificado) |
| Email | consola/Mailpit | SMTP real |

## 18. Decisiones técnicas

PBKDF2 de Django (sin cambio), `UniqueConstraint` donde aplique,
`PROTECT` en FK históricas, `challenge_id` en vez de email+code,
hash-antes-de-estado, sin auto-login tras reset/registro.

## 19. Limitaciones actuales

Caché locmem (backoff/throttle por proceso); sin Redis/WAF/captcha;
CSP solo reporta; retención de logs pendiente; email-OTP no es OOB
fuerte (ver §5).

## 20. Evolución futura

TOTP, WebAuthn/passkeys, SSO (Google/Microsoft/Apple), Redis,
WAF/fail2ban, CSP enforce, HSTS preload, retención definida.

## Matriz amenaza → protección → evidencia

| Amenaza | Protección | Evidencia |
|---|---|---|
| Fuerza bruta login | throttle 5/min + backoff 5/15min | `test_throttle_login`, `test_backoff_login_progresivo` |
| Fuerza bruta OTP | 5 intentos + backoff + expiración | `test_08_maximo_intentos`, `test_backoff_otp` |
| Robo sesión vía JS | HttpOnly | inspección `Set-Cookie` (`test_cookie_flags_y_edad`) |
| CSRF | Django + `X-CSRFToken` | `test_csrf_flujo_react` |
| Fixation | rotación en login | `test_fixation_key_rota_en_login` |
| Enumeración | respuestas/códigos neutros | `test_login_no_enumera`, `test_reset_no_enumera` |
| Reuso OTP | `used_at`/`superseded_at` | `test_06_reutilizado`, `test_07_anterior_invalidado` |
| Filtración secretos | `.env` + hash + sanitización | `test_logs_eventos_sin_secretos`, revisión Git |
| Clickjacking/MIME | DENY + nosniff | `test_headers_base` |
| Reenvío abusivo | 3/15min + 60 s + throttle | `test_09_exceso_reenvios`, `test_intervalo_minimo_reenvio` |
