import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { userMessage } from '../../api/errors'
import { useAuth } from '../../auth/AuthContext'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import PasswordInput from '../../components/auth/PasswordInput'
import SocialLoginButtons from '../../components/auth/SocialLoginButtons'
import Alert from '../../components/ui/Alert'
import { isEmail } from '../../utils/validation'

/* FASE 1: guarda challenge_id en memoria y va a /otp. Sin sesión aún. */
export default function LoginPage() {
  const navigate = useNavigate()
  const { setChallengeId } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [apiError, setApiError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const next: typeof errors = {}
    if (!email.trim()) next.email = 'El correo es requerido'
    else if (!isEmail(email)) next.email = 'Formato de correo inválido'
    if (!password) next.password = 'La contraseña es requerida'
    setErrors(next)
    if (Object.keys(next).length > 0) return
    setApiError('')
    setLoading(true)
    try {
      const res = await authApi.login(email.trim(), password)
      setChallengeId(res.challenge_id) // memoria: nunca storage
      navigate('/otp', { replace: true })
    } catch (err) {
      setApiError(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <AuthCard title="Iniciar sesión" subtitle="Accede a tu cuenta de AgroTech-T">
        <form onSubmit={(e) => void submit(e)} noValidate>
          <AuthInput label="Correo electrónico" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={errors.email} placeholder="usuario@correo.com" />
          <PasswordInput label="Contraseña" name="password" value={password} onChange={(e) => setPassword(e.target.value)} error={errors.password} placeholder="••••••••" />
          {apiError && (
            <div className="mb-4">
              <Alert kind="error">{apiError}</Alert>
            </div>
          )}
          <Button loading={loading}>Iniciar sesión</Button>
        </form>
        <div className="mt-4 flex items-center justify-between text-sm">
          <Link to="/forgot-password" className="font-medium text-forest-700 hover:text-forest-600">
            ¿Olvidaste tu contraseña?
          </Link>
          <Link to="/register" className="font-medium text-forest-700 hover:text-forest-600">
            Crear una cuenta
          </Link>
        </div>
        <SocialLoginButtons />
      </AuthCard>
    </AuthLayout>
  )
}
