import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'
import {
  Monitor, LogIn, Square, Loader2, WifiOff, PowerOff, RefreshCw,
} from 'lucide-react'

const POLL_INTERVAL = 5000

// ── Status dot ────────────────────────────────────────────────────────────────

function StatusDot({ variant }) {
  // variant: 'stopped' | 'starting' | 'ready' | 'applying' | 'session-expired'
  const cls = {
    stopped:         'bg-danger',
    starting:        'bg-warning animate-pulse',
    ready:           'bg-success',
    applying:        'bg-accent animate-pulse',
    'session-expired': 'bg-warning',
  }[variant] ?? 'bg-fg-muted'

  const title = {
    stopped:         'Browser stopped',
    starting:        'Browser starting',
    ready:           'Browser running',
    applying:        'Auto-apply running',
    'session-expired': 'Session expired',
  }[variant] ?? 'Unknown'

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${cls}`}
      title={title}
    />
  )
}

// ── Disconnect inline confirmation ────────────────────────────────────────────

function DisconnectButton({ onConfirm, loading }) {
  const [confirming, setConfirming] = useState(false)

  if (confirming) {
    return (
      <div className="flex items-center gap-1 text-xs">
        <span className="text-fg-secondary mr-1">Disconnect?</span>
        <button
          onClick={() => { onConfirm(); setConfirming(false) }}
          disabled={loading}
          className="px-2 py-1 rounded-md bg-danger-bg border border-danger/30 text-danger
            hover:bg-danger/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Yes
        </button>
        <button
          onClick={() => setConfirming(false)}
          className="px-2 py-1 rounded-md bg-bg-tertiary border border-border text-fg-secondary
            hover:text-fg-primary hover:border-border-light transition-colors"
        >
          No
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      disabled={loading}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-tertiary border border-border
        text-xs text-fg-secondary hover:text-danger hover:border-danger/30 transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <PowerOff size={12} />
      Disconnect
    </button>
  )
}

// ─── BrowserBar ───────────────────────────────────────────────────────────────

export default function BrowserBar() {
  const [status, setStatus] = useState(null)
  const [phase, setPhase] = useState('stopped') // stopped | starting | ready | applying | session-expired
  const [apiError, setApiError] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.getBrowserStatus()
      setStatus(data)
      setApiError(false)

      if (!data.running) {
        setPhase('stopped')
      } else if (data.status === 'starting') {
        setPhase('starting')
      } else if (!data.logged_in) {
        setPhase('session-expired')
      } else if (data.apply_log !== undefined && data.current_job) {
        setPhase('applying')
      } else {
        setPhase('ready')
      }
    } catch {
      setApiError(true)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [fetchStatus])

  const handleStartBrowser = async () => {
    setActionLoading(true)
    setPhase('starting')
    try {
      await api.startBrowser()
      await fetchStatus()
    } catch {
      setPhase('stopped')
    } finally {
      setActionLoading(false)
    }
  }

  const handleOpenLogin = async () => {
    setActionLoading(true)
    try {
      await api.openLogin()
    } catch {}
    finally {
      setActionLoading(false)
    }
  }

  const handleStopBrowser = async () => {
    setActionLoading(true)
    try {
      await api.stopBrowser()
      await fetchStatus()
    } catch {}
    finally {
      setActionLoading(false)
    }
  }

  const loggedIn = status?.logged_in ?? false
  const currentJob = status?.current_job ?? null
  const isApplying = phase === 'applying'

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="h-10 w-full bg-bg-secondary border-b border-border flex items-center px-4 gap-4 shrink-0">

      {/* LEFT — status indicator */}
      <div className="flex items-center gap-2 min-w-0">
        {apiError ? (
          <>
            <WifiOff size={13} className="text-fg-muted shrink-0" />
            <span className="text-xs text-fg-muted truncate">Backend unreachable</span>
          </>
        ) : (
          <>
            <StatusDot variant={phase} />
            <Monitor size={13} className="text-fg-muted shrink-0" />
            <span className="text-xs font-medium truncate">
              {phase === 'stopped' && (
                <span className="text-fg-muted">Browser stopped</span>
              )}
              {phase === 'starting' && (
                <span className="text-warning">Starting browser…</span>
              )}
              {phase === 'session-expired' && (
                <span className="text-warning">Session expired</span>
              )}
              {phase === 'applying' && (
                <span className="text-accent">Auto-apply running</span>
              )}
              {phase === 'ready' && (
                <span className="text-success">Browser ready</span>
              )}
            </span>
          </>
        )}
      </div>

      {/* CENTER — current job when applying */}
      <div className="flex-1 flex items-center justify-center min-w-0">
        {isApplying && currentJob && (
          <div className="flex items-center gap-2 px-3 py-0.5 rounded-md bg-accent-bg border border-accent/20 max-w-sm truncate">
            <Loader2 size={12} className="text-accent animate-spin shrink-0" />
            <span className="text-xs text-fg-primary font-medium truncate">
              Applying: {currentJob}
            </span>
          </div>
        )}
      </div>

      {/* RIGHT — actions */}
      <div className="flex items-center gap-2 shrink-0 ml-auto">

        {/* Backend unreachable → Retry */}
        {apiError && (
          <button
            onClick={fetchStatus}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-tertiary border border-border
              text-xs text-fg-secondary hover:text-fg-primary hover:border-border-light transition-colors"
          >
            <RefreshCw size={12} />
            Retry
          </button>
        )}

        {/* Stopped → Start Browser */}
        {!apiError && phase === 'stopped' && (
          <button
            onClick={handleStartBrowser}
            disabled={actionLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-tertiary border border-border
              text-xs text-fg-secondary hover:text-fg-primary hover:border-border-light transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Monitor size={12} />
            )}
            Start Browser
          </button>
        )}

        {/* Starting → spinner indicator */}
        {!apiError && phase === 'starting' && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-tertiary border border-border text-xs text-warning">
            <Loader2 size={12} className="animate-spin" />
            Starting…
          </div>
        )}

        {/* Session expired (running + not logged in) → Reconnect */}
        {!apiError && phase === 'session-expired' && (
          <button
            onClick={handleOpenLogin}
            disabled={actionLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-accent-bg border border-accent/30
              text-xs text-accent hover:bg-accent/20 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <LogIn size={12} />
            )}
            Reconnect
          </button>
        )}

        {/* Auto-apply running → Stop */}
        {!apiError && isApplying && (
          <button
            onClick={handleStopBrowser}
            disabled={actionLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-danger-bg border border-danger/30
              text-xs text-danger hover:bg-danger/20 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Square size={12} className="fill-current" />
            )}
            Stop
          </button>
        )}

        {/* Fully connected + not applying → Disconnect */}
        {!apiError && phase === 'ready' && loggedIn && !isApplying && (
          <DisconnectButton onConfirm={handleStopBrowser} loading={actionLoading} />
        )}

      </div>
    </div>
  )
}
