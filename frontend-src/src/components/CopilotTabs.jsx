import { useState, useEffect, useCallback } from 'react'
import { Loader2, Copy, Check, Target, Flame, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from './Toast'

// ─── Shared bits ─────────────────────────────────────────────────────────────

const inputCls = 'w-full px-3 py-2 rounded-xl bg-bg-secondary border border-border text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none focus:border-accent'
const btnCls = 'inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50'

function Card({ title, children, copyText }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-fg-primary">{title}</h3>
        {copyText && (
          <button
            onClick={async () => { await navigator.clipboard.writeText(copyText); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-bg-tertiary text-fg-muted hover:text-fg-primary"
          >
            {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </div>
      <div className="text-sm text-fg-secondary whitespace-pre-wrap">{children}</div>
    </div>
  )
}

function List({ items }) {
  return <ul className="list-disc pl-5 space-y-1">{(items || []).map((x, i) => <li key={i}>{String(x)}</li>)}</ul>
}

function useRunner(fn) {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const run = useCallback(async (...args) => {
    setLoading(true)
    try {
      setResult(await fn(...args))
    } catch (e) {
      toast({ title: e.message, type: 'error' })
    } finally {
      setLoading(false)
    }
  }, [fn, toast])
  return { loading, result, setResult, run }
}

// ─── Cover Letter (Teal / Kickresume) ────────────────────────────────────────

export function CoverLetterTab() {
  const [form, setForm] = useState({ jd_text: '', company: '', role: '', tone: 'professional' })
  const { loading, result, run } = useRunner(api.coverLetter)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <input className={inputCls} placeholder="Company" value={form.company} onChange={set('company')} />
        <input className={inputCls} placeholder="Role" value={form.role} onChange={set('role')} />
        <select className={inputCls} value={form.tone} onChange={set('tone')}>
          {['professional', 'enthusiastic', 'concise', 'storytelling'].map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <textarea className={`${inputCls} h-40`} placeholder="Paste the job description…" value={form.jd_text} onChange={set('jd_text')} />
      <button className={btnCls} disabled={loading || !form.jd_text.trim()} onClick={() => run(form)}>
        {loading && <Loader2 size={14} className="animate-spin" />} {loading ? 'Writing…' : 'Generate cover letter'}
      </button>
      {result && (
        <div className="space-y-4">
          <Card title={result.subject || 'Cover Letter'} copyText={result.cover_letter}>{result.cover_letter}</Card>
          {result.requirements_matched?.length > 0 && <Card title="Requirements matched"><List items={result.requirements_matched} /></Card>}
          {result.gaps_not_addressed?.length > 0 && <Card title="Gaps (not claimed)"><List items={result.gaps_not_addressed} /></Card>}
        </div>
      )}
    </div>
  )
}

// ─── Salary (Levels.fyi / Glassdoor style) ───────────────────────────────────

const fmt = (n, cur) => {
  if (typeof n !== 'number') return '—'
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: cur || 'USD', maximumFractionDigits: 0 }).format(n) } catch { return n.toLocaleString() }
}

export function SalaryTab() {
  const [form, setForm] = useState({ role: '', company: '', location: '', experience_years: '' })
  const { loading, result, run } = useRunner(api.salaryEstimate)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const band = (label, b) => b && (
    <div className="grid grid-cols-4 gap-2 items-center">
      <span className="text-fg-muted">{label}</span>
      {['p25', 'p50', 'p75'].map((p) => (
        <div key={p} className={`text-center rounded-lg py-1.5 ${p === 'p50' ? 'bg-accent/15 text-accent font-semibold' : 'bg-bg-tertiary'}`}>
          <div className="text-[10px] uppercase text-fg-muted">{p}</div>{fmt(b[p], result.currency)}
        </div>
      ))}
    </div>
  )
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <input className={inputCls} placeholder="Role *" value={form.role} onChange={set('role')} />
        <input className={inputCls} placeholder="Company" value={form.company} onChange={set('company')} />
        <input className={inputCls} placeholder="Location" value={form.location} onChange={set('location')} />
        <input className={inputCls} placeholder="Years exp" type="number" value={form.experience_years} onChange={set('experience_years')} />
      </div>
      <button className={btnCls} disabled={loading || !form.role.trim()} onClick={() => run(form)}>
        {loading && <Loader2 size={14} className="animate-spin" />} {loading ? 'Estimating…' : 'Estimate pay'}
      </button>
      {result && (
        <div className="space-y-4">
          <Card title={`Pay range · ${result.level_guess || ''} · confidence ${result.confidence || '?'}`}>
            <div className="space-y-2">
              {band('Base', result.base)}
              {band('Total comp', result.total_comp)}
              {typeof result.suggested_ask === 'number' && <p className="pt-2">Suggested ask: <b className="text-fg-primary">{fmt(result.suggested_ask, result.currency)}</b></p>}
              <p className="text-xs text-fg-muted">{result.disclaimer}</p>
            </div>
          </Card>
          {result.negotiation_tips?.length > 0 && <Card title="Negotiation tips"><List items={result.negotiation_tips} /></Card>}
          {result.factors?.length > 0 && <Card title="What moves the number"><List items={result.factors} /></Card>}
        </div>
      )}
    </div>
  )
}

// ─── LinkedIn optimizer (Careerflow / Jobscan) ───────────────────────────────

export function LinkedInTab() {
  const [form, setForm] = useState({ headline: '', about: '', target_role: '' })
  const { loading, result, run } = useRunner(api.linkedinOptimize)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <div className="space-y-4">
      <input className={inputCls} placeholder="Target role (e.g. Healthcare AI Engineer)" value={form.target_role} onChange={set('target_role')} />
      <input className={inputCls} placeholder="Current headline" value={form.headline} onChange={set('headline')} />
      <textarea className={`${inputCls} h-32`} placeholder="Current About section" value={form.about} onChange={set('about')} />
      <button className={btnCls} disabled={loading} onClick={() => run(form)}>
        {loading && <Loader2 size={14} className="animate-spin" />} {loading ? 'Analyzing…' : 'Optimize profile'}
      </button>
      {result && (
        <div className="space-y-4">
          <Card title={`Profile strength: ${result.score ?? '?'}/100`}><List items={result.quick_wins} /></Card>
          {result.headline_options?.map((h, i) => <Card key={i} title={`Headline option ${i + 1}`} copyText={h}>{h}</Card>)}
          {result.about && <Card title="Rewritten About" copyText={result.about}>{result.about}</Card>}
          {result.missing_keywords?.length > 0 && <Card title="Missing recruiter keywords">{result.missing_keywords.join(' · ')}</Card>}
          {result.featured_suggestions?.length > 0 && <Card title="Featured section ideas"><List items={result.featured_suggestions} /></Card>}
        </div>
      )}
    </div>
  )
}

