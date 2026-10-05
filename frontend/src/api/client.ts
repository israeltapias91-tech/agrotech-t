/* Cliente HTTP centralizado. Única vía hacia Django. */

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {
  status: number
  code: string
  detail: string
  messages?: string[]

  constructor(status: number, code: string, detail: string, messages?: string[]) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
    this.messages = messages
  }
}

/* Token CSRF en memoria (nunca storage): lo provee GET /api/auth/csrf/.
   Necesario cross-site (Netlify -> Render), donde document.cookie no ve
   la cookie del dominio del backend. */
let memoryCsrfToken: string | null = null

export function setCsrfToken(token: string | null): void {
  memoryCsrfToken = token
}

export function getCsrfToken(): string | null {
  if (memoryCsrfToken) return memoryCsrfToken
  // Fallback desarrollo local (mismo sitio): leer la cookie.
  const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)
  return m ? decodeURIComponent(m[1]) : null
}

type Options = {
  method?: 'GET' | 'POST'
  body?: unknown
}

export async function apiFetch<T>(path: string, { method = 'GET', body }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (method !== 'GET') {
    const csrf = getCsrfToken()
    if (csrf) headers['X-CSRFToken'] = csrf
  }
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      credentials: 'include',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'network_error', 'No pudimos conectar con el servidor. Verifica tu conexión.')
  }
  let data: Record<string, unknown> = {}
  try {
    data = (await res.json()) as Record<string, unknown>
  } catch {
    data = {}
  }
  if (!res.ok) {
    // 429 de DRF (throttle) no trae `code`: se normaliza para mensaje adecuado.
    // 401 no lo emite el backend (SessionAuth responde 403); se mapea igual.
    let code = typeof data.code === 'string' ? data.code : 'unknown_error'
    if (code === 'unknown_error' && res.status === 429) code = 'rate_limited'
    if (code === 'unknown_error' && res.status === 401) code = 'session_expired'
    throw new ApiError(
      res.status,
      code,
      typeof data.detail === 'string' ? data.detail : 'Ocurrió un error inesperado.',
      Array.isArray(data.messages) ? (data.messages as string[]) : undefined,
    )
  }
  return data as T
}
