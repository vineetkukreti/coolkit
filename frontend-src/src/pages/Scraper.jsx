import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Globe,
  Play,
  LogIn,
  ShieldCheck,
  Loader2,
  Check,
  Search,
  CheckCircle,
  SkipForward,
  Copy,
  Sparkles,
  FileText,
  Database,
  AlertCircle,
  Trophy,
  Square,
  Mail,
  ArrowRight,
  RotateCcw,
  Users,
  AtSign,
  TrendingUp,
  Building,
  ChevronDown,
  MapPin,
} from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'

/* ─── Event type config for log rendering ─── */
const EVENT_CONFIG = {
  info:    { icon: Globe,        color: 'text-info',    label: 'INFO' },
  search:  { icon: Search,      color: 'text-info',    label: 'SEARCH' },
  found:   { icon: CheckCircle,  color: 'text-success', label: 'FOUND' },
  skip:    { icon: SkipForward,  color: 'text-fg-muted', label: 'SKIP' },
  dedup:   { icon: Copy,         color: 'text-warning', label: 'DUP' },
  llm:     { icon: Sparkles,     color: 'text-accent',  label: 'LLM' },
  extract: { icon: FileText,     color: 'text-info',    label: 'EXTRACT' },
  saved:   { icon: Database,     color: 'text-success', label: 'SAVED' },
  error:   { icon: AlertCircle,  color: 'text-danger',  label: 'ERROR' },
  done:    { icon: Trophy,       color: 'text-success', label: 'DONE' },
  query_done: { icon: Check,    color: 'text-fg-secondary', label: 'QDONE' },
  profile_email: { icon: AtSign, color: 'text-success', label: 'EMAIL' },
  profile_error: { icon: AlertCircle, color: 'text-fg-muted', label: 'PROF' },
  deep_extract:  { icon: FileText, color: 'text-accent', label: 'DEEP' },
  career_page:   { icon: Globe, color: 'text-info', label: 'CAREER' },
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d)) return ''
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatEventMessage(event) {
  const t = event.type
  if (t === 'search') return `Searching: ${event.query || '...'} (${event.index || 0}/${event.total || 0})`
  if (t === 'found') return `#${event.sno || '?'} ${event.author || event.name || ''} | ${event.role || ''} @ ${event.company || ''} | ${event.domain || ''} | ${event.email || 'no email'}`
  if (t === 'skip') return `SKIP: ${event.author || event.name || ''} | ${event.role || ''} | ${event.reason || 'Not relevant'}`
  if (t === 'dedup') return `DUP: ${event.message || 'Already in database'}`
  if (t === 'llm') return `LLM extracting role & company...`
  if (t === 'extract') return `Extracted ${event.count || '?'} raw posts from page`
  if (t === 'saved') return `Saved ${event.count || '?'} posts (${event.inserted || 0} new, ${event.skipped || 0} duplicates)`
  if (t === 'error') return `${event.message || 'Unknown error'}`
  if (t === 'done') return `Done! ${event.total || 0} posts from ${event.queries_searched || 0} queries`
  if (t === 'profile_email') return `Profile email found: ${event.email || '?'}`
  if (t === 'profile_error') return `Profile visit failed: ${event.error || '?'}`
  return event.message || JSON.stringify(event)
}