// ─── Mock interview (Final Round AI / Yoodli) ────────────────────────────────

export function MockInterviewTab() {
  const { toast } = useToast()
  const [setup, setSetup] = useState({ company: '', role: '', round_type: 'behavioral' })
  const [q, setQ] = useState(null)
  const [answer, setAnswer] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const set = (k) => (e) => setSetup({ ...setup, [k]: e.target.value })

  const next = async () => {
    setLoading(true)
    try {
      setQ(await api.mockQuestion({ ...setup, asked: history.map((h) => h.question) }))
      setAnswer('')
    } catch (e) { toast({ title: e.message, type: 'error' }) } finally { setLoading(false) }
  }
  const grade = async () => {
    setLoading(true)
    try {
      const g = await api.mockGrade({ question: q.question, answer, role: setup.role })
      setHistory([{ question: q.question, answer, ...g }, ...history])
      setQ(null)
    } catch (e) { toast({ title: e.message, type: 'error' }) } finally { setLoading(false) }
  }
  const avg = history.length ? (history.reduce((s, h) => s + (h.score || 0), 0) / history.length).toFixed(1) : null

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <input className={inputCls} placeholder="Company *" value={setup.company} onChange={set('company')} />
        <input className={inputCls} placeholder="Role *" value={setup.role} onChange={set('role')} />
        <select className={inputCls} value={setup.round_type} onChange={set('round_type')}>
          {['behavioral', 'technical', 'system design', 'ML / AI depth', 'hiring manager'].map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      {!q && (
        <button className={btnCls} disabled={loading || !setup.company || !setup.role} onClick={next}>
          {loading && <Loader2 size={14} className="animate-spin" />} {history.length ? 'Next question' : 'Start mock interview'}
        </button>
      )}
      {q && (
        <Card title="Interviewer">
          <p className="text-fg-primary font-medium mb-3">{q.question}</p>
          <textarea className={`${inputCls} h-36`} placeholder="Type your answer as you'd say it…" value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <div className="flex gap-2 mt-3">
            <button className={btnCls} disabled={loading || !answer.trim()} onClick={grade}>
              {loading && <Loader2 size={14} className="animate-spin" />} Submit answer
            </button>
            <button className="px-4 py-2 rounded-xl border border-border text-sm text-fg-muted" onClick={next} disabled={loading}>Skip</button>
          </div>
        </Card>
      )}
      {avg && <p className="text-sm text-fg-muted">Session average: <b className="text-accent">{avg}/10</b> over {history.length} answer(s)</p>}
      {history.map((h, i) => (
        <Card key={i} title={`${h.score ?? '?'}/10 — ${h.question}`}>
          {h.structure && <p className="mb-2">{h.structure}</p>}
          {h.strengths?.length > 0 && <><b className="text-fg-primary">Strengths</b><List items={h.strengths} /></>}
          {h.improvements?.length > 0 && <><b className="text-fg-primary">Improve</b><List items={h.improvements} /></>}
          {h.model_answer && <><b className="text-fg-primary block mt-2">Stronger answer</b><p>{h.model_answer}</p></>}
          {h.follow_up_question && <p className="mt-2 text-fg-muted">Likely follow-up: {h.follow_up_question}</p>}
        </Card>
      ))}
    </div>
  )
}

