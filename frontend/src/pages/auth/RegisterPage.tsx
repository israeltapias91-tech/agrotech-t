import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { userMessage } from '../../api/errors'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import PasswordInput from '../../components/auth/PasswordInput'
import { isEmail, passwordRules } from '../../utils/validation'

export default function RegisterPage() {
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', phone: '', password: '', confirm: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [apiError, setApiError] = useState('')
  const [apiMessages, setApiMessages] = useState<string[]>([])
  const [status, setStatus] = useState<'idle' | 'loading' | 'success'>('idle')

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  const rules = passwordRules(form.password)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (!form.firstName.trim()) next.firstName = 'El nombre es requerido'
    if (!form.lastName.trim()) next.lastName = 'El apellido es requerido'
    if (!form.email.trim()) next.email = 'El correo es requerido'
    else if (!isEmail(form.email)) next.email = 'Formato de correo inválido'
    if (form.phone && !/^\+?[0-9\s\-()]{7,20}$/.test(form.phone.trim())) next.phone = 'Teléfono inválido'
    if (!form.password) next.password = 'La contraseña es requerida'
    else if (rules.some((r) => !r.ok)) next.password = 'Revisa las reglas de contraseña'
    if (form.confirm !== form.password) next.confirm = 'Debe coincidir con la contraseña'
    setErrors(next)
    if (Object.keys(next).length > 0) return
    setApiError('')
    setApiMessages([])
    setStatus('loading')
    try {
      await authApi.register({
        first_name: form.firstName.trim(),
        last_name: form.lastName.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        password: form.password,
        password_confirm: form.confirm,
      })
      setStatus('success')
    } catch (err) {
      setStatus('idle')
      if (err instanceof ApiError) {
        if (err.code === 'email_taken') setErrors((p) => ({ ...p, email: userMessage(err.code) }))
        else if (err.code === 'password_too_weak') {
          setErrors((p) => ({ ...p, password: userMessage(err.code) }))
          setApiMessages(err.messages ?? [])
        } else if (err.code === 'password_mismatch') setErrors((p) => ({ ...p, confirm: userMessage(err.code) }))
        else if (err.code === 'phone_invalid') setErrors((p) => ({ ...p, phone: userMessage(err.code) }))
        else if (err.code === 'email_invalid') setErrors((p) => ({ ...p, email: userMessage(err.code) }))
        else setApiError(userMessage(err.code, err.detail))
      } else setApiError('Ocurrió un error inesperado.')
    }
  }

  if (status === 'success') {
    return (
      <AuthLayout>
        <AuthCard title="Cuenta creada" subtitle="Revisa tu correo para verificarla">
          <Alert kind="success" title="Registro exitoso">
            Te enviamos un enlace de verificación a <strong>{form.email}</strong>.
          </Alert>
          <Link to="/verify-email" className="mt-4 block text-center text-sm font-medium text-forest-700 hover:text-forest-600">
            Ir a verificación de correo
          </Link>
        </AuthCard>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <AuthCard title="Crear cuenta" subtitle="Empieza a gestionar tu producción">
        <form onSubmit={(e) => void submit(e)} noValidate>
          <div className="grid gap-x-3 sm:grid-cols-2">
            <AuthInput label="Nombre" name="firstName" value={form.firstName} onChange={set('firstName')} error={errors.firstName} autoComplete="given-name" />
            <AuthInput label="Apellido" name="lastName" value={form.lastName} onChange={set('lastName')} error={errors.lastName} autoComplete="family-name" />
          </div>
          <AuthInput label="Correo electrónico" name="email" type="email" value={form.email} onChange={set('email')} error={errors.email} autoComplete="email" />
          <AuthInput label="Teléfono (opcional)" name="phone" type="tel" value={form.phone} onChange={set('phone')} error={errors.phone} autoComplete="tel" placeholder="+57 300 000 0000" />
          <PasswordInput label="Contraseña" name="password" value={form.password} onChange={set('password')} error={errors.password} autoComplete="new-password" />
          <ul className="mb-4 space-y-1 text-xs" aria-label="Reglas de contraseña">
            {rules.map((r) => (
              <li key={r.id} className={r.ok ? 'text-forest-700' : 'text-neutral-500'}>
                {r.ok ? '✓' : '•'} {r.label}
              </li>
            ))}
          </ul>
          <PasswordInput label="Confirmar contraseña" name="confirm" value={form.confirm} onChange={set('confirm')} error={errors.confirm} autoComplete="new-password" />
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
          <Button loading={status === 'loading'}>Crear cuenta</Button>
        </form>
        <p className="mt-4 text-center text-sm text-neutral-500">
          <Link to="/login" className="font-medium text-forest-700 hover:text-forest-600">
            Ya tengo una cuenta
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  )
}
