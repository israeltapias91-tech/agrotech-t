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

export function getCsrfToken(): string | null {
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
    throw new ApiError(
      res.status,
      typeof data.code === 'string' ? data.code : 'unknown_error',
      typeof data.detail === 'string' ? data.detail : 'Ocurrió un error inesperado.',
      Array.isArray(data.messages) ? (data.messages as string[]) : undefined,
    )
  }
  return data as T
}
