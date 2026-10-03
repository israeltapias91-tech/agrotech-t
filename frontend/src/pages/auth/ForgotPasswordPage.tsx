import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import { isEmail } from '../../utils/validation'

/* Respuesta siempre neutra: nunca revela si el correo existe. */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'sent'>('idle')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('El correo es requerido')
      return
    }
    if (!isEmail(email)) {
      setError('Formato de correo inválido')
      return
    }
    setError('')
    setStatus('loading')
    try {
      await authApi.requestPasswordReset(email.trim())
      setStatus('sent')
    } catch (err) {
      setStatus('idle')
      setError(err instanceof ApiError ? 'Ocurrió un error inesperado.' : 'Ocurrió un error inesperado.')
    }
  }

  return (
    <AuthLayout>
      <AuthCard title="Recuperar contraseña" subtitle="Te enviaremos instrucciones para restablecerla">
        {status === 'sent' ? (
          <Alert kind="success" title="Revisa tu correo">
            Si el correo existe, recibirás instrucciones para restablecer tu contraseña.
          </Alert>
        ) : (
          <form onSubmit={(e) => void submit(e)} noValidate>
            <AuthInput label="Correo electrónico" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={error} placeholder="usuario@correo.com" />
            <Button loading={status === 'loading'}>Enviar enlace</Button>
          </form>
        )}
        <p className="mt-4 text-center text-sm text-neutral-500">
          <Link to="/login" className="font-medium text-forest-700 hover:text-forest-600">
            Volver al inicio de sesión
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  )
}
