import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { userMessage } from '../../api/errors'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import Spinner from '../../components/ui/Spinner'

type State = 'working' | 'verified' | 'error'

/* Token desde la URL (?token=). Auto-verifica al montar. */
export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const [state, setState] = useState<State>('working')
  const [detail, setDetail] = useState('')
  const [email, setEmail] = useState('')
  const [resendState, setResendState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [resendDetail, setResendDetail] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [changing, setChanging] = useState(false)
  const [changeState, setChangeState] = useState<'idle' | 'sending' | 'done' | 'error'>('idle')
  const [changeDetail, setChangeDetail] = useState('')

  useEffect(() => {
    const token = params.get('token') ?? ''
    if (!token) {
      setState('error')
      setDetail('Falta el token de verificación. Abre el enlace de tu correo.')
      return
    }
    let alive = true
    authApi
      .verifyEmail(token)
      .then(() => {
        if (alive) setState('verified')
      })
      .catch((err: unknown) => {
        if (!alive) return
        setState('error')
        setDetail(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
      })
    return () => {
      alive = false
    }
  }, [params])

  const resend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setResendState('sending')
    setResendDetail('')
    try {
      await authApi.resendEmail(email.trim())
      setResendState('sent')
    } catch (err) {
      setResendState('error')
      setResendDetail(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
    }
  }

  return (
    <AuthLayout>
      <AuthCard title="Verifica tu correo electrónico" subtitle="Confirmamos que controlas tu buzón">
        {state === 'working' && <Spinner label="Verificando enlace…" />}
        {state === 'verified' && (
          <Alert kind="success" title="Correo verificado">
            Tu cuenta quedó habilitada para iniciar sesión.
          </Alert>
        )}
        {state === 'error' && (
          <Alert kind="error" title="No pudimos verificar">
            {detail}
          </Alert>
        )}
        {(state === 'verified' || state === 'error') && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium text-neutral-700">¿No te llegó o venció el enlace?</p>
            <form onSubmit={(e) => void resend(e)} className="flex flex-col gap-2">
              <AuthInput label="Correo de la cuenta" name="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="usuario@correo.com" />
              <Button loading={resendState === 'sending'}>Reenviar enlace</Button>
            </form>
            {resendState === 'sent' && (
              <p className="mt-2 text-sm text-forest-700">Si la cuenta existe, reenviamos el correo.</p>
            )}
            {resendState === 'error' && (
              <p role="alert" className="mt-2 text-sm text-red-600">
                {resendDetail}
              </p>
            )}
            <button type="button" onClick={() => setChanging((v) => !v)} className="mt-3 text-sm font-medium text-forest-700 hover:text-forest-600">
              Cambiar correo de destino
            </button>
            {changing && (
              <form
                className="mt-4 rounded-lg border border-neutral-200 p-3"
                onSubmit={(e) => {
                  e.preventDefault()
                  const token = params.get('token') ?? ''
                  if (!token || !newEmail.trim()) {
                    setChangeState('error')
                    setChangeDetail('Necesitas el enlace vigente y el nuevo correo.')
                    return
                  }
                  setChangeState('sending')
                  setChangeDetail('')
                  authApi
                    .changeEmail(token, newEmail.trim())
                    .then(() => setChangeState('done'))
                    .catch((err: unknown) => {
                      setChangeState('error')
                      setChangeDetail(err instanceof ApiError ? userMessage(err.code, err.detail) : 'Ocurrió un error inesperado.')
                    })
                }}
              >
                <AuthInput label="Nuevo correo" name="newEmail" type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="nuevo@correo.com" />
                <Button loading={changeState === 'sending'}>Guardar y reenviar</Button>
                {changeState === 'done' && (
                  <p className="mt-2 text-sm text-forest-700">Correo actualizado, revisa tu nuevo buzón.</p>
                )}
                {changeState === 'error' && (
                  <p role="alert" className="mt-2 text-sm text-red-600">
                    {changeDetail}
                  </p>
                )}
              </form>
            )}
            <p className="mt-4 text-center text-sm">
              <Link to="/login" className="font-medium text-forest-700 hover:text-forest-600">
                {state === 'verified' ? 'Ir al inicio de sesión' : 'Volver al inicio de sesión'}
              </Link>
            </p>
          </div>
        )}
        {state === 'working' && (
          <p className="mt-4 text-center text-sm text-neutral-500">
            <Link to="/login" className="font-medium text-forest-700 hover:text-forest-600">
              Volver al inicio de sesión
            </Link>
          </p>
        )}
      </AuthCard>
    </AuthLayout>
  )
}
