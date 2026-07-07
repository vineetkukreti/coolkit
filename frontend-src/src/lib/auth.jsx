import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, tokenStore } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount, if we have a token, validate it and load the user.
  useEffect(() => {
    let cancelled = false
    const token = tokenStore.get()
    if (!token) {
      setLoading(false)
      return
    }
    api.me()
      .then((res) => { if (!cancelled) setUser(res.user) })
      .catch(() => { if (!cancelled) { tokenStore.clear(); setUser(null) } })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await api.login({ email, password })
    tokenStore.set(res.token)
    setUser(res.user)
    return res.user
  }, [])

  const register = useCallback(async (email, password, name) => {
    const res = await api.register({ email, password, name })
    tokenStore.set(res.token)
    setUser(res.user)
    return res.user
  }, [])

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  const value = { user, loading, isAuthenticated: !!user, login, register, logout }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
