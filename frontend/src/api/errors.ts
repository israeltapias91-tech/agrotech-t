/* Mensajes seguros para el usuario a partir del `code` lógico de Django.
   La lógica usa `code`; el texto mostrado nunca filtra información sensible. */

const MAP: Record<string, string> = {
  invalid_credentials: 'Correo o contraseña inválidos.',
  account_suspended: 'Tu cuenta está suspendida. Contacta soporte.',
  account_deactivated: 'Tu cuenta está desactivada. Contacta soporte.',
  email_not_verified: 'Debes verificar tu correo antes de entrar. Revisa tu bandeja.',
  otp_invalid: 'Código incorrecto o ya utilizado.',
  otp_expired: 'El código expiró. Pide uno nuevo.',
  otp_attempts_exceeded: 'Demasiados intentos. Pide un código nuevo.',
  otp_resend_limited: 'Límite de reenvíos alcanzado. Espera unos minutos.',
  token_invalid: 'El enlace no es válido o ya fue utilizado.',
  token_expired: 'El enlace expiró. Pide uno nuevo.',
  already_verified: 'El correo ya fue verificado.',
  email_taken: 'Ese correo ya está registrado.',
  email_invalid: 'Correo inválido.',
  phone_invalid: 'Teléfono inválido.',
  password_mismatch: 'Las contraseñas no coinciden.',
  password_too_weak: 'La contraseña no cumple los requisitos.',
  fields_required: 'Completa los campos requeridos.',
  email_required: 'El correo es requerido.',
  network_error: 'No pudimos conectar con el servidor. Verifica tu conexión.',
}

export function userMessage(code: string, fallback = 'Ocurrió un error inesperado. Intenta de nuevo.'): string {
  return MAP[code] ?? fallback
}
