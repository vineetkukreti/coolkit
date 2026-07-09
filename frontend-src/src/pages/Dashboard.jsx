import { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Send, Mail, Database, Target, Zap, RefreshCw, Search,
  Wifi, WifiOff, LayoutDashboard, BarChart3, ChevronDown,
  TrendingUp, AlertTriangle, Lightbulb, Play, Square, Loader2,
  Check,
} from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'

// ─── Constants ───────────────────────────────────────────────────────────────

const DOT_COLORS = {
  applied: 'bg-success',
  skipped: 'bg-warning',
  failed: 'bg-danger',
  info: 'bg-info',
  accent: 'bg-accent',
}

const SAMPLE_COMPANIES = [
  { company: 'Google', count: 8 },
  { company: 'Microsoft', count: 6 },
  { company: 'Atlassian', count: 5 },
  { company: 'Razorpay', count: 4 },
  { company: 'Swiggy', count: 3 },
]

const SAMPLE_WEEKLY = [3, 5, 8, 6, 12, 4, 2]

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// ─── Small helpers ────────────────────────────────────────────────────────────

function formatActivityTitle(app) {
  if (app.status === 'applied') return `Applied to ${app.job_title ?? 'a job'}${app.company ? ` at ${app.company}` : ''}`
  if (app.status === 'skipped') return `Skipped ${app.job_title ?? 'a job'}${app.company ? ` at ${app.company}` : ''}`
  if (app.status === 'failed') return `Failed to apply to ${app.job_title ?? 'a job'}${app.company ? ` at ${app.company}` : ''}`
  return app.job_title ?? 'Job activity'
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date)) return ''
  const diff = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function getDayOfWeek(dateStr) {
  if (!dateStr) return -1
  const d = new Date(dateStr)
  if (isNaN(d)) return -1
  // 0 = Sun, 1 = Mon … 6 = Sat  →  shift to Mon=0 … Sun=6
  return (d.getDay() + 6) % 7
}

// ─── Shared UI components ─────────────────────────────────────────────────────

function StatCard({ label, icon: Icon, value, sub }) {
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-fg-muted font-medium">{label}</span>
        <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
          <Icon size={15} className="text-accent" />
        </div>
      </div>
      <div className="text-4xl font-bold font-mono text-fg-primary">{value}</div>
      {sub && <div className="text-xs text-fg-muted font-medium">{sub}</div>}
    </div>
  )
}


// ─── Daily Cycle Card ─────────────────────────────────────────────────────────

