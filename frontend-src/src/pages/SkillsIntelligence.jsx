import { useState, useEffect, useCallback, useRef } from 'react'
import {
  BarChart3, Target, TrendingUp, Newspaper, Brain, RefreshCw, Loader2,
  Play, CheckCircle, AlertCircle, ExternalLink, Flame, ArrowUpRight,
  GraduationCap, Briefcase, Filter,
} from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'
import PageTabs, { useTabState } from '../components/PageTabs'

const TABS = [
  { key: 'demand', label: 'Skills Demand', icon: BarChart3 },
  { key: 'gaps', label: 'Resume Gaps', icon: Target },
  { key: 'trending', label: 'Trending Now', icon: TrendingUp },
  { key: 'news', label: 'Industry News', icon: Newspaper },
]

const CATEGORIES = ['All', 'Languages', 'AI_ML', 'Frameworks', 'Cloud', 'Databases', 'DevOps', 'Domain']

function StatCard({ icon: Icon, label, value, sub, color = 'text-accent' }) {
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
          color === 'text-accent' ? 'bg-accent-bg' :
          color === 'text-success' ? 'bg-success-bg' :
          color === 'text-warning' ? 'bg-warning-bg' :
          'bg-danger-bg'
        }`}>
          <Icon size={18} className={color} />
        </div>
        <div>
          <p className="text-xs text-fg-muted">{label}</p>
          <p className="text-xl font-bold text-fg-primary font-mono">{value}</p>
          {sub && <p className="text-xs text-fg-muted">{sub}</p>}
        </div>
      </div>
    </div>
  )
}

// ─── Tab 1: Skills Demand ──────────────────────────────────────────────────

function SkillsDemandTab() {
  const { toast } = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [progress, setProgress] = useState(null)
  const [category, setCategory] = useState('All')

  const fetchData = useCallback(async () => {
    try {
      const d = await api.getSkillsDashboard()
      setData(d)
    } catch (e) { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const pollRef = useRef(null)

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleAnalyze = async (useLlm = false) => {
    setAnalyzing(true)
    try {
      await api.analyzeSkills({ use_llm: useLlm, llm_sample_size: 100 })
      // Poll progress
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        try {
          const st = await api.getAnalysisStatus()
          setProgress(st)
          if (!st.running) {
            clearInterval(pollRef.current)
            pollRef.current = null
            setAnalyzing(false)
            setProgress(null)
            fetchData()
            toast({ type: 'success', title: 'Skills analysis complete!' })
          }
        } catch { clearInterval(pollRef.current); pollRef.current = null; setAnalyzing(false) }
      }, 2000)
    } catch (e) {
      toast({ type: 'error', title: e.message })
      setAnalyzing(false)
    }
  }

  if (loading) return <LoadingSkeleton />

  const skills = data?.has_data ? data.top_skills : []
  const filtered = category === 'All' ? skills : skills.filter(s => s.category === category)
  const eduStats = data?.education_stats || {}
  const expDist = data?.experience_distribution || {}

  return (
    <div className="space-y-6 p-6">
      {/* Analyze button + progress */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => handleAnalyze(false)}
          disabled={analyzing}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-fg-inverse text-sm font-medium hover:bg-accent-dim transition-colors disabled:opacity-50"
        >
          {analyzing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Analyze Jobs (Regex)
        </button>
        <button
          onClick={() => handleAnalyze(true)}
          disabled={analyzing}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-bg-tertiary text-fg-primary text-sm font-medium hover:bg-bg-secondary transition-colors disabled:opacity-50 border border-border"
        >
          {analyzing ? <Loader2 size={14} className="animate-spin" /> : <Brain size={14} />}
          Deep Analyze (+ AI)
        </button>
        {data?.last_analysis && (
          <span className="text-xs text-fg-muted">Last: {new Date(data.last_analysis).toLocaleDateString()}</span>
        )}
      </div>

      {/* Progress bar */}
      {analyzing && progress && (
        <div className="bg-accent-bg border border-accent/20 rounded-xl px-4 py-3 flex items-center gap-3">
          <Loader2 size={16} className="text-accent animate-spin" />
          <div className="flex-1">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-fg-primary font-medium">
                {progress.phase === 'regex_scan' ? 'Scanning jobs...' :
                 progress.phase === 'llm_enrichment' ? 'AI deep analysis...' :
                 progress.phase === 'aggregation' ? 'Computing stats...' : 'Starting...'}
              </span>
              <span className="text-fg-muted">{progress.processed}/{progress.total}</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
              <div className="h-full rounded-full bg-accent transition-all"
                   style={{ width: `${progress.total ? (progress.processed / progress.total) * 100 : 0}%` }} />
            </div>
          </div>
        </div>
      )}

      {!data?.has_data && !analyzing ? (
        <EmptyState
          icon={BarChart3}
          title="No analysis data yet"
          description='Click "Analyze Jobs" to scan your saved jobs and extract skill demands.'
        />
      ) : data?.has_data && (
        <>
          {/* Category filter */}
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  category === cat
                    ? 'bg-accent text-fg-inverse'
                    : 'bg-bg-tertiary text-fg-muted hover:text-fg-primary'
                }`}
              >
                {cat === 'AI_ML' ? 'AI/ML' : cat}
              </button>
            ))}
          </div>

          {/* Skills list */}
          <div className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-fg-primary mb-4">
              Top Skills ({filtered.length})
            </h3>
            {filtered.slice(0, 30).map((s, i) => (
              <SkillBar key={s.skill_name} rank={i + 1} skill={s} />
            ))}
          </div>

          {/* Education & Experience */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <EducationCard stats={eduStats} />
            <ExperienceCard dist={expDist} />
          </div>
        </>
      )}
    </div>
  )
}

