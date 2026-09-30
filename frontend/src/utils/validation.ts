/* Validación SOLO visual/local. El backend decide siempre. */

export function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

export type PasswordRule = { id: string; label: string; ok: boolean }

export function passwordRules(password: string): PasswordRule[] {
  return [
    { id: 'len', label: 'Mínimo 8 caracteres', ok: password.length >= 8 },
    { id: 'num', label: 'No solo números', ok: !/^\d+$/.test(password) || password.length === 0 },
    { id: 'common', label: 'Evita claves comunes (123456, password)', ok: !/^(123456|password|qwerty)$/i.test(password) },
  ]
}

export function isOtp(value: string): boolean {
  return /^\d{6}$/.test(value)
}
