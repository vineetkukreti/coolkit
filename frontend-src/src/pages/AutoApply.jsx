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

  const hasLog = status?.log && status.log.length > 0

  return (
    <div className="p-6 md:p-8 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-fg-primary flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
              <Zap size={16} className="text-accent" />
            </div>
            Auto-Apply Engine
          </h2>
          <p className="text-sm text-fg-muted mt-1 ml-[42px]">
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
                  className="w-20 px-2.5 py-1.5 bg-bg-tertiary border border-border rounded-lg text-sm text-fg-primary
                    focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
              <button
                onClick={handleStart}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/90 text-white rounded-xl
                  text-sm font-semibold transition-colors disabled:opacity-50"
              >
                <Play size={14} />
                Start Auto-Apply
              </button>
            </>
          ) : (
            <button
              onClick={handleStop}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-danger/10 hover:bg-danger/20 text-danger
                rounded-xl text-sm font-semibold border border-danger/20 transition-colors disabled:opacity-50"
            >
              <Square size={14} />
              Stop Engine
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Applied Today', value: appliedToday, icon: CheckCircle, iconBg: 'bg-success-bg', iconColor: 'text-success', valueColor: 'text-fg-primary' },
          { label: 'Failed', value: quotaData.failed || 0, icon: XCircle, iconBg: 'bg-danger-bg', iconColor: 'text-danger', valueColor: 'text-fg-primary' },
          { label: 'Skipped', value: quotaData.skipped || 0, icon: Clock, iconBg: 'bg-warning-bg', iconColor: 'text-warning', valueColor: 'text-fg-primary' },
          { label: 'All-Time Total', value: statsData.total || 0, icon: TrendingUp, iconBg: 'bg-accent-bg', iconColor: 'text-accent', valueColor: 'text-fg-primary' },
        ].map(({ label, value, icon: Icon, iconBg, iconColor, valueColor }) => (
          <div key={label} className="bg-bg-secondary border border-border rounded-2xl p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-fg-muted font-medium">{label}</span>
              <div className={`w-8 h-8 rounded-lg ${iconBg} flex items-center justify-center`}>
                <Icon size={15} className={iconColor} />
              </div>
            </div>
            <p className={`text-4xl font-bold font-mono ${valueColor}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Daily Quota Progress */}
      <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-fg-primary flex items-center gap-2">
            <Target size={14} className="text-accent" />
            Daily Quota
          </h3>
          <span className="text-sm font-mono font-semibold text-accent">
            {appliedToday} <span className="text-fg-muted font-normal">/ {targetToday}</span>
          </span>
        </div>
        <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent to-purple-400 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-fg-muted">
          <span>{progressPct}% complete</span>
          <span>{targetToday - appliedToday} remaining</span>
        </div>
      </div>

      {/* Current Job */}
      {isRunning && progress.current_job && (
        <div className="bg-accent-bg/40 border border-accent/20 rounded-2xl p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
            <Zap size={16} className="text-accent animate-pulse" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-accent mb-0.5">Currently Applying</p>
            <p className="text-sm text-fg-primary font-medium truncate">
              {progress.current_job.title} at {progress.current_job.company}
            </p>
          </div>
          <span className="text-xs text-fg-muted bg-bg-tertiary px-2.5 py-1 rounded-lg shrink-0">
            {progress.current_job.method?.replace('_', ' ')}
          </span>
        </div>
      )}

      {/* Activity Log */}
      <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <span className="text-sm font-semibold text-fg-primary">Activity Log</span>
          {isRunning && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-success bg-success-bg px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse inline-block" />
              Live
            </span>
          )}
        </div>
        <div
          ref={logRef}
          className={`overflow-y-auto px-5 py-3 font-mono text-xs space-y-1 ${hasLog ? 'max-h-72' : ''}`}
        >
          {hasLog ? (status.log.map((entry, i) => {
            const color = entry.type === 'applied' ? 'text-success'
              : entry.type === 'failed' ? 'text-danger'
              : entry.type === 'error' ? 'text-danger'
              : entry.type === 'info' ? 'text-accent'
              : entry.type === 'done' ? 'text-success'
              : 'text-fg-muted'

            const time = entry.time?.split('T')[1]?.split('.')[0] || ''

            return (
              <div key={i} className={`${color} leading-relaxed py-0.5`}>
                <span className="text-fg-muted/40 mr-2">{time}</span>
                {entry.type === 'applied' && `Applied: ${entry.job} at ${entry.company} (${entry.method})`}
                {entry.type === 'failed' && `Failed: ${entry.job} at ${entry.company} — ${entry.error}`}
                {entry.type === 'info' && entry.message}
                {entry.type === 'done' && entry.message}
                {entry.type === 'error' && entry.message}
                {entry.type === 'skip' && `Skipped: ${entry.reason}`}
              </div>
            )
          })) : (
            <div className="flex flex-col items-center gap-2 py-8">
              <div className="w-10 h-10 rounded-xl bg-bg-tertiary flex items-center justify-center">
                <Play size={16} className="text-fg-muted" />
              </div>
              <p className="text-sm text-fg-muted">No activity yet</p>
              <p className="text-xs text-fg-muted/60">Start auto-apply to see logs here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