function SkillBar({ rank, skill }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-mono text-fg-muted w-6 shrink-0 text-right">{rank}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-sm text-fg-primary font-medium">{skill.skill_name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-tertiary text-fg-muted">
              {skill.category === 'AI_ML' ? 'AI/ML' : skill.category}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {skill.required_count > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-danger-bg text-danger">
                {skill.required_count} req
              </span>
            )}
            <span className="text-xs font-mono font-bold text-accent">{skill.percentage}%</span>
          </div>
        </div>
        <div className="w-full h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
          <div className="h-full rounded-full bg-accent transition-all duration-500"
               style={{ width: `${Math.min(skill.percentage, 100)}%` }} />
        </div>
      </div>
    </div>
  )
}

function EducationCard({ stats }) {
  const items = [
    { label: "Bachelor's required", pct: stats.bachelors_required_pct || 0, color: 'bg-info' },
    { label: "Master's required", pct: stats.masters_required_pct || 0, color: 'bg-warning' },
    { label: "Master's preferred", pct: stats.masters_preferred_pct || 0, color: 'bg-accent' },
    { label: "PhD required", pct: stats.phd_required_pct || 0, color: 'bg-danger' },
    { label: "PhD preferred", pct: stats.phd_preferred_pct || 0, color: 'bg-accent/50' },
  ]
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <GraduationCap size={16} className="text-accent" />
        <h3 className="text-sm font-semibold text-fg-primary">Education Requirements</h3>
      </div>
      <div className="space-y-3">
        {items.map(item => (
          <div key={item.label} className="flex items-center gap-3">
            <span className="text-xs text-fg-muted w-36 shrink-0">{item.label}</span>
            <div className="flex-1 h-2 rounded-full bg-bg-tertiary overflow-hidden">
              <div className={`h-full rounded-full ${item.color} transition-all`}
                   style={{ width: `${Math.min(item.pct * 2, 100)}%` }} />
            </div>
            <span className="text-xs font-mono text-fg-primary w-10 text-right">{item.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ExperienceCard({ dist }) {
  const items = [
    { label: '0-2 years', pct: dist['0-2 years'] || 0, color: 'bg-info' },
    { label: '2-5 years', pct: dist['2-5 years'] || 0, color: 'bg-accent' },
    { label: '5-10 years', pct: dist['5-10 years'] || 0, color: 'bg-warning' },
    { label: '10+ years', pct: dist['10+ years'] || 0, color: 'bg-danger' },
  ]
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Briefcase size={16} className="text-accent" />
        <h3 className="text-sm font-semibold text-fg-primary">Experience Distribution</h3>
      </div>
      <div className="space-y-3">
        {items.map(item => (
          <div key={item.label} className="flex items-center gap-3">
            <span className="text-xs text-fg-muted w-24 shrink-0">{item.label}</span>
            <div className="flex-1 h-2 rounded-full bg-bg-tertiary overflow-hidden">
              <div className={`h-full rounded-full ${item.color} transition-all`}
                   style={{ width: `${Math.min(item.pct * 2, 100)}%` }} />
            </div>
            <span className="text-xs font-mono text-fg-primary w-10 text-right">{item.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Tab 2: Resume Gaps ────────────────────────────────────────────────────

function ResumeGapsTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSkillsGaps().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton />
  if (!data?.has_data) return (
    <div className="p-6">
      <EmptyState icon={Target} title="No gap data" description="Run a skills analysis first to see your resume gaps." />
    </div>
  )

  const scoreColor = data.readiness_score >= 70 ? 'text-success' : data.readiness_score >= 40 ? 'text-warning' : 'text-danger'
  const barColor = data.readiness_score >= 70 ? 'bg-success' : data.readiness_score >= 40 ? 'bg-warning' : 'bg-danger'

  return (
    <div className="space-y-6 p-6">
      {/* Readiness Score */}
      <div className="bg-bg-secondary border border-border rounded-2xl p-6">
        <p className="text-xs text-fg-muted mb-1">Market Readiness Score</p>
        <div className="flex items-end gap-3 mb-3">
          <span className={`text-4xl font-bold font-mono ${scoreColor}`}>{data.readiness_score}%</span>
          <span className="text-sm text-fg-muted pb-1">of top-20 market skills matched</span>
        </div>
        <div className="w-full h-2.5 rounded-full bg-bg-tertiary overflow-hidden">
          <div className={`h-full rounded-full ${barColor} transition-all duration-700`}
               style={{ width: `${data.readiness_score}%` }} />
        </div>
        {data.education_insight && (
          <p className="text-xs text-fg-secondary mt-3 bg-accent-bg rounded-lg px-3 py-2">
            <GraduationCap size={12} className="inline mr-1 text-accent" />
            {data.education_insight}
          </p>
        )}
      </div>

      {/* Two columns */}
      <div className="flex gap-4 flex-col lg:flex-row">
        {/* Strengths */}
        <div className="flex-1 bg-bg-secondary border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-success" />
            <h3 className="text-sm font-semibold text-fg-primary">Your Strengths ({data.strengths?.length || 0})</h3>
          </div>
          <div className="space-y-2">
            {(data.strengths || []).map(s => (
              <div key={s.skill} className="flex items-center gap-3 bg-bg-tertiary rounded-lg px-3 py-2.5">
                <CheckCircle size={14} className="text-success shrink-0" />
                <span className="text-sm text-fg-primary font-medium flex-1">{s.skill}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-secondary text-fg-muted">{s.category === 'AI_ML' ? 'AI/ML' : s.category}</span>
                <span className="text-xs font-mono text-success bg-success-bg px-2 py-0.5 rounded-full">
                  {s.market_pct}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Gaps */}
        <div className="flex-1 bg-bg-secondary border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-warning" />
            <h3 className="text-sm font-semibold text-fg-primary">Skills to Learn ({data.gaps?.length || 0})</h3>
          </div>
          <div className="space-y-2">
            {(data.gaps || []).map(g => (
              <div key={g.skill} className="flex items-center gap-3 bg-bg-tertiary rounded-lg px-3 py-2.5">
                <AlertCircle size={14} className={g.priority === 1 ? 'text-danger' : g.priority === 2 ? 'text-warning' : 'text-info'} />
                <span className="text-sm text-fg-primary font-medium flex-1">{g.skill}</span>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                  g.priority === 1 ? 'bg-danger-bg text-danger' :
                  g.priority === 2 ? 'bg-warning-bg text-warning' :
                  'bg-info-bg text-info'
                }`}>P{g.priority}</span>
                <span className="text-xs font-mono text-danger bg-danger-bg px-2 py-0.5 rounded-full">
                  {g.market_pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Underutilized */}
      {data.underutilized?.length > 0 && (
        <div className="bg-bg-secondary border border-border rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-fg-primary mb-3">
            Resume Skills Not Seen in Job Postings ({data.underutilized.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.underutilized.map(u => (
              <span key={u.skill} className="px-2.5 py-1 rounded-lg text-xs bg-bg-tertiary text-fg-muted">
                {u.skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Tab 3: Trending Now ───────────────────────────────────────────────────

function TrendingTab() {
  const { toast } = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    api.getSkillsTrends().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const d = await api.refreshSkillsTrends()
      setData(d)
      if (d.has_data) toast({ type: 'success', title: 'Trends updated!' })
      else toast({ type: 'error', title: d.message || 'Failed to fetch trends' })
    } catch (e) {
      toast({ type: 'error', title: e.message })
    } finally { setRefreshing(false) }
  }

  if (loading) return <LoadingSkeleton />

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          {data?.fetched_at && (
            <span className="text-xs text-fg-muted">Updated: {new Date(data.fetched_at).toLocaleString()}</span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-tertiary text-fg-primary text-xs font-medium hover:bg-bg-secondary transition-colors border border-border disabled:opacity-50"
        >
          <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {!data?.has_data ? (
        <EmptyState icon={TrendingUp} title="No trend data" description="Click Refresh to fetch latest AI/ML trends from the web." />
      ) : (
        <>
          <TrendSection title="Hot Tools" icon={Flame} iconColor="text-danger" iconBg="bg-danger-bg" items={data.hot_tools} />
          <TrendSection title="Rising Models" icon={Brain} iconColor="text-accent" iconBg="bg-accent-bg" items={data.rising_models} />
          <TrendSection title="Must-Know Frameworks" icon={BarChart3} iconColor="text-info" iconBg="bg-info-bg" items={data.must_know_frameworks} />
        </>
      )}
    </div>
  )
}

function TrendSection({ title, icon: Icon, iconColor, iconBg, items }) {
  if (!items?.length) return null
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-8 h-8 rounded-lg ${iconBg} flex items-center justify-center`}>
          <Icon size={15} className={iconColor} />
        </div>
        <h3 className="text-sm font-semibold text-fg-primary">{title}</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {items.map((item, i) => (
          <div key={i} className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-fg-primary">{item.name}</h4>
              {item.url && (
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-accent-dim">
                  <ExternalLink size={14} />
                </a>
              )}
            </div>
            <p className="text-xs text-fg-secondary leading-relaxed">{item.description}</p>
            <div className="bg-accent-bg rounded-lg px-3 py-2">
              <p className="text-xs text-accent font-medium">Why it's hot</p>
              <p className="text-xs text-fg-secondary mt-0.5">{item.why_hot}</p>
            </div>
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${
              item.relevance === 'High' ? 'bg-success-bg text-success border-success/20' :
              item.relevance === 'Medium' ? 'bg-warning-bg text-warning border-warning/20' :
              'bg-info-bg text-info border-info/20'
            }`}>
              {item.relevance} relevance
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Tab 4: Industry News ──────────────────────────────────────────────────

function IndustryNewsTab() {
  const { toast } = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    api.getSkillsNews().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const d = await api.refreshSkillsNews()
      setData(d)
      if (d.has_data) toast({ type: 'success', title: 'News updated!' })
      else toast({ type: 'error', title: d.message || 'Failed to fetch news' })
    } catch (e) {
      toast({ type: 'error', title: e.message })
    } finally { setRefreshing(false) }
  }

  if (loading) return <LoadingSkeleton />

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          {data?.fetched_at && (
            <span className="text-xs text-fg-muted">Updated: {new Date(data.fetched_at).toLocaleString()}</span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-tertiary text-fg-primary text-xs font-medium hover:bg-bg-secondary transition-colors border border-border disabled:opacity-50"
        >
          <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {!data?.has_data ? (
        <EmptyState icon={Newspaper} title="No news yet" description="Click Refresh to fetch the latest industry news." />
      ) : (
        <div className="space-y-3">
          {(data.articles || []).map((item, i) => (
            <div key={i} className="bg-bg-secondary border border-border rounded-2xl p-5 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <h4 className="text-sm font-semibold text-fg-primary leading-snug flex-1">{item.title}</h4>
                <span className="text-xs text-fg-muted shrink-0">{item.date}</span>
              </div>
              <p className="text-xs text-fg-secondary leading-relaxed">{item.summary}</p>
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-1.5">
                  {(item.tags || []).map(tag => (
                    <span key={tag} className="px-2 py-0.5 rounded text-xs bg-accent-bg text-accent border border-accent/20">
                      {tag}
                    </span>
                  ))}
                </div>
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noopener noreferrer"
                     className="flex items-center gap-1 text-xs text-accent hover:text-accent-dim font-medium transition-colors">
                    {item.source} <ArrowUpRight size={12} />
                  </a>
                ) : item.source && (
                  <span className="text-xs text-fg-muted">{item.source}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Shared Components ─────────────────────────────────────────────────────

function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-10 flex flex-col items-center gap-3 text-center">
      <div className="w-12 h-12 rounded-xl bg-accent-bg flex items-center justify-center mb-1">
        <Icon size={22} className="text-accent" />
      </div>
      <p className="text-fg-primary font-semibold text-base">{title}</p>
      <p className="text-sm text-fg-muted max-w-xs">{description}</p>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-6">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="h-16 rounded-2xl bg-bg-secondary border border-border animate-pulse" />
      ))}
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────

export default function SkillsIntelligence() {
  const [tab, setTab] = useTabState('demand')
  const [stats, setStats] = useState(null)

  useEffect(() => {
    Promise.all([
      api.getSkillsDashboard().catch(() => null),
      api.getSkillsGaps().catch(() => null),
    ]).then(([dash, gaps]) => {
      setStats({
        jobs_analyzed: dash?.total_jobs_analyzed || 0,
        unique_skills: dash?.unique_skills || 0,
        readiness: gaps?.readiness_score || 0,
        top_gap: gaps?.top_gap || '--',
      })
    })
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 md:px-10 pt-6 md:pt-8 pb-0">
        <h1 className="text-2xl font-semibold text-fg-primary">Skills Intelligence</h1>
        <p className="text-sm text-fg-muted mt-1">Understand what the market demands and how you match up</p>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mt-5">
          <StatCard icon={Briefcase} label="Jobs Analyzed" value={stats?.jobs_analyzed ?? '--'} sub="from saved jobs" />
          <StatCard icon={Brain} label="Unique Skills" value={stats?.unique_skills ?? '--'} sub="across all listings" color="text-accent" />
          <StatCard icon={Target} label="Market Readiness" value={stats?.readiness ? `${stats.readiness}%` : '--'} sub="resume match" color="text-success" />
          <StatCard icon={AlertCircle} label="Top Skill Gap" value={stats?.top_gap ?? '--'} sub="most in-demand missing" color="text-warning" />
        </div>

        <div className="mt-5">
          <PageTabs tabs={TABS} activeTab={tab} onTabChange={setTab} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === 'demand' && <SkillsDemandTab />}
        {tab === 'gaps' && <ResumeGapsTab />}
        {tab === 'trending' && <TrendingTab />}
        {tab === 'news' && <IndustryNewsTab />}
      </div>
    </div>
  )
}
