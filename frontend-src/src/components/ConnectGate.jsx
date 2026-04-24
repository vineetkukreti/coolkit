import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../lib/api'
import {
  Globe, WifiOff, CheckCircle, AlertTriangle, Loader2,
  ShieldCheck, RefreshCw, Power,
} from 'lucide-react'

const POLL_INTERVAL = 3000

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useLinkedInStatus() {
  const [running, setRunning] = useState(false)
  const [logged_in, setLoggedIn] = useState(false)
  const [checking, setChecking] = useState(true)
  const [unreachable, setUnreachable] = useState(false)
  const intervalRef = useRef(null)

  const check = useCallback(async () => {
    try {
      const data = await api.getBrowserStatus()
      setRunning(data.running)
      setLoggedIn(data.logged_in)
      setUnreachable(false)
      setChecking(false)
    } catch {
      // Network error — backend unreachable
      setUnreachable(true)
      setRunning(false)
      setLoggedIn(false)
      setChecking(false)
    }
  }, [])

  const refresh = useCallback(() => {
    setChecking(true)
    check()
  }, [check])

  useEffect(() => {
    check()
    intervalRef.current = setInterval(check, POLL_INTERVAL)
    return () => clearInterval(intervalRef.current)
  }, [check])

  return { running, logged_in, checking, unreachable, refresh }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StepRow({ num, label, desc, active, done }) {
  return (
    <div
      className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
        done
          ? 'bg-success-bg border-success/20'
          : active
          ? 'bg-bg-tertiary border-border-light'
          : 'bg-bg-primary border-border opacity-40'
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
          done
            ? 'bg-success text-fg-inverse'
            : active
            ? 'bg-accent text-fg-inverse'
            : 'bg-bg-tertiary text-fg-muted border border-border'
        }`}
      >
        {done ? <CheckCircle size={14} /> : num}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${done ? 'text-success' : 'text-fg-primary'}`}>
          {label}
        </p>
        <p className="text-xs text-fg-muted mt-0.5">{desc}</p>
      </div>
    </div>
  )
}

function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-danger-bg border border-danger/20">
      <AlertTriangle size={15} className="text-danger shrink-0 mt-0.5" />
      <p className="text-xs text-danger leading-relaxed">{message}</p>
    </div>
  )
}

// ─── ConnectGate ──────────────────────────────────────────────────────────────

