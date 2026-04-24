import { useState, useEffect, useRef } from 'react'
import { Play, Square, Zap, Target, CheckCircle, XCircle, Clock, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'

export default function AutoApply() {
  const [status, setStatus] = useState(null)
  const [quota, setQuota] = useState(null)
  const [maxApps, setMaxApps] = useState(500)
  const [loading, setLoading] = useState(false)
  const logRef = useRef(null)

  const fetchStatus = async () => {
    try {
      const [statusRes, quotaRes] = await Promise.all([
        api.getAutoApplyStatus(),
        api.getAutoApplyQuota(),
      ])
      setStatus(statusRes)
      setQuota(quotaRes)
    } catch (e) {
      console.error('Status fetch error:', e)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [status?.log])

  const handleStart = async () => {
    setLoading(true)
    try {
      await api.startAutoApply({ max_applications: maxApps })
      setTimeout(fetchStatus, 1000)
    } catch (e) {
      console.error('Start error:', e)
    }
    setLoading(false)
  }

  const handleStop = async () => {
    setLoading(true)
    try {
      await api.stopAutoApply()
      setTimeout(fetchStatus, 1000)
    } catch (e) {
      console.error('Stop error:', e)
    }
    setLoading(false)
  }

  const isRunning = status?.running
  const progress = status?.progress || {}
  const quotaData = quota?.quota || {}
  const statsData = quota?.stats || {}

  const appliedToday = quotaData.applied || 0
  const targetToday = quotaData.target || 500
  const progressPct = Math.min(100, Math.round((appliedToday / targetToday) * 100))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-fg-primary flex items-center gap-3">
            <Zap size={24} className="text-accent" />
            Auto-Apply Engine
          </h1>
          <p className="text-sm text-fg-muted mt-1">
            Automated job applications across all platforms
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!isRunning ? (
            <>
              <div className="flex items-center gap-2">
                <label className="text-xs text-fg-muted">Target:</label>
                <input
                  type="number"
                  value={maxApps}
                  onChange={e => setMaxApps(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 px-2 py-1.5 bg-bg-tertiary border border-border rounded-lg text-sm text-fg-primary"
                />
              </div>
              <button
                onClick={handleStart}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent/90 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Play size={16} />
                Start Auto-Apply
              </button>
            </>
          ) : (
            <button
              onClick={handleStop}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-danger hover:bg-danger/90 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Square size={16} />
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Daily Quota Progress */}
      <div className="bg-bg-secondary border border-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-fg-primary flex items-center gap-2">
            <Target size={16} className="text-accent" />
            Daily Quota
          </h3>
          <span className="text-sm font-mono text-accent">
            {appliedToday} / {targetToday}
          </span>
        </div>
        <div className="w-full h-3 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent to-purple-400 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2 text-xs text-fg-muted">
          <span>{progressPct}% complete</span>
          <span>{targetToday - appliedToday} remaining</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Applied Today', value: appliedToday, icon: CheckCircle, color: 'text-success' },
          { label: 'Failed', value: quotaData.failed || 0, icon: XCircle, color: 'text-danger' },
          { label: 'Skipped', value: quotaData.skipped || 0, icon: Clock, color: 'text-warning' },
          { label: 'All-Time Total', value: statsData.total || 0, icon: TrendingUp, color: 'text-accent' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-bg-secondary border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Icon size={14} className={color} />
              <span className="text-xs text-fg-muted">{label}</span>
            </div>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Current Job */}
      {isRunning && progress.current_job && (
        <div className="bg-accent-bg/50 border border-accent/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 bg-accent rounded-full animate-pulse" />
            <span className="text-xs font-medium text-accent">Currently Applying</span>
          </div>
          <p className="text-sm text-fg-primary font-medium">
            {progress.current_job.title} at {progress.current_job.company}
          </p>
          <p className="text-xs text-fg-muted mt-0.5">
            Method: {progress.current_job.method?.replace('_', ' ')}
          </p>
        </div>
      )}

      {/* Live Log */}
      <div className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-bg-tertiary/50">
          <span className="text-xs font-semibold text-fg-primary">Activity Log</span>
          {isRunning && (
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
              <span className="text-xs text-accent">Live</span>
            </div>
          )}
        </div>
        <div
          ref={logRef}
          className="h-80 overflow-y-auto p-3 font-mono text-xs space-y-0.5"
        >
          {(status?.log || []).map((entry, i) => {
            const color = entry.type === 'applied' ? 'text-success'
              : entry.type === 'failed' ? 'text-danger'
              : entry.type === 'error' ? 'text-danger'
              : entry.type === 'info' ? 'text-accent'
              : entry.type === 'done' ? 'text-success'
              : 'text-fg-muted'

            const time = entry.time?.split('T')[1]?.split('.')[0] || ''

            return (
              <div key={i} className={`${color} leading-relaxed`}>
                <span className="text-fg-muted/50">{time}</span>{' '}
                {entry.type === 'applied' && `Applied: ${entry.job} at ${entry.company} (${entry.method})`}
                {entry.type === 'failed' && `Failed: ${entry.job} at ${entry.company} — ${entry.error}`}
                {entry.type === 'info' && entry.message}
                {entry.type === 'done' && entry.message}
                {entry.type === 'error' && entry.message}
                {entry.type === 'skip' && `Skipped: ${entry.reason}`}
              </div>
            )
          })}
          {(!status?.log || status.log.length === 0) && (
            <p className="text-fg-muted text-center py-8">
              No activity yet. Start auto-apply to begin.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
