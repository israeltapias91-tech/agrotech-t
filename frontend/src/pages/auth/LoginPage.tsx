import { useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import PasswordInput from '../../components/auth/PasswordInput'
import SocialLoginButtons from '../../components/auth/SocialLoginButtons'
import { isEmail } from '../../utils/validation'

/* Visual solamente: sin fetch, sin backend. */
export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [status, setStatus] = useState<'idle' | 'loading' | 'demo-error'>('idle')

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const next: typeof errors = {}
    if (!email.trim()) next.email = 'El correo es requerido'
    else if (!isEmail(email)) next.email = 'Formato de correo inválido'
    if (!password) next.password = 'La contraseña es requerida'
    setErrors(next)
    if (Object.keys(next).length > 0) return
    setStatus('loading')
    window.setTimeout(() => setStatus('idle'), 1200) // demo visual
  }

  return (
    <AuthLayout>
      <AuthCard title="Iniciar sesión" subtitle="Accede a tu cuenta de AgroTech-T">
        <form onSubmit={submit} noValidate>
          <AuthInput label="Correo electrónico" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={errors.email} placeholder="usuario@correo.com" />
          <PasswordInput label="Contraseña" name="password" value={password} onChange={(e) => setPassword(e.target.value)} error={errors.password} placeholder="••••••••" />
          {status === 'demo-error' && (
            <div className="mb-4">
              <Alert kind="error" title="No pudimos iniciar sesión">
                Credenciales inválidas. Verifica tu correo y contraseña. (Vista previa de error)
              </Alert>
            </div>
          )}
          <Button loading={status === 'loading'}>Iniciar sesión</Button>
        </form>
        <div className="mt-4 flex items-center justify-between text-sm">
          <Link to="/forgot-password" className="font-medium text-forest-700 hover:text-forest-600">
            ¿Olvidaste tu contraseña?
          </Link>
          <Link to="/register" className="font-medium text-forest-700 hover:text-forest-600">
            Crear una cuenta
          </Link>
        </div>
        <button type="button" onClick={() => setStatus(status === 'demo-error' ? 'idle' : 'demo-error')} className="mt-3 text-xs text-neutral-400 underline">
          Vista previa: mostrar error
        </button>
        <SocialLoginButtons />
      </AuthCard>
    </AuthLayout>
  )
}
