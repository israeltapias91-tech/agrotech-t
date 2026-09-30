import { useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../../components/ui/Alert'
import AuthCard from '../../components/auth/AuthCard'
import AuthInput from '../../components/auth/AuthInput'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/ui/Button'
import Spinner from '../../components/ui/Spinner'

type State = 'sent' | 'resending' | 'error' | 'verified'

/* Visual solamente: estados enviados/reenvío/error/verificado sin backend. */
const copy: Record<State, { kind: 'info' | 'success' | 'error'; title: string; text: string }> = {
  sent: { kind: 'info', title: 'Revisa tu bandeja', text: 'Te enviamos un enlace de verificación. (Vista previa)' },
  resending: { kind: 'info', title: 'Reenviando…', text: 'Estamos generando un nuevo enlace. (Vista previa)' },
  error: { kind: 'error', title: 'No pudimos verificar', text: 'El enlace expiró o ya fue utilizado. Pide uno nuevo. (Vista previa)' },
  verified: { kind: 'success', title: 'Correo verificado', text: 'Tu cuenta quedó habilitada para iniciar sesión. (Vista previa)' },
}

export default function VerifyEmailPage() {
  const [email] = useState('usuario@correo.com')
  const [state, setState] = useState<State>('sent')
  const [newEmail, setNewEmail] = useState('')
  const [changing, setChanging] = useState(false)

  const resend = () => {
    setState('resending')
    window.setTimeout(() => setState('sent'), 1200)
  }

  const current = copy[state]

  return (
    <AuthLayout>
      <AuthCard title="Verifica tu correo electrónico" subtitle={`Enviamos un enlace a ${email}`}>
        <div className="mb-4">
          {state === 'resending' ? <Spinner label="Reenviando enlace…" /> : <Alert kind={current.kind} title={current.title}>{current.text}</Alert>}
        </div>
        <div className="flex flex-col gap-2">
          <Button type="button" onClick={resend}>
            Reenviar enlace
          </Button>
          <button type="button" onClick={() => setChanging((v) => !v)} className="text-sm font-medium text-forest-700 hover:text-forest-600">
            Cambiar correo de destino
          </button>
        </div>
        {changing && (
          <form
            className="mt-4 rounded-lg border border-neutral-200 p-3"
            onSubmit={(e) => {
              e.preventDefault()
              setChanging(false)
            }}
          >
            <AuthInput label="Nuevo correo" name="newEmail" type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="nuevo@correo.com" />
            <Button>Guardar y reenviar</Button>
          </form>
        )}
        <div className="mt-4 flex gap-3 text-xs">
          <span className="text-neutral-400">Vistas previas:</span>
          {(['sent', 'error', 'verified'] as State[]).map((s) => (
            <button key={s} type="button" onClick={() => setState(s)} className="text-forest-700 underline">
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
