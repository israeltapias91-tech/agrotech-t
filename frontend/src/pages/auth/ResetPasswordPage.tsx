import { useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import PasswordInput from '../../components/auth/PasswordInput'
import { passwordRules } from '../../utils/validation'

type State = 'form' | 'processing' | 'changed' | 'invalid' | 'expired'

/* Visual solamente: form/processing/changed/invalid/expired sin backend. */
export default function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<{ password?: string; confirm?: string }>({})
  const [state, setState] = useState<State>('form')

  const rules = passwordRules(password)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const next: typeof errors = {}
    if (!password) next.password = 'La nueva contraseña es requerida'
    else if (rules.some((r) => !r.ok)) next.password = 'Revisa las reglas de contraseña'
    if (confirm !== password) next.confirm = 'Debe coincidir con la nueva contraseña'
    setErrors(next)
    if (Object.keys(next).length > 0) return
    setState('processing')
    window.setTimeout(() => setState('changed'), 1200) // demo visual
  }

  if (state === 'changed') {
    return (
      <AuthLayout>
        <AuthCard title="Contraseña actualizada" subtitle="Ya puedes entrar con tu nueva contraseña">
          <Alert kind="success" title="Cambio exitoso">
            Tu contraseña fue actualizada. (Vista previa)
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
            {state === 'invalid'
              ? 'Este enlace no es válido o ya fue utilizado. (Vista previa)'
              : 'Este enlace venció. Pide uno nuevo. (Vista previa)'}
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
        <form onSubmit={submit} noValidate>
          <PasswordInput label="Nueva contraseña" name="password" value={password} onChange={(e) => setPassword(e.target.value)} error={errors.password} autoComplete="new-password" />
          <ul className="mb-4 space-y-1 text-xs" aria-label="Reglas de contraseña">
            {rules.map((r) => (
              <li key={r.id} className={r.ok ? 'text-forest-700' : 'text-neutral-500'}>
                {r.ok ? '✓' : '•'} {r.label}
              </li>
            ))}
          </ul>
          <PasswordInput label="Confirmar contraseña" name="confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} error={errors.confirm} autoComplete="new-password" />
          <Button loading={state === 'processing'}>Actualizar contraseña</Button>
        </form>
        <div className="mt-3 flex gap-3 text-xs">
          <span className="text-neutral-400">Vistas previas:</span>
          {(['invalid', 'expired'] as State[]).map((s) => (
            <button key={s} type="button" onClick={() => setState(s)} className="text-forest-700 underline">
              {s}
            </button>
          ))}
        </div>
      </AuthCard>
    </AuthLayout>
  )
}
