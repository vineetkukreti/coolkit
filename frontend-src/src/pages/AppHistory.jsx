import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, Briefcase, CalendarCheck, AlertTriangle, XCircle, Loader2, Search, RotateCcw, ExternalLink } from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'
import FilterBar, { useFilters, applyFilters, dateRangeMatch } from '../components/FilterBar'

const STATUS_BADGE = {
  applied: 'bg-success-bg text-success border-success/30',
  partial: 'bg-warning-bg text-warning border-warning/30',
  failed: 'bg-danger-bg text-danger border-danger/30',
  skipped: 'bg-info-bg text-info border-info/30',
}

const STATUS_LABEL = {
  applied: 'Applied',
  partial: 'Partial',
  failed: 'Failed',
  skipped: 'Skipped',
}

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'applied', label: 'Applied' },
  { value: 'partial', label: 'Partial' },
  { value: 'failed', label: 'Failed' },
  { value: 'skipped', label: 'Skipped' },
]

function StatCard({ icon: Icon, label, value, valueClass = 'text-fg-primary', iconBg }) {
  return (
    <div className="flex-1 min-w-0 bg-bg-secondary border border-border rounded-2xl p-5 flex flex-col gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg}`}>
        <Icon size={20} className={valueClass} />
      </div>
      <div>
        <p className={`text-3xl font-mono font-semibold leading-none ${valueClass}`}>
          {value ?? '—'}
        </p>
        <p className="text-fg-muted text-sm mt-1.5">{label}</p>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const cls = STATUS_BADGE[status] ?? 'bg-bg-tertiary text-fg-secondary border-border'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  )
}

function isToday(timestamp) {
  if (!timestamp) return false
  const d = new Date(timestamp)
  const now = new Date()
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  )
}

function formatDate(timestamp) {
  if (!timestamp) return '—'
  const d = new Date(timestamp)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
}

