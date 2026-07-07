import { useState } from 'react'
import { useNavigate, Link, Navigate } from 'react-router-dom'
import { Loader2, UserPlus } from 'lucide-react'
import { useAuth } from '../lib/auth'

export default function Register() {
  const { register, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!loading && isAuthenticated) return <Navigate to="/" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setSubmitting(true)
    try {
      await register(email, password, name)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 mb-8 justify-center">
          <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center">
            <span className="text-fg-inverse font-bold">CK</span>
          </div>
          <span className="text-xl font-bold text-fg-primary">CareerKit</span>
        </div>

        <div className="bg-bg-secondary border border-border rounded-2xl p-6">
          <h1 className="text-lg font-bold text-fg-primary mb-1">Create your account</h1>
          <p className="text-sm text-fg-secondary mb-5">Your jobs, leads, and outreach stay private to you.</p>

          {error && (
            <div className="mb-4 px-3 py-2.5 rounded-lg bg-danger-bg border border-danger/20 text-sm text-danger">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-fg-secondary">Name</span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                className="px-3 py-2.5 rounded-lg bg-bg-primary border border-border text-sm text-fg-primary
                  focus:outline-none focus:border-accent transition-colors"
                placeholder="Your name"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-fg-secondary">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="px-3 py-2.5 rounded-lg bg-bg-primary border border-border text-sm text-fg-primary
                  focus:outline-none focus:border-accent transition-colors"
                placeholder="you@example.com"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-fg-secondary">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="px-3 py-2.5 rounded-lg bg-bg-primary border border-border text-sm text-fg-primary
                  focus:outline-none focus:border-accent transition-colors"
                placeholder="At least 6 characters"
              />
            </label>
            <button
              type="submit"
              disabled={submitting}
              className="mt-2 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent
                hover:bg-accent-dim text-fg-inverse text-sm font-semibold transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <UserPlus size={16} />}
              {submitting ? 'Creating account…' : 'Sign up'}
            </button>
          </form>

          <p className="mt-5 text-sm text-fg-secondary text-center">
            Already have an account?{' '}
            <Link to="/login" className="text-accent hover:underline font-medium">Log in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
