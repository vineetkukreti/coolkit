import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Building2, Mail, Globe, Search, ChevronDown, ChevronUp,
  Link2, RefreshCw, X, MapPin, Tag, FileText,
  ArrowUpDown, ChevronLeft, ChevronRight,
  Zap, CheckCircle, AlertCircle, Loader2, Square, Play,
  SearchCheck, MailSearch,
} from 'lucide-react'
import { api } from '../lib/api'

// ─── Stat Card ───────────────────────────────────────────────────────────────

function StatCard({ label, icon: Icon, value, sub, accent = false }) {
  return (
    <div className={`border rounded-2xl p-5 flex flex-col gap-3 ${
      accent ? 'bg-accent-bg border-accent/20' : 'bg-bg-secondary border-border'
    }`}>
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

// ─── Filter Pill ─────────────────────────────────────────────────────────────

function FilterPill({ label, value, onClear }) {
  if (!value) return null
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-accent-bg text-accent text-xs font-medium rounded-full">
      {label}: {value}
      <button onClick={onClear} className="hover:text-fg-primary"><X size={12} /></button>
    </span>
  )
}

// ─── Status Badge ────────────────────────────────────────────────────────────

const STATUS_STYLES = {
  not_contacted: 'bg-bg-tertiary text-fg-muted',
  contacted: 'bg-info/10 text-info',
  replied: 'bg-success/10 text-success',
  interested: 'bg-accent-bg text-accent',
  not_interested: 'bg-danger/10 text-danger',
}

function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.not_contacted
  const label = (status || 'not_contacted').replace(/_/g, ' ')
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${style}`}>
      {label}
    </span>
  )
}

// ─── Bar Chart (horizontal) ──────────────────────────────────────────────────

function HBar({ data, maxItems = 6 }) {
  const items = Object.entries(data || {}).slice(0, maxItems)
  const max = Math.max(...items.map(([, v]) => v), 1)
  return (
    <div className="flex flex-col gap-2">
      {items.map(([label, count]) => (
        <div key={label} className="flex items-center gap-2">
          <span className="text-xs text-fg-muted w-32 truncate text-right" title={label}>{label}</span>
          <div className="flex-1 h-5 bg-bg-tertiary rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all"
              style={{ width: `${(count / max) * 100}%` }}
            />
          </div>
          <span className="text-xs font-mono text-fg-secondary w-8 text-right">{count}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Email Finder Panel ─────────────────────────────────────────────────────

function EmailFinderPanel({ onComplete }) {
  const [enrichStatus, setEnrichStatus] = useState(null)
  const [maxLeads, setMaxLeads] = useState(50)
  const [target, setTarget] = useState('startup_leads')
  const pollRef = useRef(null)

  const startEnrichment = async () => {
    try {
      await api.startEnrichment({ max_leads: maxLeads, target })
      pollRef.current = setInterval(async () => {
        try {
          const data = await api.getEnrichmentStatus()
          setEnrichStatus(data)
          if (!data.running && data.summary) {
            clearInterval(pollRef.current)
            pollRef.current = null
            if (onComplete) onComplete()
          }
        } catch {}
      }, 1500)
    } catch (err) {
      console.error('Failed to start enrichment:', err)
    }
  }

  const stopEnrichment = async () => {
    try {
      await api.stopEnrichment()
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {}
  }

  // Check if already running on mount
  useEffect(() => {
    const check = async () => {
      try {
        const data = await api.getEnrichmentStatus()
        if (data.running) {
          setEnrichStatus(data)
          pollRef.current = setInterval(async () => {
            try {
              const data2 = await api.getEnrichmentStatus()
              setEnrichStatus(data2)
              if (!data2.running) {
                clearInterval(pollRef.current)
                pollRef.current = null
                if (onComplete) onComplete()
              }
            } catch {}
          }, 1500)
        }
      } catch {}
    }
    check()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const isRunning = enrichStatus?.running
  const progress = enrichStatus?.total ? Math.round((enrichStatus.current / enrichStatus.total) * 100) : 0

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
            <MailSearch size={15} className="text-accent" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-fg-primary">Email Finder</h3>
            <p className="text-xs text-fg-muted">Search the web for company emails</p>
          </div>
        </div>

        {!isRunning ? (
          <div className="flex items-center gap-2">
            <select value={target} onChange={e => setTarget(e.target.value)}
              className="text-xs bg-bg-primary border border-border rounded-lg px-2 py-1.5 text-fg-primary">
              <option value="startup_leads">Startup Leads</option>
              <option value="posts">LinkedIn Posts</option>
            </select>
            <select value={maxLeads} onChange={e => setMaxLeads(Number(e.target.value))}
              className="text-xs bg-bg-primary border border-border rounded-lg px-2 py-1.5 text-fg-primary">
              <option value={10}>10 leads</option>
              <option value={25}>25 leads</option>
              <option value={50}>50 leads</option>
              <option value={100}>100 leads</option>
              <option value={200}>200 leads</option>
            </select>
            <button
              onClick={startEnrichment}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent-dim text-fg-inverse
                text-xs font-semibold rounded-xl transition-colors"
            >
              <Zap size={13} /> Find Emails
            </button>
          </div>
        ) : (
          <button
            onClick={stopEnrichment}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-danger/10 hover:bg-danger/20
              text-danger text-xs font-semibold rounded-lg transition-colors"
          >
            <Square size={11} /> Stop
          </button>
        )}
      </div>

      {/* Progress bar */}
      {isRunning && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs font-mono text-fg-secondary w-16 text-right">
              {enrichStatus.current}/{enrichStatus.total}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-fg-muted">
            <Loader2 size={12} className="animate-spin text-accent" />
            <span>Searching: <span className="text-fg-primary font-medium">{enrichStatus.current_company}</span></span>
          </div>

          {/* Stats row */}
          <div className="flex gap-4 text-xs">
            <span className="flex items-center gap-1 text-success">
              <CheckCircle size={11} /> {enrichStatus.found || 0} found
            </span>
            <span className="flex items-center gap-1 text-fg-muted">
              <X size={11} /> {enrichStatus.not_found || 0} not found
            </span>
            {enrichStatus.errors > 0 && (
              <span className="flex items-center gap-1 text-danger">
                <AlertCircle size={11} /> {enrichStatus.errors} errors
              </span>
            )}
          </div>
        </div>
      )}

      {/* Live results feed */}
      {enrichStatus?.results?.length > 0 && (
        <div className="mt-3 max-h-48 overflow-y-auto border border-border rounded-lg bg-bg-primary">
          <div className="divide-y divide-border">
            {[...enrichStatus.results].reverse().slice(0, 20).map((r, i) => (
              <div key={i} className="px-3 py-1.5 text-xs flex items-center gap-2">
                {r.type === 'found' && (
                  <>
                    <CheckCircle size={11} className="text-success shrink-0" />
                    <span className="text-fg-primary font-medium truncate">{r.company}</span>
                    <span className="text-fg-muted mx-1">-</span>
                    <span className="text-accent truncate">{r.emails?.join(', ')}</span>
                    <span className="text-fg-muted ml-auto shrink-0">({r.all_count} total)</span>
                  </>
                )}
                {r.type === 'not_found' && (
                  <>
                    <X size={11} className="text-fg-muted shrink-0" />
                    <span className="text-fg-muted truncate">{r.company}</span>
                    <span className="text-fg-muted ml-auto">no emails</span>
                  </>
                )}
                {r.type === 'searching' && (
                  <>
                    <Loader2 size={11} className="text-accent animate-spin shrink-0" />
                    <span className="text-fg-secondary truncate">{r.company}...</span>
                  </>
                )}
                {r.type === 'error' && (
                  <>
                    <AlertCircle size={11} className="text-danger shrink-0" />
                    <span className="text-danger truncate">{r.company}: {r.error}</span>
                  </>
                )}
                {r.type === 'done' && (
                  <>
                    <CheckCircle size={11} className="text-success shrink-0" />
                    <span className="text-success font-medium">
                      Done! {r.enriched} enriched, {r.total_emails_found} emails found
                    </span>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary when done */}
      {enrichStatus?.summary && !isRunning && (
        <div className="mt-3 p-3 bg-success/5 border border-success/20 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-success font-medium">
            <CheckCircle size={14} />
            Enrichment complete
          </div>
          <div className="flex gap-6 mt-2 text-xs text-fg-secondary">
            <span><strong className="text-fg-primary">{enrichStatus.summary.enriched}</strong> companies enriched</span>
            <span><strong className="text-fg-primary">{enrichStatus.summary.total_emails_found}</strong> emails found</span>
            <span>{enrichStatus.summary.skipped} skipped</span>
            {enrichStatus.summary.failed > 0 && (
              <span className="text-danger">{enrichStatus.summary.failed} failed</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Lead Row ────────────────────────────────────────────────────────────────

function LeadRow({ lead, onStatusChange, onFindEmail }) {
  const [expanded, setExpanded] = useState(false)
  const [finding, setFinding] = useState(false)
  const [foundEmails, setFoundEmails] = useState(null)

  const handleFindEmail = async (e) => {
    e.stopPropagation()
    setFinding(true)
    setFoundEmails(null)
    try {
      const data = await api.enrichSingleLead(lead.id)
      setFoundEmails(data)
      if (data.emails_found > 0 && onFindEmail) {
        onFindEmail(lead.id, data.saved)
      }
    } catch (err) {
      console.error('Find email failed:', err)
    } finally {
      setFinding(false)
    }
  }

  return (
    <>
      <tr
        className="border-b border-border hover:bg-bg-tertiary/50 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center shrink-0">
              <Building2 size={14} className="text-accent" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium text-fg-primary truncate max-w-[200px]">{lead.company_name}</div>
              {lead.industry && <div className="text-xs text-fg-muted truncate">{lead.industry}</div>}
            </div>
          </div>
        </td>
        <td className="px-4 py-3">
          {lead.email ? (
            <a
              href={`mailto:${lead.email}`}
              className="text-sm text-accent hover:underline truncate block max-w-[220px]"
              onClick={e => e.stopPropagation()}
              title={lead.email}
            >
              {lead.email}
            </a>
          ) : (
            <button
              onClick={handleFindEmail}
              disabled={finding}
              className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-accent/10 hover:bg-accent/20
                text-accent rounded-md transition-colors disabled:opacity-50"
            >
              {finding ? (
                <><Loader2 size={11} className="animate-spin" /> Searching...</>
              ) : (
                <><SearchCheck size={11} /> Find Email</>
              )}
            </button>
          )}
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-1 text-sm text-fg-secondary">
            <MapPin size={12} className="text-fg-muted shrink-0" />
            <span className="truncate max-w-[150px]">{lead.location || lead.city || lead.country || '--'}</span>
          </div>
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={lead.email_status} />
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {lead.website && (
              <a href={lead.website} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}
                className="text-fg-muted hover:text-accent transition-colors">
                <Globe size={14} />
              </a>
            )}
            {lead.linkedin_url && (
              <a href={lead.linkedin_url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}
                className="text-fg-muted hover:text-accent transition-colors">
                <Link2 size={14} />
              </a>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <button className="text-fg-muted hover:text-fg-primary">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-bg-tertiary/30">
          <td colSpan={6} className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-medium text-fg-primary mb-2">Details</h4>
                {lead.description && (
                  <p className="text-fg-secondary text-xs leading-relaxed mb-2 line-clamp-3">{lead.description}</p>
                )}
                <div className="flex flex-wrap gap-2 text-xs">
                  {lead.sector && <span className="px-2 py-0.5 bg-bg-secondary rounded text-fg-muted">{lead.sector}</span>}
                  {lead.entity_type && <span className="px-2 py-0.5 bg-bg-secondary rounded text-fg-muted">{lead.entity_type}</span>}
                  {lead.funding_status && <span className="px-2 py-0.5 bg-bg-secondary rounded text-fg-muted">{lead.funding_status}</span>}
                  {lead.funding_info && <span className="px-2 py-0.5 bg-success/10 text-success rounded">{lead.funding_info}</span>}
                  {lead.employees && lead.employees !== '0' && lead.employees !== 'Information Not Shared' && (
                    <span className="px-2 py-0.5 bg-bg-secondary rounded text-fg-muted">{lead.employees} employees</span>
                  )}
                </div>
                {lead.tags && (
                  <div className="flex items-center gap-1 mt-2">
                    <Tag size={11} className="text-fg-muted" />
                    <span className="text-xs text-fg-muted">{lead.tags}</span>
                  </div>
                )}
                {lead.notes && (
                  <div className="flex items-center gap-1 mt-1">
                    <FileText size={11} className="text-fg-muted" />
                    <span className="text-xs text-fg-muted">{lead.notes}</span>
                  </div>
                )}
              </div>
              <div>
                <h4 className="font-medium text-fg-primary mb-2">Actions</h4>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={lead.email_status || 'not_contacted'}
                    onChange={e => {
                      e.stopPropagation()
                      onStatusChange(lead.id, e.target.value)
                    }}
                    onClick={e => e.stopPropagation()}
                    className="text-xs bg-bg-secondary border border-border rounded-lg px-2 py-1.5 text-fg-primary"
                  >
                    <option value="not_contacted">Not Contacted</option>
                    <option value="contacted">Contacted</option>
                    <option value="replied">Replied</option>
                    <option value="interested">Interested</option>
                    <option value="not_interested">Not Interested</option>
                  </select>

                  {!lead.email && (
                    <button
                      onClick={handleFindEmail}
                      disabled={finding}
                      className="inline-flex items-center gap-1 text-xs px-2 py-1.5 bg-accent hover:bg-accent-dim
                        text-fg-inverse rounded-lg transition-colors disabled:opacity-50"
                    >
                      {finding ? (
                        <><Loader2 size={12} className="animate-spin" /> Searching...</>
                      ) : (
                        <><Zap size={12} /> Find Email</>
                      )}
                    </button>
                  )}

                  {lead.website && (
                    <a href={lead.website} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs px-2 py-1.5 bg-bg-secondary border border-border rounded-lg text-fg-secondary hover:text-accent"
                      onClick={e => e.stopPropagation()}>
                      <Globe size={12} /> Website
                    </a>
                  )}
                  {lead.linkedin_url && (
                    <a href={lead.linkedin_url} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs px-2 py-1.5 bg-bg-secondary border border-border rounded-lg text-fg-secondary hover:text-accent"
                      onClick={e => e.stopPropagation()}>
                      <Link2 size={12} /> LinkedIn
                    </a>
                  )}
                </div>

                {/* Single-lead email finder results */}
                {foundEmails && (
                  <div className="mt-3 p-2 bg-bg-primary border border-border rounded-lg text-xs">
                    {foundEmails.emails_found > 0 ? (
                      <div>
                        <div className="flex items-center gap-1 text-success mb-1">
                          <CheckCircle size={11} /> Found {foundEmails.emails_found} emails
                        </div>
                        {foundEmails.emails.map((e, i) => (
                          <div key={i} className="flex items-center gap-2 py-0.5">
                            <span className="text-accent">{e.email}</span>
                            <span className="text-fg-muted">via {e.source}</span>
                            <span className="text-fg-muted font-mono">score:{e.score}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-fg-muted">
                        <X size={11} /> No emails found for this company
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-2 text-xs text-fg-muted">
                  Source: {lead.source_file || 'Unknown'}
                </div>
                {lead.dipp_recognition && (
                  <div className="text-xs text-fg-muted mt-1">DIPP: {lead.dipp_recognition}</div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function StartupLeads() {
  const [leads, setLeads] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [total, setTotal] = useState(0)

  // Filters
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [industry, setIndustry] = useState('')
  const [emailStatus, setEmailStatus] = useState('')
  const [hasEmail, setHasEmail] = useState(false)
  const [source, setSource] = useState('')
  const [sortBy, setSortBy] = useState('company_name')
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)
  const [sources, setSources] = useState([])

  const PAGE_SIZE = 50

  const fetchLeads = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (country) params.set('country', country)
      if (industry) params.set('industry', industry)
      if (emailStatus) params.set('email_status', emailStatus)
      if (hasEmail) params.set('has_email', 'true')
      if (source) params.set('source', source)
      params.set('sort_by', sortBy)
      params.set('sort_dir', sortDir)
      params.set('limit', PAGE_SIZE)
      params.set('offset', page * PAGE_SIZE)

      const data = await api.getLeads(Object.fromEntries(params))
      setLeads(data.leads || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.error('Failed to fetch leads:', err)
    } finally {
      setLoading(false)
    }
  }, [search, country, industry, emailStatus, hasEmail, source, sortBy, sortDir, page])

  const fetchStats = async () => {
    try {
      setStats(await api.getLeadsStats())
    } catch {}
  }

  const fetchSources = async () => {
    try {
      const data = await api.getLeadsSources()
      setSources(data.sources || [])
    } catch {}
  }

  const refreshAll = () => Promise.all([fetchLeads(), fetchStats(), fetchSources()])

  useEffect(() => {
    fetchLeads()
  }, [fetchLeads])

  useEffect(() => {
    fetchStats()
    fetchSources()
  }, [])

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      await api.updateLead(leadId, { email_status: newStatus })
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, email_status: newStatus } : l))
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  const handleFindEmail = (leadId, emailStr) => {
    // Update the lead in-place when a single-lead email is found
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, email: emailStr } : l))
  }

  const handleImport = async () => {
    setImporting(true)
    try {
      await api.importLeads()
      await refreshAll()
    } catch (err) {
      console.error('Import failed:', err)
    } finally {
      setImporting(false)
    }
  }

  const handleSort = (col) => {
    if (sortBy === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(col)
      setSortDir('asc')
    }
    setPage(0)
  }

  const clearFilters = () => {
    setSearch('')
    setCountry('')
    setIndustry('')
    setEmailStatus('')
    setHasEmail(false)
    setSource('')
    setPage(0)
  }

  const hasFilters = search || country || industry || emailStatus || hasEmail || source
  const totalPages = Math.ceil(total / PAGE_SIZE)

  const countries = stats?.by_country ? Object.keys(stats.by_country) : []
  const industries = stats?.by_industry ? Object.keys(stats.by_industry) : []
  const missingEmails = stats ? stats.total - stats.with_email : 0

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-fg-primary">Startup Leads</h1>
          <p className="text-sm text-fg-muted mt-1">
            Healthcare & biotech startups for cold outreach
            {missingEmails > 0 && (
              <span className="ml-2 text-warning">({missingEmails} missing emails)</span>
            )}
          </p>
        </div>
        <button
          onClick={handleImport}
          disabled={importing}
          className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-dim text-fg-inverse
            text-sm font-semibold rounded-xl transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={importing ? 'animate-spin' : ''} />
          {importing ? 'Importing...' : 'Import Leads'}
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Startups" icon={Building2} value={stats.total} accent />
          <StatCard label="With Email" icon={Mail} value={stats.with_email}
            sub={`${stats.total ? Math.round((stats.with_email / stats.total) * 100) : 0}% coverage`} />
          <StatCard label="With Website" icon={Globe} value={stats.with_website} />
          <StatCard label="With LinkedIn" icon={Link2} value={stats.with_linkedin} />
        </div>
      )}

      {/* Email Finder Panel */}
      <EmailFinderPanel onComplete={refreshAll} />

      {/* Charts Row */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-bg-secondary border border-border rounded-2xl p-5">
            <h3 className="text-sm font-medium text-fg-primary mb-3">By Country</h3>
            <HBar data={stats.by_country} />
          </div>
          <div className="bg-bg-secondary border border-border rounded-2xl p-5">
            <h3 className="text-sm font-medium text-fg-primary mb-3">By Industry</h3>
            <HBar data={stats.by_industry} />
          </div>
          <div className="bg-bg-secondary border border-border rounded-2xl p-5">
            <h3 className="text-sm font-medium text-fg-primary mb-3">By Source</h3>
            <HBar data={Object.fromEntries(
              Object.entries(stats.by_source || {}).map(([k, v]) => [k.replace('.csv', '').replace('.xlsx', ''), v])
            )} />
          </div>
        </div>
      )}

      {/* Filters Bar */}
      <div className="bg-bg-secondary border border-border rounded-2xl p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
            <input
              type="text"
              placeholder="Search companies, emails, descriptions..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0) }}
              className="w-full pl-9 pr-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary
                placeholder:text-fg-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
          <select value={country} onChange={e => { setCountry(e.target.value); setPage(0) }}
            className="text-sm bg-bg-primary border border-border rounded-lg px-3 py-2 text-fg-primary">
            <option value="">All Countries</option>
            {countries.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={industry} onChange={e => { setIndustry(e.target.value); setPage(0) }}
            className="text-sm bg-bg-primary border border-border rounded-lg px-3 py-2 text-fg-primary">
            <option value="">All Industries</option>
            {industries.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
          <select value={emailStatus} onChange={e => { setEmailStatus(e.target.value); setPage(0) }}
            className="text-sm bg-bg-primary border border-border rounded-lg px-3 py-2 text-fg-primary">
            <option value="">All Statuses</option>
            <option value="not_contacted">Not Contacted</option>
            <option value="contacted">Contacted</option>
            <option value="replied">Replied</option>
            <option value="interested">Interested</option>
            <option value="not_interested">Not Interested</option>
          </select>
          <select value={source} onChange={e => { setSource(e.target.value); setPage(0) }}
            className="text-sm bg-bg-primary border border-border rounded-lg px-3 py-2 text-fg-primary">
            <option value="">All Sources</option>
            {sources.map(s => <option key={s} value={s}>{s.replace('.csv', '').replace('.xlsx', '')}</option>)}
          </select>
          <label className="inline-flex items-center gap-1.5 text-sm text-fg-secondary cursor-pointer">
            <input type="checkbox" checked={hasEmail} onChange={e => { setHasEmail(e.target.checked); setPage(0) }}
              className="rounded border-border" />
            Has Email
          </label>
          {hasFilters && (
            <button onClick={clearFilters}
              className="text-xs text-fg-muted hover:text-accent transition-colors flex items-center gap-1">
              <X size={12} /> Clear
            </button>
          )}
        </div>
        {hasFilters && (
          <div className="flex flex-wrap gap-2">
            <FilterPill label="Search" value={search} onClear={() => setSearch('')} />
            <FilterPill label="Country" value={country} onClear={() => setCountry('')} />
            <FilterPill label="Industry" value={industry} onClear={() => setIndustry('')} />
            <FilterPill label="Status" value={emailStatus} onClear={() => setEmailStatus('')} />
            <FilterPill label="Source" value={source} onClear={() => setSource('')} />
            {hasEmail && <FilterPill label="Filter" value="Has Email" onClear={() => setHasEmail(false)} />}
          </div>
        )}
      </div>

      {/* Results count + pagination */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-fg-muted">
          {total} lead{total !== 1 ? 's' : ''} found
          {hasFilters ? ' (filtered)' : ''}
        </span>
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="p-1.5 rounded-lg border border-border hover:bg-bg-tertiary disabled:opacity-30 text-fg-muted">
              <ChevronLeft size={14} />
            </button>
            <span className="text-sm text-fg-secondary font-mono">
              {page + 1} / {totalPages}
            </span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="p-1.5 rounded-lg border border-border hover:bg-bg-tertiary disabled:opacity-30 text-fg-muted">
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-bg-tertiary/50">
                {[
                  { key: 'company_name', label: 'Company' },
                  { key: 'email', label: 'Email', sortable: false },
                  { key: 'location', label: 'Location' },
                  { key: 'email_status', label: 'Status' },
                  { key: 'links', label: 'Links', sortable: false },
                  { key: 'expand', label: '', sortable: false },
                ].map(col => (
                  <th
                    key={col.key}
                    className={`px-4 py-3 text-left text-xs font-semibold text-fg-muted uppercase tracking-wider ${
                      col.sortable !== false ? 'cursor-pointer hover:text-fg-primary select-none' : ''
                    }`}
                    onClick={() => col.sortable !== false && handleSort(col.key)}
                  >
                    <div className="flex items-center gap-1">
                      {col.label}
                      {col.sortable !== false && sortBy === col.key && (
                        sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
                      )}
                      {col.sortable !== false && sortBy !== col.key && col.label && (
                        <ArrowUpDown size={10} className="opacity-30" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm text-fg-muted">Loading leads...</span>
                    </div>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <Building2 size={32} className="text-fg-muted" />
                      <div>
                        <div className="text-sm font-medium text-fg-primary">No leads found</div>
                        <div className="text-xs text-fg-muted mt-1">
                          {hasFilters
                            ? 'Try adjusting your filters'
                            : 'Click "Import Leads" to load data from your CSV/XLSX files'}
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                leads.map(lead => (
                  <LeadRow
                    key={lead.id}
                    lead={lead}
                    onStatusChange={handleStatusChange}
                    onFindEmail={handleFindEmail}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center">
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="px-3 py-1.5 rounded-lg border border-border hover:bg-bg-tertiary disabled:opacity-30 text-sm text-fg-secondary">
              Previous
            </button>
            <span className="text-sm text-fg-muted px-3">
              Page {page + 1} of {totalPages}
            </span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="px-3 py-1.5 rounded-lg border border-border hover:bg-bg-tertiary disabled:opacity-30 text-sm text-fg-secondary">
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