function exportCSV(applications, toast) {
  try {
    const headers = ['Status', 'Job Title', 'Company', 'Location', 'Platform', 'URL', 'Message', 'Date']
    const rows = applications.map((a) => [
      a.status ?? '',
      a.title ?? '',
      a.company ?? '',
      a.location ?? '',
      a.platform ?? '',
      a.url ?? '',
      (a.message ?? '').replace(/,/g, ';'),
      a.timestamp ? new Date(a.timestamp).toISOString() : '',
    ])
    const csvContent = [headers, ...rows].map((r) => r.map((v) => `"${v}"`).join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `applications_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    toast({ title: 'Export complete', description: `${applications.length} records exported to CSV`, type: 'success' })
  } catch (e) {
    toast({ title: 'Export failed', description: e.message, type: 'error' })
  }
}

export default function AppHistory() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const [applications, setApplications] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filter state
  const [search, setSearch] = useState('')
  const appFilterDefs = [
    { key: 'status', type: 'select', label: 'Status', options: [
      { label: 'All Statuses', value: '' }, { label: 'Applied', value: 'applied' }, { label: 'Partial', value: 'partial' }, { label: 'Failed', value: 'failed' }, { label: 'Skipped', value: 'skipped' },
    ], match: (item, v) => item.status === v },
    { key: 'platform', type: 'select', label: 'Platform', options: [
      { label: 'All Platforms', value: '' }, { label: 'LinkedIn', value: 'linkedin' }, { label: 'Naukri', value: 'naukri' }, { label: 'Wellfound', value: 'wellfound' },
    ], match: (item, v) => (item.platform || '').toLowerCase().includes(v) },
    { key: 'date_range', type: 'dateRange', match: dateRangeMatch('timestamp') },
  ]
  const appFilters = useFilters(appFilterDefs)

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const [appData, statsData] = await Promise.all([
          api.getApplications(),
          api.getStats(),
        ])
        setApplications(appData.applications ?? [])
        setStats(statsData)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Derived: applied today — computed from raw applications list, not from stats
  const appliedToday = useMemo(
    () => applications.filter((a) => a.status === 'applied' && isToday(a.timestamp)).length,
    [applications]
  )

  // Filtered list
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    let result = applications.filter((a) => {
      const matchesSearch =
        !q ||
        (a.title ?? '').toLowerCase().includes(q) ||
        (a.company ?? '').toLowerCase().includes(q)
      return matchesSearch
    })
    return applyFilters(result, appFilters.values, appFilterDefs)
  }, [applications, search, appFilters.values])

  const partial = stats?.partial ?? 0
  const failed = (stats?.failed ?? 0) + (stats?.skipped ?? 0)

  const hasApplications = applications.length > 0

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary px-6 py-8 font-sans">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-fg-primary">Application History</h1>
          <p className="text-fg-muted text-sm mt-1">Track every job application across all sessions</p>
        </div>
        <button
          onClick={() => exportCSV(filtered, toast)}
          disabled={filtered.length === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-border text-fg-secondary text-sm font-medium hover:bg-bg-secondary hover:text-fg-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Download size={16} />
          Export CSV
        </button>
      </div>

      {/* Stat cards */}
      <div className="flex gap-4 mb-6">
        <StatCard
          icon={Briefcase}
          label="Total Applied"
          value={stats?.applied ?? '—'}
          valueClass="text-fg-primary"
          iconBg="bg-bg-tertiary"
        />
        <StatCard
          icon={CalendarCheck}
          label="Applied Today"
          value={loading ? '—' : appliedToday}
          valueClass="text-success"
          iconBg="bg-success-bg"
        />
        <StatCard
          icon={AlertTriangle}
          label="Partial / Manual"
          value={stats ? partial : '—'}
          valueClass="text-warning"
          iconBg="bg-warning-bg"
        />
        <StatCard
          icon={XCircle}
          label="Failed / Skipped"
          value={stats ? failed : '—'}
          valueClass="text-danger"
          iconBg="bg-danger-bg"
        />
      </div>

      {/* Filter row */}
      <div className="flex items-center gap-3 mb-4">
        {/* Search input */}
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by job title or company…"
            className="w-full bg-bg-secondary border border-border rounded-xl pl-9 pr-3.5 py-2 text-fg-primary text-sm placeholder:text-fg-muted focus:outline-none focus:border-accent transition-colors"
          />
        </div>
      </div>
      <div className="mb-4">
        <FilterBar
          filters={appFilterDefs}
          values={appFilters.values}
          onChange={appFilters.setFilter}
          onClear={() => { setSearch(''); appFilters.clearFilters() }}
          isFiltered={appFilters.isFiltered || !!search}
          resultCount={filtered.length}
          totalCount={applications.length}
        />
      </div>

      {/* Table card */}
      <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden">
        {/* Table header */}
        <div className="bg-bg-tertiary px-5 py-3 grid grid-cols-[120px_1fr_160px_140px_110px_170px_80px] gap-4 text-xs font-medium text-fg-muted uppercase tracking-wider">
          <span>Status</span>
          <span>Job Title</span>
          <span>Company</span>
          <span>Location</span>
          <span>Platform</span>
          <span>Date</span>
          <span></span>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex items-center justify-center gap-3 py-20 text-fg-muted">
            <Loader2 size={20} className="animate-spin text-accent" />
            <span className="text-sm">Loading applications…</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-20">
            <p className="text-danger text-sm">{error}</p>
          </div>
        ) : !hasApplications ? (
          /* Empty state — no applications at all */
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-bg-tertiary border border-border flex items-center justify-center">
              <Briefcase size={28} className="text-fg-muted opacity-50" />
            </div>
            <div className="text-center">
              <p className="text-fg-primary text-sm font-medium">No applications yet</p>
              <p className="text-fg-muted text-xs mt-1">Start by searching for jobs!</p>
            </div>
            <button
              onClick={() => navigate('/search')}
              className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-xl transition-colors"
            >
              <Search size={14} />
              Search Jobs
            </button>
          </div>
        ) : filtered.length === 0 ? (
          /* Empty state — filters returned nothing */
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Search size={28} className="text-fg-muted opacity-40" />
            <p className="text-fg-muted text-sm">No applications match your filters.</p>
            <button
              onClick={() => { setSearch(''); appFilters.clearFilters() }}
              className="text-accent text-xs hover:underline"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((app, i) => (
              <div
                key={i}
                className="px-5 py-3.5 grid grid-cols-[120px_1fr_160px_140px_110px_170px_80px] gap-4 items-center hover:bg-bg-tertiary/50 transition-colors"
              >
                <div>
                  <StatusBadge status={app.status} />
                </div>
                <div className="min-w-0">
                  {app.url ? (
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-fg-primary text-sm font-medium truncate block hover:text-accent transition-colors"
                      title={app.title}
                    >
                      {app.title ?? '—'}
                    </a>
                  ) : (
                    <span className="text-fg-primary text-sm font-medium truncate block" title={app.title}>
                      {app.title ?? '—'}
                    </span>
                  )}
                  {app.message && (
                    <p className="text-fg-muted text-xs truncate mt-0.5" title={app.message}>
                      {app.message}
                    </p>
                  )}
                </div>
                <span className="text-fg-secondary text-sm truncate" title={app.company}>{app.company ?? '—'}</span>
                <span className="text-fg-secondary text-sm truncate" title={app.location}>{app.location ?? '—'}</span>
                <span className="text-fg-muted text-sm capitalize">{app.platform ?? '—'}</span>
                <span className="text-fg-muted text-xs font-mono whitespace-nowrap">{formatDate(app.timestamp)}</span>
                {/* Retry action for failed applications */}
                <div className="flex justify-end">
                  {app.status === 'failed' && app.url && (
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Open job URL to retry manually"
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-danger-bg border border-danger/30 text-danger text-xs font-medium hover:bg-danger/20 transition-colors"
                    >
                      <ExternalLink size={11} />
                      Retry
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        {!loading && !error && hasApplications && filtered.length > 0 && (
          <div className="bg-bg-tertiary/40 px-5 py-3 border-t border-border">
            <p className="text-fg-muted text-xs">
              Showing <span className="text-fg-secondary font-medium">{filtered.length}</span>
              {filtered.length !== applications.length && (
                <> of <span className="text-fg-secondary font-medium">{applications.length}</span></>
              )}{' '}
              records
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
