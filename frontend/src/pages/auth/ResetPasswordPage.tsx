import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { userMessage } from '../../api/errors'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import PasswordInput from '../../components/auth/PasswordInput'
import { passwordRules } from '../../utils/validation'

type State = 'form' | 'processing' | 'changed' | 'invalid' | 'expired'

/* uid+token desde la URL (?uid=&token=). Sin auto-login: volver a /login. */
export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<{ password?: string; confirm?: string }>({})
  const [apiError, setApiError] = useState('')
  const [apiMessages, setApiMessages] = useState<string[]>([])
  const [state, setState] = useState<State>('form')

  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''
  const linkOk = Boolean(uid && token)

  const rules = passwordRules(password)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const next: typeof errors = {}
    if (!password) next.password = 'La nueva contraseña es requerida'
    else if (rules.some((r) => !r.ok)) next.password = 'Revisa las reglas de contraseña'
    if (confirm !== password) next.confirm = 'Debe coincidir con la nueva contraseña'
    setErrors(next)
    if (Object.keys(next).length > 0) return
    setApiError('')
    setApiMessages([])
    setState('processing')
    try {
      await authApi.confirmPasswordReset({ uid, token, new_password: password, new_password_confirm: confirm })
      setState('changed')
    } catch (err) {
      if (err instanceof ApiError && err.code === 'token_expired') setState('expired')
      else if (err instanceof ApiError && err.code === 'token_invalid') setState('invalid')
      else {
        setState('form')
        if (err instanceof ApiError && err.code === 'password_too_weak') {
          setErrors((p) => ({ ...p, password: userMessage(err.code) }))
          setApiMessages(err.messages ?? [])
        } else if (err instanceof ApiError && err.code === 'password_mismatch') {
          setErrors((p) => ({ ...p, confirm: userMessage(err.code) }))
        } else setApiError(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
      }
    }
  }

  if (state === 'changed') {
    return (
      <AuthLayout>
        <AuthCard title="Contraseña actualizada" subtitle="Ya puedes entrar con tu nueva contraseña">
          <Alert kind="success" title="Cambio exitoso">
            Tu contraseña fue actualizada.
          </Alert>
          <Link to="/login" className="mt-4 block text-center text-sm font-medium text-forest-700 hover:text-forest-600">
            Volver al inicio de sesión
          </Link>
        </AuthCard>
      </AuthLayout>
    )
  }

  if (state === 'invalid' || state === 'expired') {
    return (
      <AuthLayout>
        <AuthCard title="Enlace no válido" subtitle="Solicita un nuevo enlace de recuperación">
          <Alert kind="error" title={state === 'invalid' ? 'Enlace inválido' : 'Enlace expirado'}>
            {state === 'invalid' ? 'Este enlace no es válido o ya fue utilizado.' : 'Este enlace venció. Pide uno nuevo.'}
          </Alert>
          <Link to="/forgot-password" className="mt-4 block text-center text-sm font-medium text-forest-700 hover:text-forest-600">
            Pedir un nuevo enlace
          </Link>
        </AuthCard>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <AuthCard title="Nueva contraseña" subtitle="Elige una contraseña segura">
        {!linkOk && (
          <div className="mb-4">
            <Alert kind="error" title="Enlace incompleto">
              Abre el enlace completo enviado a tu correo.
            </Alert>
          </div>
        )}
        <form onSubmit={(e) => void submit(e)} noValidate>
          <PasswordInput label="Nueva contraseña" name="password" value={password} onChange={(e) => setPassword(e.target.value)} error={errors.password} autoComplete="new-password" />
          <ul className="mb-4 space-y-1 text-xs" aria-label="Reglas de contraseña">
            {rules.map((r) => (
              <li key={r.id} className={r.ok ? 'text-forest-700' : 'text-neutral-500'}>
                {r.ok ? '✓' : '•'} {r.label}
              </li>
            ))}
          </ul>
          <PasswordInput label="Confirmar contraseña" name="confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} error={errors.confirm} autoComplete="new-password" />
          {apiMessages.length > 0 && (
            <ul className="mb-3 list-disc pl-5 text-xs text-red-600">
              {apiMessages.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
          {apiError && (
            <div className="mb-4">
              <Alert kind="error">{apiError}</Alert>
            </div>
          )}
          <Button loading={state === 'processing'}>Actualizar contraseña</Button>
        </form>
      </AuthCard>
    </AuthLayout>
  )
}
