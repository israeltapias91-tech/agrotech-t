import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import OtpInput from '../../components/auth/OtpInput'
import { isOtp } from '../../utils/validation'

type State = 'idle' | 'loading' | 'success' | 'error' | 'expired' | 'blocked'

const OTP_SECONDS = 10 * 60

function format(s: number) {
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/* Visual solamente: sin OTP real, sin backend. Temporizador e intentos locales. */
export default function OtpPage() {
  const [code, setCode] = useState('')
  const [state, setState] = useState<State>('idle')
  const [error, setError] = useState('')
  const [attemptsLeft, setAttemptsLeft] = useState(5)
  const [secondsLeft, setSecondsLeft] = useState(OTP_SECONDS)
  const [resending, setResending] = useState(false)

  useEffect(() => {
    if (secondsLeft <= 0) {
      setState((s) => (s === 'success' ? s : 'expired'))
      return
    }
    const t = window.setTimeout(() => setSecondsLeft((s) => s - 1), 1000)
    return () => window.clearTimeout(t)
  }, [secondsLeft])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isOtp(code)) {
      setError('Ingresa los 6 dígitos numéricos')
      return
    }
    setError('')
    setState('loading')
    window.setTimeout(() => setState('success'), 1000) // demo visual
  }

  const resend = () => {
    setResending(true)
    window.setTimeout(() => {
      setResending(false)
      setCode('')
      setSecondsLeft(OTP_SECONDS)
      setAttemptsLeft(5)
      setState('idle')
      setError('')
    }, 1000)
  }

  const preview = (s: State) => {
    if (s === 'error') {
      setAttemptsLeft(3)
      setError('Código incorrecto, te quedan 3 intentos. (Vista previa)')
    }
    if (s === 'blocked') setError('')
    if (s === 'expired') setSecondsLeft(0)
    setState(s)
  }

  return (
    <AuthLayout>
      <AuthCard title="Verificación en dos pasos" subtitle="Enviamos un código de 6 dígitos a tu correo">
        {state === 'success' ? (
          <Alert kind="success" title="Código verificado">
            Sesión creada correctamente. (Vista previa — continúa a la app en FASE 3)
          </Alert>
        ) : (
          <form onSubmit={submit} noValidate>
            <OtpInput value={code} onChange={(v) => setCode(v)} disabled={state === 'loading' || state === 'blocked' || state === 'expired'} />
            {error && (
              <p role="alert" className="mt-2 text-sm text-red-600">
                {error}
              </p>
            )}
            {state === 'expired' && (
              <div className="mt-3">
                <Alert kind="error" title="Código expirado">
                  El código venció. Pide uno nuevo con Reenviar. (Vista previa)
                </Alert>
              </div>
            )}
            {state === 'blocked' && (
              <div className="mt-3">
                <Alert kind="error" title="Demasiados intentos">
                  Alcanzaste el máximo de 5 intentos. Solicita un código nuevo. (Vista previa)
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
            <button type="button" onClick={resend} disabled={resending} className="mt-3 w-full text-sm font-medium text-forest-700 hover:text-forest-600 disabled:opacity-60">
              {resending ? 'Reenviando…' : 'Reenviar código'}
            </button>
          </form>
        )}
        <div className="mt-4 flex flex-wrap gap-3 text-xs">
          <span className="text-neutral-400">Vistas previas:</span>
          {(['idle', 'error', 'expired', 'blocked'] as State[]).map((s) => (
            <button key={s} type="button" onClick={() => preview(s)} className="text-forest-700 underline">
              {s}
            </button>
          ))}
        </div>
        <p className="mt-4 text-center text-sm text-neutral-500">
          <Link to="/login" className="font-medium text-forest-700 hover:text-forest-600">
            Volver al inicio de sesión
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  )
}