/* ─── Step indicator ─── */
function StepIndicator({ steps, currentStep }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {steps.map((step, i) => {
        const isCompleted = i < currentStep
        const isActive = i === currentStep
        const isFuture = i > currentStep
        return (
          <div key={i} className="flex items-center">
            {i > 0 && (
              <div className={`w-12 sm:w-20 h-0.5 transition-colors duration-500 ${isCompleted ? 'bg-success' : 'bg-border'}`} />
            )}
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={`
                  flex items-center justify-center rounded-full transition-all duration-500 font-semibold text-sm
                  ${isCompleted
                    ? 'w-9 h-9 bg-success text-white'
                    : isActive
                      ? 'w-10 h-10 bg-accent text-white ring-4 ring-accent/20'
                      : 'w-9 h-9 bg-bg-tertiary text-fg-muted border border-border'
                  }
                `}
              >
                {isCompleted ? <Check size={16} strokeWidth={3} /> : i + 1}
              </div>
              <span
                className={`text-xs font-medium whitespace-nowrap transition-colors duration-300 ${
                  isCompleted ? 'text-success' : isActive ? 'text-accent' : 'text-fg-muted'
                }`}
              >
                {step}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ─── Main Scraper component ─── */
export default function Scraper() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const pollRef = useRef(null)
  const browserPollRef = useRef(null)
  const lastLogCountsRef = useRef({})
  const logEndRefs = useRef({})

  // Step management
  const [currentStep, setCurrentStep] = useState(0)

  // Step 1: Browser/LinkedIn connection
  const [browserRunning, setBrowserRunning] = useState(false)
  const [loggedIn, setLoggedIn] = useState(false)
  const [actionLoading, setActionLoading] = useState(null)
  const [browserChecking, setBrowserChecking] = useState(true)

  // Step 2: Config
  const [maxPosts, setMaxPosts] = useState(200)
  const [sources, setSources] = useState({ linkedin: true })
  const [sourceGroups, setSourceGroups] = useState(null)
  const [sourceCount, setSourceCount] = useState(0)

  // Step 3: Scraping — per-source state
  const [scraping, setScraping] = useState(false)
  const [scraperStatus, setScraperStatus] = useState('idle')
  const [sourcesState, setSourcesState] = useState({})  // { linkedin: { status, log, progress }, ... }

  // Step 4: Results
  const [results, setResults] = useState(null)

  // ATS Scanner
  const [atsOpen, setAtsOpen] = useState(false)
  const [atsScanning, setAtsScanning] = useState(false)
  const [atsResults, setAtsResults] = useState(null)
  const [atsCompanyCount, setAtsCompanyCount] = useState(null)

  const steps = ['Connect', 'Configure', 'Scraping', 'Results']

  /* ─── Check browser status on mount + poll ─── */
  const checkBrowser = useCallback(async () => {
    try {
      const data = await api.getBrowserStatus()
      const running = data?.running ?? false
      const logged = data?.logged_in ?? false
      setBrowserRunning(running)
      setLoggedIn(logged)
      if (running && logged && currentStep === 0) {
        setCurrentStep(1)
      }
    } catch {
      setBrowserRunning(false)
      setLoggedIn(false)
    } finally {
      setBrowserChecking(false)
    }
  }, [currentStep])

  useEffect(() => {
    checkBrowser()
    browserPollRef.current = setInterval(checkBrowser, 3000)
    return () => clearInterval(browserPollRef.current)
  }, [checkBrowser])

  /* ─── Load source configs from API ─── */
  useEffect(() => {
    async function loadSources() {
      try {
        const data = await api.getScraperSources()
        setSourceGroups(data.groups || [])
        setSourceCount(data.total || 0)
        // Init sources state from API response
        const init = {}
        for (const grp of (data.groups || [])) {
          for (const src of grp.sources) {
            init[src.key] = src.key === 'linkedin'  // Only linkedin on by default
          }
        }
        setSources(prev => ({ ...init, ...prev }))
      } catch (e) {
        /* silent */
      }
    }
    loadSources()
  }, [])

  /* ─── Also check if scraper is already running (page reload scenario) ─── */
  useEffect(() => {
    async function checkScraper() {
      try {
        const data = await api.getScraperStatus()
        if (data.running) {
          setScraping(true)
          setScraperStatus('running')
          setSourcesState(data.sources || {})
          setCurrentStep(2)
        } else if (data.status === 'done' && data.sources && Object.keys(data.sources).length > 0) {
          setSourcesState(data.sources || {})
          setResults(buildResultsFromSources(data.sources))
          setCurrentStep(3)
        }
      } catch { /* ignore */ }
    }
    checkScraper()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  /* ─── Poll scraper status while scraping ─── */
  useEffect(() => {
    if (!scraping) {
      clearInterval(pollRef.current)
      return
    }

    async function poll() {
      try {
        const data = await api.getScraperStatus()
        setScraperStatus(data.status)

        // Update per-source state — only update sources with new log entries
        if (data.sources) {
          setSourcesState(prev => {
            const next = { ...prev }
            for (const [name, srcState] of Object.entries(data.sources)) {
              const prevCount = lastLogCountsRef.current[name] || 0
              if (srcState.log_count !== prevCount || !prev[name]) {
                next[name] = srcState
                lastLogCountsRef.current[name] = srcState.log_count
              }
            }
            return next
          })
        }

        if (!data.running) {
          setScraping(false)
          if (data.status === 'done') {
            setSourcesState(data.sources || {})
            setResults(buildResultsFromSources(data.sources || {}))
            setCurrentStep(3)
          } else if (data.status === 'error') {
            toast({ type: 'error', title: 'Scraping failed', description: 'Check the logs for details.' })
          }
        }
      } catch { /* ignore */ }
    }

    pollRef.current = setInterval(poll, 1500)
    return () => clearInterval(pollRef.current)
  }, [scraping, toast])

  /* ─── Auto-scroll each source terminal (internal scroll only, never moves the page) ─── */
  useEffect(() => {
    for (const ref of Object.values(logEndRefs.current)) {
      if (!ref) continue
      const container = ref.parentElement
      if (!container) continue
      // Only auto-scroll if user is near the bottom (not manually scrolled up)
      const distFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
      if (distFromBottom < 80) {
        container.scrollTop = container.scrollHeight
      }
    }
  }, [sourcesState])

  /* ─── Helpers ─── */
  function buildResultsFromSources(sources) {
    let total = 0, newSaved = 0, duplicates = 0, withEmail = 0, hiringPosts = 0, queriesSearched = 0
    for (const srcState of Object.values(sources)) {
      const log = srcState.log || []
      const doneEvent = [...log].reverse().find(e => e.type === 'done')
      const savedEvent = [...log].reverse().find(e => e.type === 'saved')
      const foundEvents = log.filter(e => e.type === 'found')
      total += doneEvent?.total ?? foundEvents.length
      newSaved += savedEvent?.inserted ?? 0
      duplicates += savedEvent?.skipped ?? 0
      withEmail += foundEvents.filter(e => e.email && e.email !== 'no email' && e.email !== '').length
      hiringPosts += foundEvents.filter(e => e.domain === 'High' || e.domain === 'Medium').length
      queriesSearched += doneEvent?.queries_searched ?? 0
    }
    return { total, newSaved, duplicates, withEmail, hiringPosts, queriesSearched }
  }

  /* ─── Actions ─── */
  async function handleBrowserAction(action, label) {
    setActionLoading(label)
    try {
      await action()
      await checkBrowser()
      if (label === 'verify') {
        const status = await api.getBrowserStatus()
        if (status?.logged_in) {
          toast({ type: 'success', title: 'Connected!', description: 'LinkedIn session verified successfully.' })
          setLoggedIn(true)
          setCurrentStep(1)
        } else {
          toast({ type: 'warning', title: 'Not logged in', description: 'Please log in to LinkedIn in the browser window first.' })
        }
      }
    } catch (e) {
      toast({ type: 'error', title: 'Action failed', description: e.message })
    } finally {
      setActionLoading(null)
    }
  }

  async function handleStartScraping() {
    try {
      const activeSources = Object.entries(sources).filter(([, v]) => v).map(([k]) => k)
      if (activeSources.length === 0) {
        toast({ type: 'warning', title: 'No sources selected', description: 'Select at least one source to scrape.' })
        return
      }
      await api.startScraper({ max_posts: maxPosts, sources: activeSources })
      setScraping(true)
      setScraperStatus('running')
      // Don't wipe existing sourcesState — new sources merge in from polling
      if (!scraping) {
        setSourcesState({})
        setResults(null)
        lastLogCountsRef.current = {}
      }
      setCurrentStep(2)
      const sourceNames = activeSources.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(', ')
      toast({ type: 'success', title: 'Scraping started', description: `Running ${sourceNames} in parallel...` })
    } catch (e) {
      toast({ type: 'error', title: 'Could not start scraper', description: e.message })
    }
  }

  async function handleStopScraping() {
    try {
      await api.stopScraper()
      setScraping(false)
      toast({ type: 'info', title: 'Scraping stopped' })
    } catch (e) {
      toast({ type: 'error', title: 'Could not stop scraper', description: e.message })
    }
  }

  function handleReset() {
    setCurrentStep(1)
    setScraping(false)
    setScraperStatus('idle')
    setSourcesState({})
    setResults(null)
  }

  /* ─── Fetch ATS company count when section opens ─── */
  useEffect(() => {
    if (!atsOpen) return
    api.atsCompanies()
      .then(data => setAtsCompanyCount(Array.isArray(data) ? data.length : data?.count ?? 0))
      .catch(() => {})
  }, [atsOpen])

  async function handleAtsScan() {
    setAtsScanning(true)
    setAtsResults(null)
    try {
      const data = await api.atsScan()
      setAtsResults(data)
      toast({ type: 'success', title: 'ATS Scan complete', description: `${data?.jobs_found ?? 0} jobs found` })
    } catch (e) {
      toast({ type: 'error', title: 'ATS Scan failed', description: e.message })
    } finally {
      setAtsScanning(false)
    }
  }

  const isConnected = browserRunning && loggedIn
  const activeSources = Object.keys(sourcesState)

  return (
    <div className="min-h-screen bg-bg-primary p-6 md:p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-fg-primary">LinkedIn Scraper</h1>
        <p className="text-sm text-fg-muted mt-1">
          Connect to LinkedIn, configure scraping parameters, and extract hiring posts automatically.
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex justify-center">
        <StepIndicator steps={steps} currentStep={currentStep} />
      </div>

      <div className="max-w-4xl mx-auto space-y-6">

        {/* ────────────────────────────────────────── */}
        {/* STEP 1: Connect to LinkedIn               */}
        {/* ────────────────────────────────────────── */}
        <div
          className={`bg-bg-secondary border rounded-2xl overflow-hidden transition-all duration-500 ${
            currentStep === 0 ? 'border-accent/40 shadow-lg shadow-accent/5' : 'border-border'
          }`}
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isConnected ? 'bg-success-bg' : 'bg-accent-bg'}`}>
                <Globe size={16} className={isConnected ? 'text-success' : 'text-accent'} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-fg-primary">Connect to LinkedIn</h2>
                <p className="text-xs text-fg-muted">Launch browser and sign in to your LinkedIn account</p>
              </div>
            </div>
            {browserChecking ? (
              <Loader2 size={16} className="animate-spin text-fg-muted" />
            ) : isConnected ? (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-success-bg text-success text-xs font-medium border border-success/30">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-danger-bg text-danger text-xs font-medium border border-danger/30">
                <span className="w-1.5 h-1.5 rounded-full bg-danger" />
                Not Connected
              </span>
            )}
          </div>

          {currentStep === 0 && (
            <div className="px-5 py-5">
              {/* Status row */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary border border-border mb-4">
                <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${browserRunning ? 'bg-success animate-pulse' : 'bg-fg-muted'}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-fg-primary text-sm font-medium">
                    {browserRunning ? 'Browser is running' : 'Browser is stopped'}
                  </p>
                  <p className="text-fg-muted text-xs mt-0.5">
                    {browserRunning
                      ? loggedIn
                        ? 'LinkedIn session active — ready to scrape'
                        : 'Running but not logged in to LinkedIn'
                      : 'Start the browser to begin'
                    }
                  </p>
                </div>
                {browserRunning && (
                  <div className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${
                    loggedIn ? 'bg-success-bg text-success border border-success/30' : 'bg-warning-bg text-warning border border-warning/30'
                  }`}>
                    {loggedIn ? <CheckCircle size={11} /> : <AlertCircle size={11} />}
                    {loggedIn ? 'Logged in' : 'Not logged in'}
                  </div>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                {!browserRunning ? (
                  <button
                    onClick={() => handleBrowserAction(api.startBrowser, 'start')}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-xl transition-colors disabled:opacity-60"
                  >
                    {actionLoading === 'start' ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                    Launch Browser
                  </button>
                ) : (
                  <>
                    {!loggedIn && (
                      <button
                        onClick={() => handleBrowserAction(api.openLogin, 'login')}
                        disabled={actionLoading !== null}
                        className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-xl transition-colors disabled:opacity-60"
                      >
                        {actionLoading === 'login' ? <Loader2 size={15} className="animate-spin" /> : <LogIn size={15} />}
                        Open LinkedIn Login
                      </button>
                    )}
                    {!loggedIn && (
                      <button
                        onClick={() => handleBrowserAction(api.checkLogin, 'verify')}
                        disabled={actionLoading !== null}
                        className="flex items-center gap-2 px-5 py-2.5 bg-bg-tertiary border border-border text-fg-primary text-sm font-medium rounded-xl hover:bg-border transition-colors disabled:opacity-60"
                      >
                        {actionLoading === 'verify' ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
                        Verify Connection
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ────────────────────────────────────────── */}
        {/* STEP 2: Configure & Start Scraping         */}
        {/* ────────────────────────────────────────── */}
        <div
          className={`bg-bg-secondary border rounded-2xl overflow-hidden transition-all duration-500 ${
            currentStep === 1 ? 'border-accent/40 shadow-lg shadow-accent/5' : 'border-border'
          } ${currentStep < 1 ? 'opacity-50' : ''}`}
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
                <Search size={16} className="text-accent" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-fg-primary">Configure & Start Scraping</h2>
                <p className="text-xs text-fg-muted">Set parameters and begin extraction</p>
              </div>
            </div>
            {currentStep < 1 && (
              <span className="text-xs text-fg-muted">Connect to LinkedIn first</span>
            )}
          </div>

          {currentStep === 1 && (
            <div className="px-5 py-5 space-y-5">
              {/* Max posts input */}
              <div>
                <label className="text-fg-muted text-xs font-medium uppercase tracking-wider mb-2 block">
                  Max posts to scrape
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min={10}
                    max={2000}
                    step={10}
                    value={maxPosts}
                    onChange={(e) => setMaxPosts(parseInt(e.target.value))}
                    className="flex-1 accent-[hsl(var(--accent))] h-2 rounded-full bg-bg-tertiary cursor-pointer"
                  />
                  <input
                    type="number"
                    min={10}
                    max={2000}
                    value={maxPosts}
                    onChange={(e) => setMaxPosts(Math.max(10, Math.min(2000, parseInt(e.target.value) || 10)))}
                    className="w-20 bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-fg-primary text-sm font-mono text-center focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
              </div>

              {/* Source selection */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-fg-muted text-xs font-medium uppercase tracking-wider">
                    Sources to scrape
                    {sourceCount > 0 && <span className="ml-1.5 px-1.5 py-0.5 bg-accent/20 text-accent rounded text-[10px] font-bold">{sourceCount}</span>}
                    <span className="ml-1.5 text-fg-muted/50 font-normal normal-case">
                      ({Object.values(sources).filter(Boolean).length} selected)
                    </span>
                  </label>
                  <button
                    onClick={() => {
                      const allOn = Object.values(sources).filter(Boolean).length > Object.keys(sources).length / 2
                      setSources(prev => {
                        const next = {}
                        Object.keys(prev).forEach(k => next[k] = !allOn)
                        return next
                      })
                    }}
                    className="text-xs font-medium text-accent hover:text-accent/80 transition-colors"
                  >
                    {Object.values(sources).filter(Boolean).length > Object.keys(sources).length / 2 ? 'Deselect All' : 'Select All'}
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {sourceGroups ? sourceGroups.map(({ key: groupKey, label: groupLabel, icon, sources: groupSources }) => (
                    <div key={groupKey} className="col-span-2 sm:col-span-3">
                      <div className="flex items-center justify-between mb-1.5 mt-2">
                        <span className="text-xs font-bold text-fg-muted uppercase tracking-wider">
                          {icon} {groupLabel} <span className="text-fg-muted/50 font-normal">({groupSources.length})</span>
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            const keys = groupSources.map(s => s.key)
                            const allOn = keys.every(k => sources[k])
                            setSources(prev => {
                              const next = { ...prev }
                              keys.forEach(k => next[k] = !allOn)
                              return next
                            })
                          }}
                          className="text-[10px] text-accent hover:underline"
                        >
                          {groupSources.every(s => sources[s.key]) ? 'Deselect' : 'Select All'}
                        </button>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                        {groupSources.map(({ key, label }) => (
                          <button
                            key={key}
                            onClick={() => setSources(prev => ({ ...prev, [key]: !prev[key] }))}
                            className={`flex items-start gap-2 p-2 rounded-lg border text-left transition-all ${
                              sources[key]
                                ? 'border-accent/50 bg-accent-bg/50'
                                : 'border-border bg-bg-tertiary hover:border-border-light'
                            }`}
                          >
                            <div className={`mt-0.5 w-3 h-3 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                              sources[key] ? 'border-accent bg-accent' : 'border-fg-muted'
                            }`}>
                              {sources[key] && <span className="text-white text-[8px] font-bold">✓</span>}
                            </div>
                            <p className={`text-[11px] font-medium leading-tight ${sources[key] ? 'text-fg-primary' : 'text-fg-secondary'}`}>{label}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )) : <div className="col-span-3 text-center py-4 text-fg-muted text-sm">Loading sources...</div>}
                </div>
              </div>

              {/* Info text */}
              <div className="flex items-start gap-3 p-3 rounded-xl bg-accent-bg/50 border border-accent/20">
                <Sparkles size={16} className="text-accent mt-0.5 flex-shrink-0" />
                <p className="text-xs text-fg-secondary leading-relaxed">
                  Each post is analyzed by LLM for relevance, role, company, and contact info.
                  Only healthcare AI, GenAI &amp; agentic AI roles are kept.
                </p>
              </div>

              {/* Start button */}
              <button
                onClick={handleStartScraping}
                disabled={!isConnected || scraping}
                className="w-full flex items-center justify-center gap-2.5 py-3.5 bg-gradient-to-r from-accent to-accent/80 hover:from-accent/90 hover:to-accent/70 text-white text-sm font-semibold rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-accent/20"
              >
                <Play size={16} />
                Start Scraping
              </button>
            </div>
          )}
        </div>

        {/* ────────────────────────────────────────── */}
        {/* STEP 3: Parallel Extraction Terminals       */}
        {/* ────────────────────────────────────────── */}
        {(currentStep >= 2 || (currentStep === 1 && scraping)) && (
          <div className="space-y-4">
            {/* Header with stop button */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
                  <Database size={16} className="text-accent" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-fg-primary">
                    {scraping ? 'Scraping in parallel...' : scraperStatus === 'done' ? 'All scrapers complete' : 'Scraping stopped'}
                  </h2>
                  <p className="text-xs text-fg-muted">
                    {activeSources.length} source{activeSources.length !== 1 ? 's' : ''} running in parallel
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {scraping && (
                  <>
                    <button
                      onClick={() => setCurrentStep(1)}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-accent/10 hover:bg-accent/20 text-accent text-xs font-medium rounded-lg transition-colors"
                    >
                      <Play size={13} />
                      Add Sources
                    </button>
                    <button
                      onClick={handleStopScraping}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-danger hover:bg-danger/90 text-white text-xs font-medium rounded-lg transition-colors"
                    >
                      <Square size={13} />
                      Stop All
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* 2x2 Terminal Grid */}
            <div className={`grid gap-3 ${activeSources.length === 1 ? 'grid-cols-1' : activeSources.length <= 2 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1 md:grid-cols-2'}`}>
              {activeSources.map(sourceName => {
                const srcState = sourcesState[sourceName] || { status: 'waiting', log: [], progress: { current_query: '', query_index: 0, total_queries: 0, posts_found: 0 } }
                const srcLog = srcState.log || []
                const srcProgress = srcState.progress || {}
                const srcPct = srcProgress.total_queries > 0
                  ? Math.round((srcProgress.query_index / srcProgress.total_queries) * 100)
                  : 0
                const srcStatus = srcState.status || 'waiting'

                const SOURCE_LABELS = { linkedin: 'LinkedIn Search', feed: 'LinkedIn Feed', hashtags: 'Hashtag Feeds', enricher: 'Email Enricher', deepfetch: 'Deep Fetch', career_links: 'Career Links', google: 'DuckDuckGo', wellfound: 'Wellfound', yc: 'YC Jobs', remoteok: 'RemoteOK', himalayas: 'Himalayas', hn: 'HN Hiring', remotive: 'Remotive', wwr_rss: 'WWR RSS', workingnomads: 'Working Nomads', greenhouse: 'Greenhouse', lever: 'Lever', ashby: 'Ashby', jobspy: 'JobSpy', indeed: 'Indeed', naukri: 'Naukri', arcdev: 'Arc.dev', weworkremotely: 'WeWorkRemotely', japandev: 'JapanDev', euremotejobs: 'EU Remote', bayt: 'Bayt', remoteai: 'RemoteAI' }
                const label = SOURCE_LABELS[sourceName] || sourceName

                const statusColor = srcStatus === 'done' ? 'text-success' : srcStatus === 'error' ? 'text-danger' : srcStatus === 'running' ? 'text-accent' : 'text-fg-muted'
                const borderColor = srcStatus === 'done' ? 'border-success/30' : srcStatus === 'error' ? 'border-danger/30' : srcStatus === 'running' ? 'border-accent/40' : 'border-border'
                const dotColor = srcStatus === 'done' ? 'bg-success' : srcStatus === 'error' ? 'bg-danger' : srcStatus === 'running' ? 'bg-accent animate-pulse' : 'bg-fg-muted'

                return (
                  <div key={sourceName} className={`bg-bg-secondary border ${borderColor} rounded-xl overflow-hidden transition-all duration-500 shadow-sm`}>
                    {/* Terminal header */}
                    <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-bg-tertiary/50">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
                        <span className="text-xs font-semibold text-fg-primary">{label}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {srcProgress.posts_found > 0 && (
                          <span className="text-[10px] font-medium text-success bg-success-bg px-1.5 py-0.5 rounded-full">
                            {srcProgress.posts_found} found
                          </span>
                        )}
                        <span className={`text-[10px] font-medium capitalize ${statusColor}`}>
                          {srcStatus === 'running' && srcPct > 0 ? `${srcPct}%` : srcStatus}
                        </span>
                      </div>
                    </div>

                    {/* Mini progress bar */}
                    {srcStatus === 'running' && srcPct > 0 && (
                      <div className="w-full h-1 bg-bg-tertiary">
                        <div
                          className="h-full bg-accent/70 transition-all duration-700 ease-out"
                          style={{ width: `${srcPct}%` }}
                        />
                      </div>
                    )}

                    {/* Terminal log */}
                    <div
                      className="h-[250px] overflow-y-auto px-3 py-2 font-mono text-[11px] leading-relaxed bg-[hsl(var(--bg-primary))]"
                      style={{
                        scrollbarWidth: 'thin',
                        scrollbarColor: 'hsl(var(--border)) transparent',
                      }}
                    >
                      {srcLog.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-fg-muted">
                          <div className="flex items-center gap-2 text-xs">
                            {srcStatus === 'waiting' ? (
                              <>
                                <Loader2 size={12} className="animate-spin" />
                                Initializing...
                              </>
                            ) : srcStatus === 'running' ? (
                              <>
                                <Loader2 size={12} className="animate-spin" />
                                Waiting for events...
                              </>
                            ) : (
                              'No events'
                            )}
                          </div>
                        </div>
                      ) : (
                        srcLog.map((event, i) => {
                          const config = EVENT_CONFIG[event.type] || { icon: FileText, color: 'text-fg-muted', label: event.type?.toUpperCase() || '?' }
                          const Icon = config.icon
                          const isBold = event.type === 'saved' || event.type === 'done'
                          return (
                            <div
                              key={i}
                              className={`flex items-start gap-1.5 py-0.5 ${
                                event.type === 'error' ? 'bg-danger-bg/30 -mx-3 px-3 rounded' : ''
                              }`}
                            >
                              <span className="text-fg-muted flex-shrink-0 w-14 text-right">{formatTime(event.timestamp)}</span>
                              <Icon size={11} className={`${config.color} flex-shrink-0 mt-0.5`} />
                              <span className={`${config.color} ${isBold ? 'font-semibold' : ''} break-words min-w-0`}>
                                {formatEventMessage(event)}
                              </span>
                            </div>
                          )
                        })
                      )}
                      <div ref={el => { logEndRefs.current[sourceName] = el }} />
                    </div>

                    {/* Terminal footer with current query */}
                    {srcProgress.current_query && srcStatus === 'running' && (
                      <div className="px-3 py-1.5 border-t border-border bg-bg-tertiary/30">
                        <p className="text-[10px] text-fg-muted truncate">
                          <span className="text-fg-secondary font-medium">Q{srcProgress.query_index}/{srcProgress.total_queries}:</span> {srcProgress.current_query}
                        </p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ────────────────────────────────────────── */}
        {/* STEP 4: Results Summary                    */}
        {/* ────────────────────────────────────────── */}
        {currentStep >= 3 && results && (
          <div className="bg-bg-secondary border border-success/30 rounded-2xl overflow-hidden shadow-lg shadow-success/5 transition-all duration-500">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-success-bg flex items-center justify-center">
                  <Trophy size={16} className="text-success" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-fg-primary">Scraping Complete</h2>
                  <p className="text-xs text-fg-muted">Here is a summary of your results</p>
                </div>
              </div>
            </div>

            <div className="px-5 py-5 space-y-5">
              {/* Stat cards */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { label: 'Total Found', value: results.total, icon: Search, color: 'text-accent' },
                  { label: 'New Saved', value: results.newSaved, icon: Database, color: 'text-success' },
                  { label: 'Duplicates', value: results.duplicates, icon: Copy, color: 'text-warning' },
                  { label: 'With Email', value: results.withEmail, icon: AtSign, color: 'text-info' },
                  { label: 'Hiring Posts', value: results.hiringPosts, icon: TrendingUp, color: 'text-accent' },
                ].map(({ label, value, icon: Icon, color }) => (
                  <div key={label} className="bg-bg-tertiary border border-border rounded-xl p-4 text-center">
                    <Icon size={18} className={`${color} mx-auto mb-2`} />
                    <p className="text-2xl font-bold font-mono text-fg-primary">{value}</p>
                    <p className="text-xs text-fg-muted mt-1">{label}</p>
                  </div>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={() => navigate('/posts')}
                  className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-xl transition-colors"
                >
                  <Database size={15} />
                  View All Posts
                  <ArrowRight size={14} />
                </button>
                <button
                  onClick={() => navigate('/email')}
                  className="flex items-center gap-2 px-5 py-2.5 bg-bg-tertiary border border-border text-fg-primary text-sm font-medium rounded-xl hover:bg-border transition-colors"
                >
                  <Mail size={15} />
                  Email Outreach
                </button>
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 px-5 py-2.5 bg-bg-tertiary border border-border text-fg-primary text-sm font-medium rounded-xl hover:bg-border transition-colors"
                >
                  <RotateCcw size={15} />
                  Scrape More
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ────────────────────────────────────────── */}
        {/* ATS Job Board Scanner                      */}
        {/* ────────────────────────────────────────── */}
        <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden transition-all duration-500">
          {/* Collapsible header */}
          <button
            onClick={() => setAtsOpen(prev => !prev)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-bg-tertiary/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center">
                <Building size={16} className="text-accent" />
              </div>
              <div className="text-left">
                <h2 className="text-sm font-semibold text-fg-primary">ATS Job Board Scanner</h2>
                <p className="text-xs text-fg-muted">Scan Greenhouse, Ashby &amp; Lever APIs for healthcare AI jobs</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {atsCompanyCount !== null && (
                <span className="text-xs text-fg-muted font-medium">
                  {atsCompanyCount} companies tracked
                </span>
              )}
              <ChevronDown
                size={16}
                className={`text-fg-muted transition-transform duration-300 ${atsOpen ? 'rotate-180' : ''}`}
              />
            </div>
          </button>

          {/* Collapsible body */}
          {atsOpen && (
            <div className="px-5 py-5 border-t border-border space-y-5">
              {/* Scan button */}
              <button
                onClick={handleAtsScan}
                disabled={atsScanning}
                className="flex items-center justify-center gap-2.5 px-5 py-2.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-xl transition-colors disabled:opacity-60"
              >
                {atsScanning ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
                {atsScanning ? 'Scanning...' : 'Scan Now'}
              </button>

              {/* Results summary */}
              {atsResults && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-success-bg/50 border border-success/20">
                    <CheckCircle size={16} className="text-success flex-shrink-0" />
                    <p className="text-sm text-fg-primary">
                      <span className="font-semibold">{atsResults.jobs_found ?? 0}</span> jobs found
                      {' · '}
                      <span className="font-semibold">{atsResults.inserted ?? 0}</span> inserted
                      {' · '}
                      <span className="font-semibold">{atsResults.duplicates ?? 0}</span> duplicates
                    </p>
                  </div>

                  {/* Jobs table */}
                  {atsResults.jobs && atsResults.jobs.length > 0 && (
                    <div className="border border-border rounded-xl overflow-hidden">
                      <div className="overflow-x-auto max-h-[400px] overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'hsl(var(--border)) transparent' }}>
                        <table className="w-full text-sm">
                          <thead className="sticky top-0 bg-bg-tertiary border-b border-border">
                            <tr>
                              <th className="text-left px-4 py-2.5 text-xs font-medium text-fg-muted uppercase tracking-wider">Company</th>
                              <th className="text-left px-4 py-2.5 text-xs font-medium text-fg-muted uppercase tracking-wider">Role</th>
                              <th className="text-left px-4 py-2.5 text-xs font-medium text-fg-muted uppercase tracking-wider">Location</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {atsResults.jobs.slice(0, 50).map((job, i) => (
                              <tr key={i} className="hover:bg-bg-tertiary/50 transition-colors">
                                <td className="px-4 py-2.5 text-fg-primary font-medium whitespace-nowrap">
                                  <div className="flex items-center gap-2">
                                    <Building size={13} className="text-fg-muted flex-shrink-0" />
                                    {job.company || '—'}
                                  </div>
                                </td>
                                <td className="px-4 py-2.5 text-fg-secondary">{job.role || job.title || '—'}</td>
                                <td className="px-4 py-2.5 text-fg-muted whitespace-nowrap">
                                  <div className="flex items-center gap-1.5">
                                    <MapPin size={12} className="flex-shrink-0" />
                                    {job.location || '—'}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {atsResults.jobs.length > 50 && (
                        <div className="px-4 py-2 bg-bg-tertiary/50 border-t border-border">
                          <p className="text-xs text-fg-muted">Showing 50 of {atsResults.jobs.length} jobs</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