function DailyCycleCard() {
  const { toast } = useToast()
  const [status, setStatus] = useState(null)
  const [maxApps, setMaxApps] = useState(500)
  const [runScrapers, setRunScrapers] = useState(true)
  const [starting, setStarting] = useState(false)
  const pollRef = useRef(null)
  const logEndRef = useRef(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.getOrchestratorStatus()
        setStatus(data)
      } catch {}
    }
    poll()
    pollRef.current = setInterval(poll, 2000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [status?.log?.length])

  const isRunning = status?.running
  const logs = status?.log || []

  const handleStart = async () => {
    setStarting(true)
    try {
      await api.startDailyCycle({ max_applications: maxApps, run_scrapers: runScrapers })
      toast({ title: 'Daily cycle started', type: 'success', description: `Target: ${maxApps} applications` })
    } catch (e) {
      toast({ title: 'Failed to start', description: e.message, type: 'error' })
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    try {
      await api.stopDailyCycle()
      toast({ title: 'Stopping daily cycle...', type: 'info' })
    } catch {}
  }

  const phaseLabel = {
    scraping: 'Scraping',
    scoring: 'Scoring',
    applying: 'Applying',
    reporting: 'Reporting',
  }

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-fg-primary">Daily Cycle</h2>
        {isRunning && status?.phase && (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-bg text-accent">
            <Loader2 size={10} className="animate-spin" />
            {phaseLabel[status.phase] || status.phase}
          </span>
        )}
        {status?.status === 'done' && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-success-bg text-success">Done</span>
        )}
        {status?.status === 'error' && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-danger-bg text-danger">Error</span>
        )}
      </div>

      {!isRunning ? (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <label className="text-xs text-fg-muted">Max apps:</label>
            <input type="number" min={10} max={2000} value={maxApps}
              onChange={e => setMaxApps(Number(e.target.value) || 500)}
              className="w-20 bg-bg-tertiary border border-border text-fg-primary text-sm rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent" />
            <label className="flex items-center gap-1.5 text-xs text-fg-muted cursor-pointer">
              <input type="checkbox" checked={runScrapers} onChange={e => setRunScrapers(e.target.checked)}
                className="rounded border-border" />
              Run scrapers
            </label>
          </div>
          <button onClick={handleStart} disabled={starting}
            className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 text-white text-sm font-medium py-2.5 rounded-xl transition-colors disabled:opacity-50">
            {starting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Run Daily Cycle
          </button>
        </div>
      ) : (
        <button onClick={handleStop}
          className="w-full flex items-center justify-center gap-2 bg-danger/10 hover:bg-danger/20 text-danger text-sm font-medium py-2 rounded-xl transition-colors">
          <Square size={12} /> Stop
        </button>
      )}

      {/* Log terminal */}
      {logs.length > 0 && (
        <div className="max-h-40 overflow-y-auto bg-bg-primary rounded-lg border border-border font-mono text-[11px]">
          <div className="px-3 py-2 space-y-0.5">
            {logs.slice(-30).map((entry, i) => (
              <div key={i} className={`py-0.5 ${
                entry.type === 'error' ? 'text-danger' :
                entry.type === 'report' ? 'text-success font-semibold' :
                'text-fg-secondary'
              }`}>
                {entry.message}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Overview Tab ─────────────────────────────────────────────────────────────

function EmailHealthCard({ emailStats }) {
  if (!emailStats) return null
  const { delivered, failed, replied, errors, recent_failures, worker_history } = emailStats
  const total = (delivered || 0) + (failed || 0)
  const deliveryPct = total > 0 ? ((delivered || 0) / total * 100).toFixed(0) : 0

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-fg-primary">Email Health</h2>
        <span className="text-xs text-fg-muted">{deliveryPct}% delivery rate</span>
      </div>

      {/* Delivery bar */}
      <div className="w-full h-2.5 bg-bg-tertiary rounded-full overflow-hidden flex">
        {delivered > 0 && <div className="h-full bg-success" style={{ width: `${(delivered / total) * 100}%` }} />}
        {(replied || 0) > 0 && <div className="h-full bg-accent" style={{ width: `${(replied / total) * 100}%` }} />}
        {failed > 0 && <div className="h-full bg-danger" style={{ width: `${(failed / total) * 100}%` }} />}
      </div>
      <div className="flex gap-4 text-xs">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-success" />Delivered {delivered || 0}</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent" />Replied {replied || 0}</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-danger" />Failed {failed || 0}</span>
      </div>

      {/* Error breakdown */}
      {errors && Object.keys(errors).length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-fg-muted font-medium uppercase tracking-wider">Failure Types</p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(errors).map(([type, count]) => (
              <span key={type} className="px-2 py-0.5 rounded text-xs bg-danger-bg text-danger border border-danger/20">
                {type.replace('_', ' ')}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recent failures */}
      {recent_failures && recent_failures.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-fg-muted font-medium uppercase tracking-wider">Recent Failures</p>
          <div className="space-y-1">
            {recent_failures.slice(0, 3).map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-fg-muted">
                <span className="text-danger font-mono">{f.error_type || 'unknown'}</span>
                <span className="truncate flex-1">{f.email}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Worker runs */}
      {worker_history && worker_history.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-fg-muted font-medium uppercase tracking-wider">Worker Activity</p>
          <div className="space-y-1">
            {worker_history.slice(0, 3).map((w, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="text-fg-muted font-mono">{w.type}</span>
                <span className={w.status === 'completed' ? 'text-success' : w.status === 'failed' ? 'text-danger' : 'text-warning'}>{w.status}</span>
                <span className="text-fg-muted">{w.succeeded}/{w.total}</span>
                <span className="text-fg-muted ml-auto">{w.started_at ? new Date(w.started_at).toLocaleDateString() : ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function OverviewTab({
  loading,
  appliedCount,
  skippedCount,
  emailCount,
  emailStats,
  postsScraped,
  activity,
  browserOnline,
}) {
  const navigate = useNavigate()

  const total = (appliedCount ?? 0) + (skippedCount ?? 0)
  const matchRate = total > 0
    ? `${Math.round(((appliedCount ?? 0) / total) * 100)}%`
    : '—'

  const hasAnyStats = (appliedCount ?? 0) > 0 || (postsScraped ?? 0) > 0 || (emailCount ?? 0) > 0

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      {!hasAnyStats && !loading ? (
        <div className="bg-bg-secondary border border-border rounded-2xl p-8 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-xl bg-accent-bg flex items-center justify-center mb-1">
            <Zap size={22} className="text-accent" />
          </div>
          <p className="text-fg-primary font-semibold text-base">No activity yet</p>
          <p className="text-sm text-fg-muted max-w-xs">
            Start by searching for jobs. Your stats will appear here once you get going.
          </p>
          <button
            onClick={() => navigate('/find?tab=search')}
            className="mt-2 flex items-center gap-2 bg-accent hover:bg-accent/90 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
          >
            <Search size={14} />
            Search Jobs
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            label="Applications Sent"
            icon={Send}
            value={loading ? '—' : (appliedCount ?? 0)}
            sub={loading ? null : skippedCount != null ? `${skippedCount} skipped` : null}
          />
          <StatCard
            label="Emails Sent"
            icon={Mail}
            value={loading ? '—' : (emailCount ?? 0)}
            sub={emailStats ? `${emailStats.replied || 0} replied · ${emailStats.failed || 0} failed` : null}
          />
          <StatCard
            label="Posts Scraped"
            icon={Database}
            value={loading ? '—' : (postsScraped ?? 0)}
          />
          <StatCard
            label="Match Rate"
            icon={Target}
            value={loading ? '—' : matchRate}
            sub={loading || total === 0 ? null : `${total} total evaluated`}
          />
        </div>
      )}

      {/* Email Health */}
      {emailStats && <EmailHealthCard emailStats={emailStats} />}

      {/* Bottom Section */}
      <div className="flex gap-4 flex-col lg:flex-row">

        {/* Recent Activity */}
        <div className="flex-1 bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-fg-primary">Recent Activity</h2>
            <span className="flex items-center gap-1.5 text-xs font-medium text-success bg-success-bg px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse inline-block" />
              Live
            </span>
          </div>

          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 rounded-lg bg-bg-tertiary animate-pulse" />
              ))}
            </div>
          ) : activity.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <p className="text-sm text-fg-muted">No activity yet</p>
              <p className="text-xs text-fg-muted max-w-xs">
                Start by searching for jobs — your application history will show up here.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {activity.map((item, idx) => (
                <div
                  key={item.id ?? item.job_id ?? `item-${idx}`}
                  className="flex items-start gap-3 rounded-lg bg-bg-tertiary px-3 py-2.5"
                >
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${DOT_COLORS[item.status] ?? 'bg-fg-muted'}`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-fg-primary leading-snug truncate">
                      {formatActivityTitle(item)}
                    </p>
                    <p className="text-xs text-fg-muted mt-0.5">
                      {formatRelativeTime(item.applied_at || item.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-4" style={{ width: '340px', minWidth: '280px', flexShrink: 0 }}>

          {/* Quick Actions */}
          <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-fg-primary">Quick Actions</h2>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/find?tab=scraper')}
                className="w-full flex items-center justify-center gap-2 bg-bg-tertiary hover:bg-border text-fg-primary text-sm font-medium py-2.5 rounded-xl border border-border transition-colors"
              >
                <RefreshCw size={14} />
                Scrape New Posts
              </button>
              <button
                onClick={() => navigate('/outreach?tab=email')}
                className="w-full flex items-center justify-center gap-2 bg-bg-tertiary hover:bg-border text-fg-primary text-sm font-medium py-2.5 rounded-xl border border-border transition-colors"
              >
                <Mail size={14} />
                Bulk Email Outreach
              </button>
            </div>
          </div>

          {/* Daily Cycle */}
          <DailyCycleCard />

          {/* Browser Status */}
          <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-fg-primary">Browser Status</h2>
            <div className="flex items-center justify-between">
              <span className="text-xs text-fg-muted">Status</span>
              <div className={`flex items-center gap-1.5 text-xs font-medium ${browserOnline ? 'text-success' : 'text-fg-muted'}`}>
                {browserOnline
                  ? <><Wifi size={12} /> Online</>
                  : <><WifiOff size={12} /> Offline</>
                }
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

// ─── Analytics Tab ────────────────────────────────────────────────────────────

const PERIOD_OPTIONS = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'All time', value: 'all' },
]

function PeriodSelector({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const selected = PERIOD_OPTIONS.find((o) => o.value === value) ?? PERIOD_OPTIONS[0]

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 bg-bg-secondary border border-border text-fg-secondary text-sm font-medium px-3.5 py-2 rounded-xl hover:border-accent/50 transition-colors"
      >
        {selected.label}
        <ChevronDown size={14} className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1.5 z-20 bg-bg-secondary border border-border rounded-xl overflow-hidden shadow-xl min-w-[140px]">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => { onChange(opt.value); setOpen(false) }}
                className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                  opt.value === value
                    ? 'text-accent bg-accent-bg'
                    : 'text-fg-secondary hover:bg-bg-tertiary'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function ApplicationFunnel({ funnelData }) {
  const max = funnelData[0]?.count || 1

  const stages = [
    { label: 'Jobs Found', count: funnelData[0]?.count ?? 0, colorClass: 'bg-accent-bg', textClass: 'text-accent' },
    { label: 'Applied', count: funnelData[1]?.count ?? 0, colorClass: 'bg-info-bg', textClass: 'text-info' },
    { label: 'Emails Sent', count: funnelData[2]?.count ?? 0, colorClass: 'bg-warning-bg', textClass: 'text-warning' },
    { label: 'Responses', count: funnelData[3]?.count ?? 5, colorClass: 'bg-success-bg', textClass: 'text-success' },
  ]

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4 flex-1">
      <h3 className="text-sm font-semibold text-fg-primary">Application Funnel</h3>
      <div className="space-y-3">
        {stages.map((stage, idx) => {
          const pct = max > 0 ? Math.max(8, Math.round((stage.count / max) * 100)) : 8
          return (
            <div key={idx} className="flex items-center gap-3">
              <div className="flex-1">
                <div
                  className={`${stage.colorClass} rounded-lg px-3 py-2.5 flex items-center transition-all duration-500`}
                  style={{ width: `${pct}%`, minWidth: '100px' }}
                >
                  <span className={`text-xs font-medium ${stage.textClass} truncate`}>{stage.label}</span>
                </div>
              </div>
              <span className="font-mono text-sm font-bold text-fg-primary w-10 text-right shrink-0">
                {stage.count}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function WeeklyBarChart({ weeklyData }) {
  const todayDow = (new Date().getDay() + 6) % 7 // Mon=0…Sun=6
  const maxVal = Math.max(...weeklyData, 1)
  const BAR_HEIGHT = 120 // px — total chart area height

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4 flex-1">
      <h3 className="text-sm font-semibold text-fg-primary">Weekly Applications</h3>
      <div className="flex items-end gap-2 pt-2" style={{ height: `${BAR_HEIGHT + 28}px` }}>
        {DAY_LABELS.map((day, idx) => {
          const val = weeklyData[idx] ?? 0
          const barH = maxVal > 0 ? Math.max(4, Math.round((val / maxVal) * BAR_HEIGHT)) : 4
          const isToday = idx === todayDow
          return (
            <div key={day} className="flex flex-col items-center gap-1.5 flex-1">
              {/* Count label */}
              <span className={`text-xs font-mono font-semibold ${isToday ? 'text-accent' : 'text-fg-muted'}`}>
                {val > 0 ? val : ''}
              </span>
              {/* Bar */}
              <div
                className={`w-full rounded-t-md transition-all duration-500 ${isToday ? 'bg-accent' : 'bg-accent-bg'}`}
                style={{ height: `${barH}px` }}
              />
              {/* Day label */}
              <span className={`text-xs ${isToday ? 'text-accent font-semibold' : 'text-fg-muted'}`}>
                {day}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TopCompanies({ companies }) {
  const maxCount = companies[0]?.count || 1
  return (
    <div className="flex-1 bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
      <h3 className="text-sm font-semibold text-fg-primary">Top Companies Applied</h3>
      {companies.length === 0 ? (
        <p className="text-sm text-fg-muted py-4 text-center">No company data yet</p>
      ) : (
        <div className="space-y-3">
          {companies.map((item, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <span className="text-xs font-mono text-fg-muted w-4 shrink-0">{idx + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-fg-primary font-medium truncate">{item.company}</span>
                  <span className="text-xs font-mono font-bold text-accent bg-accent-bg px-2 py-0.5 rounded-full ml-2 shrink-0">
                    {item.count}
                  </span>
                </div>
                <div className="w-full h-1 rounded-full bg-bg-tertiary overflow-hidden">
                  <div
                    className="h-full rounded-full bg-accent-bg transition-all duration-500"
                    style={{ width: `${Math.round((item.count / maxCount) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PlatformBreakdown({ platforms }) {
  const maxCount = Math.max(...platforms.map((p) => p.count), 1)
  const PLATFORM_COLORS = {
    LinkedIn: 'bg-info',
    Naukri: 'bg-warning',
    Wellfound: 'bg-success',
  }

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-3">
      <h3 className="text-sm font-semibold text-fg-primary">Platform Breakdown</h3>
      <div className="space-y-3">
        {platforms.map((p, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-fg-secondary font-medium">{p.name}</span>
              <span className="font-mono text-fg-primary font-semibold">{p.count}</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${PLATFORM_COLORS[p.name] ?? 'bg-accent'}`}
                style={{ width: `${Math.max(4, Math.round((p.count / maxCount) * 100))}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function PerformanceMetrics({ appliedCount, postsScraped, emailCount }) {
  const applyRate = postsScraped > 0 ? `${Math.round((appliedCount / postsScraped) * 100)}%` : '0%'
  const avgDay = appliedCount > 0 ? (appliedCount / 7).toFixed(1) : '0.0'

  const metrics = [
    { label: 'Apply Rate', value: applyRate, colorClass: 'text-success', bgClass: 'bg-success-bg' },
    { label: 'Email Open Rate', value: '49%', colorClass: 'text-accent', bgClass: 'bg-accent-bg' },
    { label: 'Avg / Day', value: avgDay, colorClass: 'text-warning', bgClass: 'bg-warning-bg' },
    { label: 'Avg Match Score', value: '92%', colorClass: 'text-info', bgClass: 'bg-info-bg' },
  ]

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-3">
      <h3 className="text-sm font-semibold text-fg-primary">Performance Metrics</h3>
      <div className="grid grid-cols-2 gap-2.5">
        {metrics.map((m, idx) => (
          <div key={idx} className="bg-bg-tertiary rounded-lg p-3.5 flex flex-col gap-1">
            <span className={`text-xl font-mono font-bold ${m.colorClass}`}>{m.value}</span>
            <span className="text-xs text-fg-muted leading-snug">{m.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function AnalyticsTab({ loading, applications, appliedCount, postsScraped, emailCount, stats }) {
  const [period, setPeriod] = useState('7d')

  const hasData = applications.length > 0

  // Filter applications by period
  const filteredApps = useMemo(() => {
    if (period === 'all') return applications
    const days = period === '7d' ? 7 : 30
    const cutoff = Date.now() - days * 86400 * 1000
    return applications.filter((a) => {
      const t = new Date(a.applied_at || a.created_at || 0).getTime()
      return t >= cutoff
    })
  }, [applications, period])

  // Funnel data
  const funnelData = useMemo(() => [
    { label: 'Jobs Found', count: postsScraped ?? 0 },
    { label: 'Applied', count: appliedCount ?? 0 },
    { label: 'Emails Sent', count: emailCount ?? 0 },
    { label: 'Responses', count: 0 },
  ], [postsScraped, appliedCount, emailCount])

  // Weekly bar data (Mon–Sun) from filtered apps, or sample data
  const weeklyData = useMemo(() => {
    if (!hasData) return SAMPLE_WEEKLY
    const counts = [0, 0, 0, 0, 0, 0, 0]
    // Use last 7 days window regardless of period for weekly chart
    const cutoff = Date.now() - 7 * 86400 * 1000
    applications.forEach((a) => {
      const t = new Date(a.applied_at || a.created_at || 0).getTime()
      if (t >= cutoff) {
        const dow = getDayOfWeek(a.applied_at || a.created_at)
        if (dow >= 0) counts[dow] += 1
      }
    })
    return counts
  }, [applications, hasData])

  // Top companies
  const topCompanies = useMemo(() => {
    if (!hasData) return SAMPLE_COMPANIES
    const map = {}
    filteredApps.forEach((a) => {
      const co = a.company?.trim()
      if (!co) return
      map[co] = (map[co] ?? 0) + 1
    })
    return Object.entries(map)
      .map(([company, count]) => ({ company, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  }, [filteredApps, hasData])

  // Platform breakdown
  const platformData = useMemo(() => {
    const PLATFORMS = ['LinkedIn', 'Naukri', 'Wellfound']
    if (!hasData) {
      return [
        { name: 'LinkedIn', count: 0 },
        { name: 'Naukri', count: 0 },
        { name: 'Wellfound', count: 0 },
      ]
    }
    const map = {}
    filteredApps.forEach((a) => {
      const platform = a.platform?.trim()
      if (!platform) return
      map[platform] = (map[platform] ?? 0) + 1
    })
    return PLATFORMS.map((name) => ({ name, count: map[name] ?? 0 }))
  }, [filteredApps, hasData])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-48 rounded-2xl bg-bg-secondary border border-border animate-pulse" />
        <div className="h-48 rounded-2xl bg-bg-secondary border border-border animate-pulse" />
      </div>
    )
  }

  if (!hasData) {
    return (
      <div className="bg-bg-secondary border border-border rounded-2xl p-10 flex flex-col items-center gap-3 text-center">
        <div className="w-12 h-12 rounded-xl bg-accent-bg flex items-center justify-center mb-1">
          <BarChart3 size={22} className="text-accent" />
        </div>
        <p className="text-fg-primary font-semibold text-base">Not enough data yet</p>
        <p className="text-sm text-fg-muted max-w-xs">
          Start applying to see your analytics! Your charts and insights will appear here once you have some applications.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Period selector */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-fg-muted">Showing data for selected period</p>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Top row: Funnel + Weekly */}
      <div className="flex gap-4 flex-col lg:flex-row">
        <ApplicationFunnel funnelData={funnelData} />
        <WeeklyBarChart weeklyData={weeklyData} />
      </div>

      {/* Bottom row: Companies + Platform + Performance */}
      <div className="flex gap-4 flex-col lg:flex-row">
        <TopCompanies companies={topCompanies} />
        <div className="flex flex-col gap-4" style={{ width: '380px', minWidth: '300px', flexShrink: 0 }}>
          <PlatformBreakdown platforms={platformData} />
          <PerformanceMetrics
            appliedCount={appliedCount ?? 0}
            postsScraped={postsScraped ?? 0}
            emailCount={emailCount ?? 0}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Outreach Insights Tab ────────────────────────────────────────────────────

const FUNNEL_STAGES = [
  { key: 'sent', label: 'Sent', color: 'bg-info', textColor: 'text-info', bgColor: 'bg-info-bg' },
  { key: 'replied', label: 'Replied', color: 'bg-success', textColor: 'text-success', bgColor: 'bg-success-bg' },
  { key: 'interviewing', label: 'Interviewing', color: 'bg-info', textColor: 'text-info', bgColor: 'bg-info-bg' },
  { key: 'offer', label: 'Offer', color: 'bg-accent', textColor: 'text-accent', bgColor: 'bg-accent-bg' },
  { key: 'rejected', label: 'Rejected', color: 'bg-danger', textColor: 'text-danger', bgColor: 'bg-danger-bg' },
]

const RELEVANCE_DOT = { High: 'bg-success', Medium: 'bg-warning', Low: 'bg-danger' }

const IMPACT_BADGE = {
  HIGH: 'bg-danger-bg text-danger',
  MEDIUM: 'bg-warning-bg text-warning',
  LOW: 'bg-success-bg text-success',
}

function OutreachInsightsTab() {
  const [patterns, setPatterns] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [pRes] = await Promise.allSettled([
        api.getPatterns(),
      ])
      if (cancelled) return
      if (pRes.status === 'fulfilled') setPatterns(pRes.value)
      setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-48 rounded-2xl bg-bg-secondary border border-border animate-pulse" />
        <div className="h-48 rounded-2xl bg-bg-secondary border border-border animate-pulse" />
      </div>
    )
  }

  // Funnel data comes from analyze_patterns().funnel
  const funnel = patterns?.funnel ?? {}
  const funnelMax = Math.max(...FUNNEL_STAGES.map((s) => funnel[s.key] ?? 0), 1)

  // Domain relevance — backend returns by_domain_relevance with {domain, sent, replied, rate}
  const rawDomain = patterns?.by_domain_relevance ?? []
  const relevance = rawDomain.length > 0
    ? rawDomain.map((d) => ({
        level: d.domain,
        sent: d.sent ?? 0,
        converted: d.replied ?? 0,
        rate: d.rate != null ? Math.round(d.rate * 100) : 0,
      }))
    : [
        { level: 'High', sent: 0, converted: 0, rate: 0 },
        { level: 'Medium', sent: 0, converted: 0, rate: 0 },
        { level: 'Low', sent: 0, converted: 0, rate: 0 },
      ]

  // Recommendations — backend returns impact in lowercase, IMPACT_BADGE uses uppercase
  const recommendations = (patterns?.recommendations ?? []).slice(0, 5)

  return (
    <div className="space-y-4">
      {/* Conversion Funnel */}
      <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
            <TrendingUp size={15} className="text-accent" />
          </div>
          <h3 className="text-sm font-semibold text-fg-primary">Conversion Funnel</h3>
        </div>
        <div className="space-y-3">
          {FUNNEL_STAGES.map((stage) => {
            const count = funnel[stage.key] ?? 0
            const pct = funnelMax > 0 ? Math.max(8, Math.round((count / funnelMax) * 100)) : 8
            return (
              <div key={stage.key} className="flex items-center gap-3">
                <span className="text-xs text-fg-muted font-medium w-24 shrink-0">{stage.label}</span>
                <div className="flex-1">
                  <div
                    className={`${stage.bgColor} rounded-lg px-3 py-2 flex items-center transition-all duration-500`}
                    style={{ width: `${pct}%`, minWidth: '60px' }}
                  >
                    <span className={`text-xs font-mono font-semibold ${stage.textColor}`}>{count}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Bottom row: Domain Relevance + Recommendations */}
      <div className="flex gap-4 flex-col lg:flex-row">

        {/* Domain Relevance Breakdown */}
        <div className="flex-1 bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
              <Target size={15} className="text-accent" />
            </div>
            <h3 className="text-sm font-semibold text-fg-primary">Domain Relevance</h3>
          </div>
          <div className="space-y-2">
            {/* Header */}
            <div className="flex items-center gap-3 text-xs text-fg-muted font-medium px-1">
              <span className="w-20">Relevance</span>
              <span className="flex-1 text-center">Sent</span>
              <span className="flex-1 text-center">Converted</span>
              <span className="flex-1 text-right">Rate</span>
            </div>
            {relevance.map((row) => (
              <div
                key={row.level}
                className="flex items-center gap-3 bg-bg-tertiary rounded-lg px-3 py-2.5"
              >
                <div className="flex items-center gap-2 w-20">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${RELEVANCE_DOT[row.level] ?? 'bg-fg-muted'}`} />
                  <span className="text-sm text-fg-primary font-medium">{row.level}</span>
                </div>
                <span className="flex-1 text-center text-sm font-mono text-fg-secondary">{row.sent}</span>
                <span className="flex-1 text-center text-sm font-mono text-fg-secondary">{row.converted}</span>
                <span className="flex-1 text-right text-sm font-mono font-semibold text-fg-primary">
                  {typeof row.rate === 'number' ? `${row.rate}%` : row.rate}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div className="flex-1 bg-bg-secondary border border-border rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-warning-bg flex items-center justify-center">
              <Lightbulb size={15} className="text-warning" />
            </div>
            <h3 className="text-sm font-semibold text-fg-primary">Recommendations</h3>
          </div>

          {recommendations.length === 0 ? (
            <p className="text-sm text-fg-muted py-4 text-center">No recommendations yet</p>
          ) : (
            <div className="space-y-2">
              {recommendations.map((rec, idx) => (
                <div key={idx} className="bg-bg-tertiary rounded-lg px-3 py-2.5 space-y-1">
                  <div className="flex items-start gap-2">
                    <span
                      className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                        IMPACT_BADGE[(rec.impact || '').toUpperCase()] ?? 'bg-bg-tertiary text-fg-muted'
                      } shrink-0 mt-0.5`}
                    >
                      {rec.impact}
                    </span>
                    <span className="text-sm text-fg-primary leading-snug">{rec.action}</span>
                  </div>
                  {rec.reasoning && (
                    <p className="text-xs text-fg-muted leading-relaxed ml-[calc(0.375rem+0.5rem+theme(spacing.2))]">
                      {rec.reasoning}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Root Dashboard ───────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview', label: 'Overview', Icon: LayoutDashboard },
  { id: 'analytics', label: 'Analytics', Icon: BarChart3 },
  { id: 'insights', label: 'Outreach Insights', Icon: TrendingUp },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const { toast } = useToast()

  const [activeTab, setActiveTab] = useState('overview')

  // Shared data state
  const [userName, setUserName] = useState(null)
  const [appliedCount, setAppliedCount] = useState(null)
  const [skippedCount, setSkippedCount] = useState(null)
  const [emailCount, setEmailCount] = useState(null)
  const [postsScraped, setPostsScraped] = useState(null)
  const [activity, setActivity] = useState([])
  const [allApplications, setAllApplications] = useState([])
  const [browserOnline, setBrowserOnline] = useState(false)
  const [stats, setStats] = useState(null)
  const [emailStats, setEmailStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const [profileRes, statsRes, dbStatsRes, appsRes, emailHistRes, browserRes, emailStatsRes] =
        await Promise.allSettled([
          api.getProfile(),
          api.getStats(),
          api.getDbStats(),
          api.getApplications(),
          api.getEmailHistory(),
          api.getBrowserStatus(),
          api.getEmailStats(),
        ])

      if (cancelled) return

      // Profile
      if (profileRes.status === 'fulfilled') {
        const p = profileRes.value
        setUserName(p?.full_name || p?.name || null)
      } else {
        toast({ type: 'error', title: 'Could not load profile', description: profileRes.reason?.message })
      }

      // Stats
      if (statsRes.status === 'fulfilled') {
        const s = statsRes.value
        setStats(s)
        setAppliedCount(s?.applied ?? 0)
        setSkippedCount(s?.skipped ?? 0)
      } else {
        toast({ type: 'error', title: 'Could not load stats', description: statsRes.reason?.message })
      }

      // DB stats
      if (dbStatsRes.status === 'fulfilled') {
        setPostsScraped(dbStatsRes.value?.total_posts ?? 0)
      } else {
        toast({ type: 'error', title: 'Could not load DB stats', description: dbStatsRes.reason?.message })
      }

      // Applications
      if (appsRes.status === 'fulfilled') {
        const rawApps = appsRes.value
        const apps = Array.isArray(rawApps?.applications) ? rawApps.applications : Array.isArray(rawApps) ? rawApps : []
        setAllApplications(apps)
        const sorted = [...apps].sort((a, b) => {
          const ta = new Date(a.applied_at || a.created_at || 0).getTime()
          const tb = new Date(b.applied_at || b.created_at || 0).getTime()
          return tb - ta
        })
        setActivity(sorted.slice(0, 5))
      } else {
        toast({ type: 'error', title: 'Could not load applications', description: appsRes.reason?.message })
      }

      // Email history
      if (emailHistRes.status === 'fulfilled') {
        const rawHist = emailHistRes.value
        const hist = Array.isArray(rawHist?.history) ? rawHist.history : Array.isArray(rawHist) ? rawHist : []
        setEmailCount(hist.length)
      } else {
        setEmailCount(0)
      }

      // Browser status
      if (browserRes.status === 'fulfilled') {
        setBrowserOnline(browserRes.value?.running ?? false)
      }

      // Email stats
      if (emailStatsRes.status === 'fulfilled') {
        setEmailStats(emailStatsRes.value)
      }

      if (!cancelled) setLoading(false)
    }

    load()
    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const hasAnyStats = (appliedCount ?? 0) > 0 || (postsScraped ?? 0) > 0 || (emailCount ?? 0) > 0

  const subtitleByTab = {
    overview: hasAnyStats
      ? "Here's what's happening with your job search today."
      : "Get started by searching for jobs.",
    analytics: "Visualize trends and performance across your job search.",
    insights: "Understand outreach patterns and optimize your conversion.",
  }

  return (
    <div className="min-h-screen bg-bg-primary p-6 md:p-8 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-fg-primary">
            {loading
              ? 'Welcome to coolkit'
              : userName
                ? `Welcome back, ${userName}`
                : 'Welcome to coolkit'
            }
          </h1>
          <p className="text-sm text-fg-muted mt-1">
            {subtitleByTab[activeTab]}
          </p>
        </div>
        <button
          onClick={() => navigate('/find?tab=search')}
          className="flex items-center gap-2 bg-accent hover:bg-accent/90 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors shrink-0"
        >
          <Search size={15} />
          Quick Search
        </button>
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-1 border-b border-border">
        {TABS.map(({ id, label, Icon }) => {
          const isActive = activeTab === id
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors relative -mb-px ${
                isActive
                  ? 'text-fg-primary border-b-2 border-accent'
                  : 'text-fg-muted hover:text-fg-secondary'
              }`}
            >
              <Icon
                size={15}
                className={isActive ? 'text-accent' : 'text-fg-muted'}
              />
              <span className={isActive ? 'font-semibold' : ''}>{label}</span>
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <OverviewTab
          loading={loading}
          appliedCount={appliedCount}
          skippedCount={skippedCount}
          emailCount={emailCount}
          emailStats={emailStats}
          postsScraped={postsScraped}
          activity={activity}
          browserOnline={browserOnline}
        />
      )}

      {activeTab === 'analytics' && (
        <AnalyticsTab
          loading={loading}
          applications={allApplications}
          appliedCount={appliedCount}
          postsScraped={postsScraped}
          emailCount={emailCount}
          stats={stats}
        />
      )}

      {activeTab === 'insights' && (
        <OutreachInsightsTab />
      )}

    </div>
  )
}
