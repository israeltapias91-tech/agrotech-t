import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { userMessage } from '../../api/errors'
import { useAuth } from '../../auth/AuthContext'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import OtpInput from '../../components/auth/OtpInput'
import { isOtp } from '../../utils/validation'

const OTP_SECONDS = 10 * 60

function format(s: number) {
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

type State = 'idle' | 'loading' | 'expired' | 'blocked'

/* challenge_id + code (nunca email+code). Sin challenge se resuelve por sesión:
   con usuario autenticado → /app, sin usuario → /login. */
export default function OtpPage() {
  const navigate = useNavigate()
  const { challengeId, setChallengeId, refresh, user, checking } = useAuth()
  const [code, setCode] = useState('')
  const [state, setState] = useState<State>('idle')
  const [error, setError] = useState('')
  const [attemptsLeft, setAttemptsLeft] = useState(5)
  const [secondsLeft, setSecondsLeft] = useState(OTP_SECONDS)
  const [resending, setResending] = useState(false)

  useEffect(() => {
    if (checking || challengeId) return
    navigate(user ? '/app' : '/login', { replace: true })
  }, [challengeId, checking, user, navigate])

  useEffect(() => {
    if (secondsLeft <= 0) {
      setState('expired')
      return
    }
    const t = window.setTimeout(() => setSecondsLeft((s) => s - 1), 1000)
    return () => window.clearTimeout(t)
  }, [secondsLeft])

  if (!challengeId) return null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (state === 'loading') return
    if (!isOtp(code)) {
      setError('Ingresa los 6 dígitos numéricos')
      return
    }
    setError('')
    setState('loading')
    try {
      await authApi.verifyOtp(challengeId, code)
      const sessionUser = await refresh()
      if (sessionUser) {
        setChallengeId(null)
        navigate('/app', { replace: true })
      } else {
        setState('idle')
        setError('No se pudo confirmar la sesión. Intenta nuevamente.')
      }
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'otp_attempts_exceeded' || err.status === 429)) {
        setState('blocked')
        setAttemptsLeft(0)
        setError(userMessage(err.code === 'otp_attempts_exceeded' ? err.code : 'rate_limited', err.detail))
      } else if (err instanceof ApiError && err.code === 'otp_expired') {
        setState('expired')
      } else {
        setState('idle')
        if (err instanceof ApiError) {
          const left = err.detail.match(/quedan (\d+)/)?.[1]
          if (left !== undefined) setAttemptsLeft(Number(left))
        }
        setError(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
      }
    }
  }

  const resend = async () => {
    setResending(true)
    setError('')
    try {
      const res = await authApi.resendOtp(challengeId)
      setChallengeId(res.challenge_id) // reemplazar: el anterior murió
      setCode('')
      setSecondsLeft(OTP_SECONDS)
      setAttemptsLeft(5)
      setState('idle')
    } catch (err) {
      setError(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthLayout>
      <AuthCard title="Verificación en dos pasos" subtitle="Enviamos un código de 6 dígitos a tu correo">
        <form onSubmit={(e) => void submit(e)} noValidate>
          <OtpInput value={code} onChange={(v) => setCode(v)} disabled={state === 'loading' || state === 'blocked' || state === 'expired'} />
          {error && (
            <p role="alert" className="mt-2 text-sm text-red-600">
              {error}
            </p>
          )}
          {state === 'expired' && (
            <div className="mt-3">
              <Alert kind="error" title="Código expirado">
                El código venció. Pide uno nuevo con Reenviar.
              </Alert>
            </div>
          )}
          {state === 'blocked' && (
            <div className="mt-3">
              <Alert kind="error" title="Demasiados intentos">
                Alcanzaste el máximo de 5 intentos. Solicita un código nuevo.
              </Alert>
            </div>
          )}
          <div className="mt-3 flex items-center justify-between text-sm text-neutral-500">
            <span>
              Vence en <strong className="font-mono text-neutral-700">{format(secondsLeft)}</strong>
            </span>
            <span>
              Intentos restantes: <strong className="font-mono text-neutral-700">{attemptsLeft}/5</strong>
            </span>
          </div>
          <div className="mt-4">
            <Button loading={state === 'loading'}>Verificar código</Button>
          </div>
          <button type="button" onClick={() => void resend()} disabled={resending} className="mt-3 w-full text-sm font-medium text-forest-700 hover:text-forest-600 disabled:opacity-60">
            {resending ? 'Reenviando…' : 'Reenviar código'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-neutral-500">
          <Link to="/login" className="font-medium text-forest-700 hover:text-forest-600">
            Volver al inicio de sesión
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  )
}
