import { createContext, useCallback, useContext, useEffect, useState, type FormEvent } from 'react'
import { LockKeyhole, Network } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, ApiError, errorMessage, UNAUTHORIZED_EVENT } from '@/lib/api'

interface AuthState {
  username: string
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthGate')
  return ctx
}

/** Renders the app only for a signed-in user; otherwise the login screen. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null | undefined>(undefined) // undefined = checking

  useEffect(() => {
    api.auth
      .me()
      .then((me) => setUsername(me.username))
      .catch(() => setUsername(null))
    const onUnauthorized = () => setUsername(null)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const logout = useCallback(async () => {
    await api.auth.logout().catch(() => undefined)
    setUsername(null)
  }, [])

  if (username === undefined) return <div className="min-h-svh bg-surface" />
  if (username === null) return <LoginScreen onLogin={setUsername} />
  return <AuthContext.Provider value={{ username, logout }}>{children}</AuthContext.Provider>
}

function LoginScreen({ onLogin }: { onLogin: (username: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const me = await api.auth.login(username.trim(), password)
      onLogin(me.username)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : errorMessage(err))
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="dot-grid flex min-h-svh items-center justify-center bg-surface-lowest p-4">
      <form onSubmit={submit} className="panel-raised grid w-full max-w-sm gap-5 p-6">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-md bg-brand-strong/20 text-brand">
            <Network className="size-5" />
          </span>
          <div>
            <h1 className="text-headline-lg font-semibold text-on-surface">DevTeam AI</h1>
            <p className="font-mono text-label-sm text-outline">Multi-agent software platform</p>
          </div>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="login-username">Tên đăng nhập</Label>
          <Input id="login-username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="login-password">Mật khẩu</Label>
          <Input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </div>
        {error && <p className="rounded-md border border-danger/30 bg-danger/10 p-2 text-body-sm text-danger" role="alert">{error}</p>}
        <Button type="submit" disabled={busy || !username.trim() || !password}>
          <LockKeyhole /> {busy ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>
        <p className="text-center text-body-sm text-outline">Tài khoản quản trị được tạo từ ADMIN_USERNAME / ADMIN_PASSWORD trong file .env khi khởi động lần đầu</p>
      </form>
    </div>
  )
}
