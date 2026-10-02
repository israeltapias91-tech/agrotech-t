import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Button from '../components/ui/Button'

/* Pantalla temporal de sesión autenticada (FASE 3). El Dashboard real es posterior. */
export default function AppPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [leaving, setLeaving] = useState(false)

  const close = async () => {
    setLeaving(true)
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-forest-950 px-4 text-center">
      <p className="text-sm font-semibold tracking-widest text-forest-200">AGROTECH-T</p>
      <h1 className="text-3xl font-bold text-white">Bienvenido</h1>
      <p className="text-emerald-100">{user?.email}</p>
      <p className="rounded bg-forest-900 px-3 py-1 font-mono text-xs text-emerald-300">Sesión activa</p>
      <div className="mt-2 w-full max-w-xs">
        <Button type="button" onClick={() => void close()} loading={leaving}>
          Cerrar sesión
        </Button>
      </div>
    </main>
  )
}
