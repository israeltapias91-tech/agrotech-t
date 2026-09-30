import { useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import { isEmail } from '../../utils/validation'

/* Visual solamente: respuesta siempre neutra, sin revelar si existe. */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'sent'>('idle')

  const submit = (e: React.FormEvent) => {
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
    window.setTimeout(() => setStatus('sent'), 1000) // demo visual
  }

  return (
    <AuthLayout>
      <AuthCard title="Recuperar contraseña" subtitle="Te enviaremos instrucciones para restablecerla">
        {status === 'sent' ? (
          <Alert kind="success" title="Revisa tu correo">
            Si el correo existe, recibirás instrucciones para restablecer tu contraseña. (Vista previa)
          </Alert>
        ) : (
          <form onSubmit={submit} noValidate>
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
