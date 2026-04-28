import { useState, useCallback } from 'react'
import {
  Sparkles, Send, Search, FileText, GraduationCap,
  Loader2, Copy, Check, ChevronDown, ChevronRight,
} from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'

// ─── Tab definitions ─────────────────────────────────────────────────────────

const TABS = [
  { key: 'evaluate', label: 'Evaluate', icon: Sparkles },
  { key: 'outreach', label: 'Outreach', icon: Send },
  { key: 'deep-dive', label: 'Deep Dive', icon: Search },
  { key: 'tailor-cv', label: 'Tailor CV', icon: FileText },
  { key: 'interview-prep', label: 'Interview Prep', icon: GraduationCap },
]

// ─── Copy button helper ─────────────────────────────────────────────────────

function CopyBtn({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium
        bg-bg-tertiary text-fg-muted hover:text-fg-primary transition-colors"
    >
      {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
      {copied ? 'Copied' : label}
    </button>
  )
}

// ─── Score badge ─────────────────────────────────────────────────────────────

function ScoreBadge({ score }) {
  const num = typeof score === 'number' ? score : parseInt(score, 10)
  let color = 'bg-danger text-white'
  if (num >= 80) color = 'bg-success text-white'
  else if (num >= 60) color = 'bg-warning text-fg-primary'
  else if (num >= 40) color = 'bg-[#fb923c] text-white'
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${color}`}>
      {num}/100
    </span>
  )
}

// ─── Verdict badge ───────────────────────────────────────────────────────────

function VerdictBadge({ verdict }) {
  const v = (verdict || '').toUpperCase()
  let cls = 'bg-bg-tertiary text-fg-muted'
  if (v === 'APPLY') cls = 'bg-success-bg text-success'
  else if (v === 'SKIP') cls = 'bg-danger-bg text-danger'
  else if (v === 'CONSIDER') cls = 'bg-warning-bg text-warning'
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase ${cls}`}>
      {verdict}
    </span>
  )
}

// ─── Collapsible section ─────────────────────────────────────────────────────

function Collapsible({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-fg-primary bg-bg-tertiary hover:bg-bg-secondary transition-colors"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {title}
      </button>
      {open && <div className="px-4 py-3 text-sm text-fg-secondary">{children}</div>}
    </div>
  )
}

// ─── Result card ─────────────────────────────────────────────────────────────

function ResultCard({ title, children, copyText }) {
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-fg-primary">{title}</h3>
        {copyText && <CopyBtn text={copyText} />}
      </div>
      <div className="text-sm text-fg-secondary whitespace-pre-wrap">{children}</div>
    </div>
  )
}

// ─── Section card for deep dive ──────────────────────────────────────────────

function SectionCard({ title, content, highlight }) {
  return (
    <div className={`bg-bg-secondary border rounded-2xl p-5 shadow-sm ${highlight ? 'border-accent' : 'border-border'}`}>
      <h3 className={`text-sm font-semibold mb-2 ${highlight ? 'text-accent' : 'text-fg-primary'}`}>{title}</h3>
      <p className="text-sm text-fg-secondary whitespace-pre-wrap">{content}</p>
    </div>
  )
}

// ─── Evaluate Tab ────────────────────────────────────────────────────────────

