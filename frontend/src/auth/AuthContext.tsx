import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type SessionInfo } from '../api/auth'
import { ApiError } from '../api/client'

/* Sesión mínima global: la verdad vive en Django (GET session/).
   challenge_id del OTP vive aquí en memoria: nunca en storage. */

type AuthState = {
  user: SessionInfo | null
  checking: boolean
  challengeId: string | null
  refresh: () => Promise<void>
  setChallengeId: (id: string | null) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionInfo | null>(null)
  const [checking, setChecking] = useState(true)
  const [challengeId, setChallengeId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      await authApi.csrf()
      const info = await authApi.session()
      setUser(info)
    } catch (e) {
      if (e instanceof ApiError && (e.status === 403 || e.status === 401)) setUser(null)
      else setUser(null)
    } finally {
      setChecking(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      /* aunque falle, limpiamos estado local */
    } finally {
      setUser(null)
      setChallengeId(null)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <AuthContext.Provider value={{ user, checking, challengeId, refresh, setChallengeId, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth fuera de AuthProvider')
  return ctx
}
