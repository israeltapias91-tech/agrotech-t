/* Servicios de autenticación. Contratos exactos del backend (FASE 0).
   Sin contraseñas ni OTP en storage: todo vive en memoria + cookie Django. */

import { apiFetch, setCsrfToken } from './client'

export type OtpRequired = { code: 'otp_required'; detail: string; challenge_id: string }
export type Authenticated = { code: 'authenticated'; detail: string; email: string; account_status: string }
export type SessionInfo = { authenticated: true; email: string; account_status: string; email_verified: boolean }

export const authApi = {
  async csrf(): Promise<{ code: string; csrfToken?: string }> {
    const data = await apiFetch<{ code: string; csrfToken?: string }>('/api/auth/csrf/')
    if (typeof data.csrfToken === 'string' && data.csrfToken.length > 0) {
      setCsrfToken(data.csrfToken)
    }
    return data
  },

  register(data: {
    first_name: string
    last_name: string
    email: string
    phone: string
    password: string
    password_confirm: string
  }): Promise<{ code: string; detail: string; email: string }> {
    return apiFetch('/api/auth/register/', { method: 'POST', body: data })
  },

  verifyEmail(token: string): Promise<{ code: string; detail: string; email: string }> {
    return apiFetch('/api/auth/email/verify/', { method: 'POST', body: { token } })
  },

  resendEmail(email: string): Promise<{ code: string; detail: string }> {
    return apiFetch('/api/auth/email/resend/', { method: 'POST', body: { email } })
  },

  changeEmail(token: string, new_email: string): Promise<{ code: string; detail: string; email: string }> {
    return apiFetch('/api/auth/email/change/', { method: 'POST', body: { token, new_email } })
  },

  login(email: string, password: string): Promise<OtpRequired> {
    return apiFetch('/api/auth/login/', { method: 'POST', body: { email, password } })
  },

  verifyOtp(challenge_id: string, code: string): Promise<Authenticated> {
    return apiFetch('/api/auth/otp/verify/', { method: 'POST', body: { challenge_id, code } })
  },

  resendOtp(challenge_id: string): Promise<{ code: string; detail: string; challenge_id: string }> {
    return apiFetch('/api/auth/otp/resend/', { method: 'POST', body: { challenge_id } })
  },

  session(): Promise<SessionInfo> {
    return apiFetch('/api/auth/session/')
  },

  logout(): Promise<{ code: string }> {
    return apiFetch('/api/auth/logout/', { method: 'POST', body: {} })
  },

  requestPasswordReset(email: string): Promise<{ code: string; detail: string }> {
    return apiFetch('/api/auth/password/request/', { method: 'POST', body: { email } })
  },

  confirmPasswordReset(data: {
    uid: string
    token: string
    new_password: string
    new_password_confirm: string
  }): Promise<{ code: string; detail: string }> {
    return apiFetch('/api/auth/password/confirm/', { method: 'POST', body: data })
  },
}