function EvaluateTab() {
  const { toast } = useToast()
  const [jdText, setJdText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async () => {
    if (!jdText.trim()) return toast({ title: 'Paste a job description first', type: 'warning' })
    setLoading(true)
    try {
      const res = await api.evaluateJob(jdText)
      setResult(res)
      toast({ title: 'Evaluation complete', type: 'success' })
    } catch (e) {
      toast({ title: e.message || 'Evaluation failed', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          placeholder="Paste job description here..."
          rows={6}
          className="w-full rounded-xl border border-border bg-bg-secondary px-4 py-3 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30 resize-y"
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-dim
            text-fg-inverse text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {loading ? 'Evaluating...' : 'Evaluate'}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <ScoreBadge score={result.score} />
            <VerdictBadge verdict={result.verdict} />
          </div>

          {result.summary && (
            <ResultCard title="Summary">
              {typeof result.summary === 'object' ? (
                <table className="w-full text-sm">
                  <tbody>
                    {Object.entries(result.summary).map(([k, v]) => (
                      <tr key={k} className="border-b border-border last:border-0">
                        <td className="py-1.5 pr-4 font-medium text-fg-primary capitalize">{k.replace(/_/g, ' ')}</td>
                        <td className="py-1.5 text-fg-secondary">{String(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                result.summary
              )}
            </ResultCard>
          )}

          {result.cv_matches && result.cv_matches.length > 0 && (
            <ResultCard title="CV Matches">
              <ul className="space-y-1">
                {result.cv_matches.map((m, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check size={14} className="text-success mt-0.5 shrink-0" />
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          )}

          {result.gaps && result.gaps.length > 0 && (
            <ResultCard title="Gaps">
              <ul className="space-y-1">
                {result.gaps.map((g, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-danger mt-0.5 shrink-0">&#x2717;</span>
                    <span>{g}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          )}

          {result.personalization_tips && result.personalization_tips.length > 0 && (
            <ResultCard title="Personalization Tips">
              <ul className="space-y-1">
                {result.personalization_tips.map((t, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Sparkles size={12} className="text-accent mt-0.5 shrink-0" />
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Outreach Tab ────────────────────────────────────────────────────────────

function OutreachTab() {
  const { toast } = useToast()
  const [form, setForm] = useState({ company: '', role: '', recruiter_name: '', context: '' })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async () => {
    if (!form.company.trim() || !form.role.trim()) return toast({ title: 'Company and role are required', type: 'warning' })
    setLoading(true)
    try {
      const res = await api.generateOutreach(form)
      setResult(res)
      toast({ title: 'Messages generated', type: 'success' })
    } catch (e) {
      toast({ title: e.message || 'Generation failed', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <input
          value={form.company}
          onChange={set('company')}
          placeholder="Company name *"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <input
          value={form.role}
          onChange={set('role')}
          placeholder="Role title *"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <input
          value={form.recruiter_name}
          onChange={set('recruiter_name')}
          placeholder="Recruiter name (optional)"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <textarea
          value={form.context}
          onChange={set('context')}
          placeholder="Additional context (optional)"
          rows={1}
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30 resize-y"
        />
      </div>
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-dim
          text-fg-inverse text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        {loading ? 'Generating...' : 'Generate Messages'}
      </button>

      {result && (
        <div className="space-y-4">
          {result.cold_email && (
            <ResultCard
              title="Cold Email"
              copyText={`Subject: ${result.cold_email.subject || ''}\n\n${result.cold_email.body || ''}`}
            >
              {result.cold_email.subject && (
                <div className="mb-2">
                  <span className="font-medium text-fg-primary">Subject:</span> {result.cold_email.subject}
                </div>
              )}
              {result.cold_email.body}
            </ResultCard>
          )}
          {result.linkedin_message && (
            <ResultCard title="LinkedIn Message" copyText={result.linkedin_message}>
              {result.linkedin_message}
            </ResultCard>
          )}
          {result.followup_email && (
            <ResultCard
              title="Follow-up Email"
              copyText={`Subject: ${result.followup_email.subject || ''}\n\n${result.followup_email.body || ''}`}
            >
              {result.followup_email.subject && (
                <div className="mb-2">
                  <span className="font-medium text-fg-primary">Subject:</span> {result.followup_email.subject}
                </div>
              )}
              {result.followup_email.body}
            </ResultCard>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Deep Dive Tab ───────────────────────────────────────────────────────────

function DeepDiveTab() {
  const { toast } = useToast()
  const [form, setForm] = useState({ company: '', role: '' })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async () => {
    if (!form.company.trim()) return toast({ title: 'Company name is required', type: 'warning' })
    setLoading(true)
    try {
      const res = await api.deepDive(form)
      setResult(res)
      toast({ title: 'Research complete', type: 'success' })
    } catch (e) {
      toast({ title: e.message || 'Research failed', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const SECTIONS = [
    { key: 'ai_strategy', title: 'AI Strategy' },
    { key: 'recent_moves', title: 'Recent Moves' },
    { key: 'engineering_culture', title: 'Engineering Culture' },
    { key: 'challenges', title: 'Challenges' },
    { key: 'competitive_position', title: 'Competitive Position' },
    { key: 'your_angle', title: 'Your Angle' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <input
          value={form.company}
          onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
          placeholder="Company name *"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <input
          value={form.role}
          onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
          placeholder="Role (optional)"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
      </div>
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-dim
          text-fg-inverse text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
        {loading ? 'Researching...' : 'Research'}
      </button>

      {result && (
        <div className="space-y-4">
          {result.outreach_hook && (
            <div className="bg-accent-bg border border-accent/30 rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-accent mb-1">Outreach Hook</h3>
              <p className="text-sm text-fg-primary">{result.outreach_hook}</p>
            </div>
          )}
          {result.suggested_opening && (
            <div className="bg-accent-bg border border-accent/30 rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-accent mb-1">Suggested Opening</h3>
              <p className="text-sm text-fg-primary">{result.suggested_opening}</p>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SECTIONS.map(({ key, title }) =>
              result[key] ? (
                <SectionCard key={key} title={title} content={result[key]} />
              ) : null
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Tailor CV Tab ───────────────────────────────────────────────────────────

function TailorCVTab() {
  const { toast } = useToast()
  const [jdText, setJdText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async () => {
    if (!jdText.trim()) return toast({ title: 'Paste a job description first', type: 'warning' })
    setLoading(true)
    try {
      const res = await api.tailorCv(jdText)
      setResult(res)
      toast({ title: 'CV tailored', type: 'success' })
    } catch (e) {
      toast({ title: e.message || 'Tailoring failed', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const allText = result
    ? [
        result.professional_summary && `Professional Summary:\n${result.professional_summary}`,
        result.competencies?.length && `Competencies:\n${result.competencies.join(', ')}`,
        result.experience_bullets?.length && `Experience:\n${result.experience_bullets.join('\n')}`,
      ]
        .filter(Boolean)
        .join('\n\n')
    : ''

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          placeholder="Paste job description here..."
          rows={6}
          className="w-full rounded-xl border border-border bg-bg-secondary px-4 py-3 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30 resize-y"
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-dim
            text-fg-inverse text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
          {loading ? 'Tailoring...' : 'Tailor CV'}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <CopyBtn text={allText} label="Copy All" />
          </div>

          {result.professional_summary && (
            <ResultCard title="Professional Summary">{result.professional_summary}</ResultCard>
          )}

          {result.competencies?.length > 0 && (
            <ResultCard title="Core Competencies">
              <div className="flex flex-wrap gap-2">
                {result.competencies.map((c, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg bg-accent-bg text-accent text-xs font-medium">
                    {c}
                  </span>
                ))}
              </div>
            </ResultCard>
          )}

          {result.experience_bullets?.length > 0 && (
            <ResultCard title="Experience Bullets">
              <ul className="space-y-1.5">
                {result.experience_bullets.map((b, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-accent mt-0.5 shrink-0">&bull;</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          )}

          {result.keyword_coverage && (
            <ResultCard title="Keyword Coverage">
              {result.keyword_coverage.coverage_percent != null && (
                <div className="mb-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-fg-muted">Coverage</span>
                    <span className="font-mono font-medium text-fg-primary">
                      {result.keyword_coverage.coverage_percent}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${result.keyword_coverage.coverage_percent}%` }}
                    />
                  </div>
                </div>
              )}
              {result.keyword_coverage.matched?.length > 0 && (
                <div className="mb-2">
                  <span className="text-xs font-medium text-fg-muted">Matched:</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {result.keyword_coverage.matched.map((k, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-success-bg text-success text-xs">{k}</span>
                    ))}
                  </div>
                </div>
              )}
              {result.keyword_coverage.gaps?.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-fg-muted">Gaps:</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {result.keyword_coverage.gaps.map((k, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-danger-bg text-danger text-xs">{k}</span>
                    ))}
                  </div>
                </div>
              )}
            </ResultCard>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Interview Prep Tab ──────────────────────────────────────────────────────

function InterviewPrepTab() {
  const { toast } = useToast()
  const [form, setForm] = useState({ company: '', role: '' })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async () => {
    if (!form.company.trim() || !form.role.trim()) return toast({ title: 'Company and role are required', type: 'warning' })
    setLoading(true)
    try {
      const res = await api.interviewPrep(form)
      setResult(res)
      toast({ title: 'Prep ready', type: 'success' })
    } catch (e) {
      toast({ title: e.message || 'Prep failed', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <input
          value={form.company}
          onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
          placeholder="Company name *"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <input
          value={form.role}
          onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
          placeholder="Role *"
          className="rounded-xl border border-border bg-bg-secondary px-4 py-2.5 text-sm text-fg-primary
            placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
      </div>
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-dim
          text-fg-inverse text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? <Loader2 size={14} className="animate-spin" /> : <GraduationCap size={14} />}
        {loading ? 'Preparing...' : 'Prepare'}
      </button>

      {result && (
        <div className="space-y-4">
          {result.process_overview && (
            <ResultCard title="Process Overview">{result.process_overview}</ResultCard>
          )}

          {result.rounds?.length > 0 && (
            <ResultCard title="Interview Rounds">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 pr-4 font-medium text-fg-primary">Round</th>
                      <th className="text-left py-2 pr-4 font-medium text-fg-primary">Type</th>
                      <th className="text-left py-2 font-medium text-fg-primary">Focus</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.rounds.map((r, i) => (
                      <tr key={i} className="border-b border-border last:border-0">
                        <td className="py-2 pr-4 text-fg-secondary">{r.round || i + 1}</td>
                        <td className="py-2 pr-4 text-fg-secondary">{r.type}</td>
                        <td className="py-2 text-fg-secondary">{r.focus}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ResultCard>
          )}

          {result.star_stories?.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-fg-primary">STAR Stories</h3>
              {result.star_stories.map((s, i) => (
                <Collapsible key={i} title={s.title || `Story ${i + 1}`}>
                  {s.situation && <p className="mb-1"><span className="font-medium text-fg-primary">Situation:</span> {s.situation}</p>}
                  {s.task && <p className="mb-1"><span className="font-medium text-fg-primary">Task:</span> {s.task}</p>}
                  {s.action && <p className="mb-1"><span className="font-medium text-fg-primary">Action:</span> {s.action}</p>}
                  {s.result && <p><span className="font-medium text-fg-primary">Result:</span> {s.result}</p>}
                  {typeof s === 'string' && <p>{s}</p>}
                </Collapsible>
              ))}
            </div>
          )}

          {result.technical_checklist?.length > 0 && (
            <ResultCard title="Technical Checklist">
              <ul className="space-y-1.5">
                {result.technical_checklist.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check size={14} className="text-accent mt-0.5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          )}

          {result.questions_to_ask?.length > 0 && (
            <ResultCard title="Questions to Ask">
              <ul className="space-y-1.5">
                {result.questions_to_ask.map((q, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-accent mt-0.5 shrink-0">?</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function AITools() {
  const [activeTab, setActiveTab] = useState('evaluate')

  const renderTab = () => {
    switch (activeTab) {
      case 'evaluate': return <EvaluateTab />
      case 'outreach': return <OutreachTab />
      case 'deep-dive': return <DeepDiveTab />
      case 'tailor-cv': return <TailorCVTab />
      case 'interview-prep': return <InterviewPrepTab />
      default: return null
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-fg-primary flex items-center gap-2">
          <Sparkles size={22} className="text-accent" />
          AI Tools
        </h1>
        <p className="text-sm text-fg-muted mt-1">AI-powered tools to supercharge your job search</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6 border-b border-border">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab.key
                ? 'border-accent text-accent'
                : 'border-transparent text-fg-muted hover:text-fg-primary'
            }`}
          >
            <tab.icon size={14} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {renderTab()}
    </div>
  )
}