// ─── Weekly goals + streak (Huntr / Teal) ────────────────────────────────────

const GOAL_LABELS = { applications: 'Applications', outreach: 'Cold emails sent', followups: 'Follow-ups' }

export function GoalsTab() {
  const { toast } = useToast()
  const [data, setData] = useState(null)
  const [edit, setEdit] = useState(null)

  const load = useCallback(() => api.getGoals().then(setData).catch((e) => toast({ title: e.message, type: 'error' })), [toast])
  useEffect(() => { load() }, [load])

  const save = async () => {
    try {
      setData(await api.setGoals(edit))
      setEdit(null)
      toast({ title: 'Goals updated', type: 'success' })
    } catch (e) { toast({ title: e.message, type: 'error' }) }
  }

  if (!data) return <Loader2 className="animate-spin text-accent" />
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 bg-bg-secondary border border-border rounded-2xl p-5">
        <Flame size={28} className={data.streak_days ? 'text-[#fb923c]' : 'text-fg-muted'} />
        <div>
          <div className="text-2xl font-bold text-fg-primary">{data.streak_days} day streak</div>
          <div className="text-xs text-fg-muted">{data.active_today ? 'Done for today ✓' : 'Apply or send one email today to keep it going'}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {data.goals.map((g) => (
          <div key={g.metric} className="bg-bg-secondary border border-border rounded-2xl p-4">
            <div className="flex items-center gap-2 text-xs text-fg-muted mb-2"><Target size={12} /> {GOAL_LABELS[g.metric]} this week</div>
            {edit ? (
              <input type="number" min="0" className={inputCls} value={edit[g.metric]} onChange={(e) => setEdit({ ...edit, [g.metric]: e.target.value })} />
            ) : (
              <>
                <div className="text-xl font-bold text-fg-primary">{g.done}<span className="text-sm text-fg-muted"> / {g.target}</span></div>
                <div className="h-2 mt-2 rounded-full bg-bg-tertiary overflow-hidden">
                  <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${g.pct}%` }} />
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      {edit ? (
        <div className="flex gap-2">
          <button className={btnCls} onClick={save}>Save goals</button>
          <button className="px-4 py-2 rounded-xl border border-border text-sm text-fg-muted" onClick={() => setEdit(null)}>Cancel</button>
        </div>
      ) : (
        <button className="px-4 py-2 rounded-xl border border-border text-sm text-fg-muted hover:text-fg-primary"
          onClick={() => setEdit(Object.fromEntries(data.goals.map((g) => [g.metric, g.target])))}>Edit weekly targets</button>
      )}
      <p className="text-xs text-fg-muted">Week starts {data.week_start}. Counts come from your applications log and sent outreach.</p>
    </div>
  )
}

// ─── Answer bank (learned answers to custom application questions) ──────────

export function AnswerBankTab() {
  const { toast } = useToast()
  const [answers, setAnswers] = useState(null)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    api.getAnswerBank().then((r) => setAnswers(r.answers)).catch((e) => toast({ title: e.message, type: 'error' }))
  }, [toast])

  const remove = async (id) => {
    try {
      await api.deleteAnswer(id)
      setAnswers(answers.filter((a) => a.id !== id))
    } catch (e) { toast({ title: e.message, type: 'error' }) }
  }

  if (!answers) return <Loader2 className="animate-spin text-accent" />
  const shown = answers.filter((a) => `${a.question} ${a.answer}`.toLowerCase().includes(filter.toLowerCase()))
  return (
    <div className="space-y-4">
      <p className="text-sm text-fg-muted">
        Answers the browser extension reuses on application forms. Fill a form, fix anything the AI got wrong,
        then click <b className="text-fg-primary">Remember my answers</b> in the extension. Your answers always win over the AI's.
      </p>
      <input className={inputCls} placeholder="Search questions…" value={filter} onChange={(e) => setFilter(e.target.value)} />
      {shown.length === 0 && <p className="text-sm text-fg-muted">No saved answers yet.</p>}
      {shown.map((a) => (
        <div key={a.id} className="bg-bg-secondary border border-border rounded-2xl p-4 flex gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-fg-primary">{a.question}</div>
            <div className="text-sm text-fg-secondary whitespace-pre-wrap mt-1">{a.answer}</div>
            <div className="text-xs text-fg-muted mt-2">
              {a.company ? `Only for ${a.company}` : 'All companies'} · used {a.uses}× · {a.source}
            </div>
          </div>
          <button onClick={() => remove(a.id)} className="text-fg-muted hover:text-danger self-start" aria-label="Delete answer">
            <Trash2 size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