export default function ConnectGate({ wasConnected = false }) {
  // phase: 'checking' | 'unreachable' | 'stopped' | 'starting' | 'ready' | 'connected'
  const [phase, setPhase] = useState('checking')
  const [error, setError] = useState('')
  const [verifyFailCount, setVerifyFailCount] = useState(0)

  // Timeout hints for the 'starting' phase
  const [startElapsed, setStartElapsed] = useState(0)
  const startTimerRef = useRef(null)

  // Poll when in 'ready' phase
  const pollRef = useRef(null)

  // ── Initial check ──────────────────────────────────────────────────────────
  const doInitialCheck = useCallback(async () => {
    setPhase('checking')
    try {
      const data = await api.getBrowserStatus()
      if (data.logged_in) {
        setPhase('connected')
      } else if (data.running) {
        setPhase('ready')
      } else {
        setPhase('stopped')
      }
    } catch {
      setPhase('unreachable')
    }
  }, [])

  useEffect(() => {
    doInitialCheck()
  }, [doInitialCheck])

  // ── Poll while in 'ready' phase ────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'ready') {
      clearInterval(pollRef.current)
      return
    }

    pollRef.current = setInterval(async () => {
      try {
        const data = await api.getBrowserStatus()
        if (data.logged_in) {
          setPhase('connected')
        } else if (!data.running) {
          // Browser stopped unexpectedly while we were waiting
          setError('Browser stopped unexpectedly. Please launch it again.')
          setPhase('stopped')
        }
      } catch {
        // Transient network blip — don't change phase yet
      }
    }, POLL_INTERVAL)

    return () => clearInterval(pollRef.current)
  }, [phase])

  // ── Starting phase timer ───────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'starting') {
      clearInterval(startTimerRef.current)
      setStartElapsed(0)
      return
    }

    setStartElapsed(0)
    startTimerRef.current = setInterval(() => {
      setStartElapsed((prev) => prev + 1)
    }, 1000)

    return () => clearInterval(startTimerRef.current)
  }, [phase])

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleLaunch = async () => {
    setError('')
    setPhase('starting')
    try {
      await api.startBrowser()
      // After start, check status — cookies might restore the session immediately
      const data = await api.getBrowserStatus()
      if (data.logged_in) {
        setPhase('connected')
      } else if (data.running) {
        setPhase('ready')
      } else {
        setPhase('ready') // still optimistic — let the poll confirm
      }
    } catch (e) {
      setError(e.message || 'Failed to launch browser.')
      setPhase('stopped')
    }
  }

  const handleVerify = async () => {
    setError('')
    try {
      const res = await api.checkLogin()
      if (res.logged_in) {
        setPhase('connected')
        setVerifyFailCount(0)
      } else {
        const newCount = verifyFailCount + 1
        setVerifyFailCount(newCount)
        if (newCount >= 3) {
          setError('Not logged in yet.')
        } else {
          setError('Not logged in yet. Please complete the login in the Chrome window, then click Verify again.')
        }
      }
    } catch {
      setError('Could not verify login status.')
    }
  }

  const handleOpenLogin = async () => {
    try {
      await api.openLogin()
    } catch {
      // Silently ignore — user can see the window
    }
  }

  const handleRetryUnreachable = () => {
    doInitialCheck()
  }

  const handleResetToStopped = () => {
    setPhase('stopped')
    setError('')
  }

  // ── State: connected (parent should have unmounted us, but guard anyway) ───
  if (phase === 'connected') return null

  // ── State: initial checking spinner ───────────────────────────────────────
  if (phase === 'checking') {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg-primary">
        <Loader2 size={32} className="text-accent animate-spin" />
      </div>
    )
  }

  // ── State 1: Backend unreachable ───────────────────────────────────────────
  if (phase === 'unreachable') {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg-primary p-8">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 bg-danger-bg rounded-2xl flex items-center justify-center mx-auto mb-5">
            <WifiOff size={32} className="text-danger" />
          </div>
          <h1 className="text-xl font-bold text-fg-primary mb-2">Cannot reach server</h1>
          <p className="text-sm text-fg-secondary mb-8 leading-relaxed">
            Make sure the backend is running at{' '}
            <code className="font-mono text-accent bg-accent-bg px-1.5 py-0.5 rounded text-xs">
              localhost:8000
            </code>
          </p>
          <button
            onClick={handleRetryUnreachable}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-dim
              text-fg-inverse font-semibold text-sm rounded-xl transition-colors"
          >
            <RefreshCw size={15} />
            Retry
          </button>
        </div>
      </div>
    )
  }

  // ── State 5: Session lost (was connected before, now stopped) ─────────────
  if (phase === 'stopped' && wasConnected) {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg-primary p-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-warning-bg rounded-2xl flex items-center justify-center mx-auto mb-5">
              <Power size={32} className="text-warning" />
            </div>
            <h1 className="text-2xl font-bold text-fg-primary mb-2">Session Lost</h1>
            <p className="text-sm text-fg-secondary max-w-sm mx-auto leading-relaxed">
              Your browser session ended. Your saved cookies may restore the session automatically.
            </p>
          </div>

          <div className="space-y-3">
            {phase === 'starting' ? (
              <button
                disabled
                className="w-full flex items-center justify-center gap-2 py-3.5 bg-accent/60
                  text-fg-inverse font-semibold text-sm rounded-xl cursor-not-allowed"
              >
                <Loader2 size={16} className="animate-spin" />
                Relaunching browser…
              </button>
            ) : (
              <button
                onClick={handleLaunch}
                className="w-full flex items-center justify-center gap-2 py-3.5 bg-accent hover:bg-accent-dim
                  text-fg-inverse font-semibold text-sm rounded-xl transition-colors"
              >
                <RefreshCw size={16} />
                Relaunch Browser
              </button>
            )}
          </div>

          {error && (
            <div className="mt-4">
              <ErrorBox message={error} />
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── States 2–4: Normal first-time flow ────────────────────────────────────
  const step1Done = phase === 'ready'
  const step2Active = phase === 'ready'
  const isStarting = phase === 'starting'

  const showSlowHint = isStarting && startElapsed >= 15
  const showTimeoutRetry = isStarting && startElapsed >= 45

  return (
    <div className="flex-1 flex items-center justify-center bg-bg-primary p-8">
      <div className="w-full max-w-lg">

        {/* Header */}
        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-accent-bg rounded-2xl flex items-center justify-center mx-auto mb-5">
            <Globe size={32} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-fg-primary mb-2">Connect to LinkedIn</h1>
          <p className="text-sm text-fg-secondary max-w-sm mx-auto leading-relaxed">
            JobAutomate needs a browser session to interact with LinkedIn.
            Connect your account to get started.
          </p>
        </div>

        {/* Steps */}
        <div className="bg-bg-secondary border border-border rounded-2xl p-6 space-y-4 mb-6">
          <StepRow
            num={1}
            label="Launch Browser & Open LinkedIn"
            desc="Opens a Chrome window with the LinkedIn login page"
            active={phase === 'stopped' || phase === 'starting'}
            done={step1Done}
          />
          <StepRow
            num={2}
            label="Login & Verify"
            desc="Sign into LinkedIn in the browser, then verify here"
            active={step2Active}
            done={false}
          />
        </div>

        {/* Status pill — shown only in ready phase */}
        {phase === 'ready' && (
          <div className="flex items-center justify-center mb-5">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-warning-bg border border-warning/30 text-xs font-medium text-warning">
              <span className="w-1.5 h-1.5 rounded-full bg-warning" />
              Browser ready — awaiting login
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-3">

          {/* State 2: Stopped — big launch button */}
          {phase === 'stopped' && (
            <button
              onClick={handleLaunch}
              className="w-full flex items-center justify-center gap-2 py-3.5 bg-accent hover:bg-accent-dim
                text-fg-inverse font-semibold text-sm rounded-xl transition-colors"
            >
              <Globe size={16} />
              Launch Browser & Open LinkedIn
            </button>
          )}

          {/* State 3: Starting — disabled with spinner */}
          {isStarting && (
            <button
              disabled
              className="w-full flex items-center justify-center gap-2 py-3.5 bg-accent/60
                text-fg-inverse font-semibold text-sm rounded-xl cursor-not-allowed"
            >
              <Loader2 size={16} className="animate-spin" />
              Launching browser…
            </button>
          )}

          {/* State 3: Slow hint at 15s */}
          {showSlowHint && !showTimeoutRetry && (
            <p className="text-xs text-fg-muted text-center">
              This is taking longer than usual…
            </p>
          )}

          {/* State 3: Timeout retry at 45s */}
          {showTimeoutRetry && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-xs text-warning text-center">
                Still waiting. Something may have gone wrong.
              </p>
              <button
                onClick={handleResetToStopped}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-bg-tertiary border border-border
                  text-xs text-fg-secondary hover:text-fg-primary hover:border-border-light transition-colors"
              >
                <RefreshCw size={12} />
                Try Again
              </button>
            </div>
          )}

          {/* State 4: Ready — verify button */}
          {phase === 'ready' && (
            <>
              <button
                onClick={handleVerify}
                className="w-full flex items-center justify-center gap-2 py-3.5 bg-accent hover:bg-accent-dim
                  text-fg-inverse font-semibold text-sm rounded-xl transition-colors"
              >
                <ShieldCheck size={16} />
                Verify Connection
              </button>

              <button
                onClick={handleOpenLogin}
                className="w-full text-center text-xs text-fg-muted hover:text-fg-secondary transition-colors py-1"
              >
                Open LinkedIn login page again
              </button>
            </>
          )}
        </div>

        {/* Verify failure hint after 3 fails */}
        {verifyFailCount >= 3 && phase === 'ready' && (
          <div className="mt-4 flex items-start gap-2.5 p-3.5 rounded-xl bg-warning-bg border border-warning/20">
            <AlertTriangle size={15} className="text-warning shrink-0 mt-0.5" />
            <p className="text-xs text-warning leading-relaxed">
              Make sure you completed the login in Chrome and LinkedIn shows your feed,
              not just the login form.
            </p>
          </div>
        )}

        {/* Error */}
        {error && verifyFailCount < 3 && (
          <div className="mt-4">
            <ErrorBox message={error} />
          </div>
        )}

        {/* Footer hint */}
        <p className="text-xs text-fg-muted text-center mt-6 leading-relaxed">
          Click "Launch Browser" — a Chrome window will open with the LinkedIn login page.
          Sign in normally, then come back here and click "Verify Connection".
          Your session is saved for future use.
        </p>

        {/* ToS disclaimer */}
        <div className="mt-4 flex items-start gap-2.5 p-3 rounded-xl bg-warning-bg/50 border border-warning/10">
          <AlertTriangle size={13} className="text-warning shrink-0 mt-0.5" />
          <p className="text-xs text-fg-muted leading-relaxed">
            Automating LinkedIn may violate their Terms of Service. Use at your own risk with conservative limits.
          </p>
        </div>

      </div>
    </div>
  )
}
