import { Navigate } from 'react-router-dom'
import Spinner from '../components/ui/Spinner'
import { useAuth } from '../auth/AuthContext'

/* Sin parpadeo: mientras checking, spinner. Sin sesión → /login. */
export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, checking } = useAuth()
  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-sand-100">
        <Spinner label="Comprobando sesión…" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}
