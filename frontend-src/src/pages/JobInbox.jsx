import { useState, useEffect, useCallback } from 'react'
import { Inbox, RefreshCw, Loader2, Check, Copy, Reply, ExternalLink } from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'

const TYPES = [
  { key: 'interview', label: 'Interviews', cls: 'bg-success-bg text-success' },
  { key: 'offer', label: 'Offers', cls: 'bg-accent/15 text-accent' },
  { key: 'rejection', label: 'Rejections', cls: 'bg-danger-bg text-danger' },
  { key: 'confirmation', label: 'Confirmations', cls: 'bg-bg-tertiary text-fg-muted' },
]
const TYPE_CLS = Object.fromEntries(TYPES.map((t) => [t.key, t.cls]))

function EmailCard({ email, onHandled }) {
  const { toast } = useToast()
  const [draft, setDraft] = useState(null)
  const [drafting, setDrafting] = useState(false)
  const [copied, setCopied] = useState(false)

  const makeDraft = async () => {
    setDrafting(true)
    try {
      setDraft(await api.draftJobEmailReply(email.id))
    } catch (e) {
      toast({ title: e.message, type: 'error' })
    } finally {
      setDrafting(false)
    }
  }
  const copy = async () => {
    await navigator.clipboard.writeText(`${draft.subject}\n\n${draft.body}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-bg-secondary border border-border rounded-2xl p-4 space-y-2">
      <div className="flex items-start gap-3">
        <span className={`shrink-0 px-2 py-0.5 rounded-full text-[11px] font-bold uppercase ${TYPE_CLS[email.type] || ''}`}>{email.type}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-fg-primary truncate">{email.subject}</div>
          <div className="text-xs text-fg-muted truncate">
            {email.from_addr} · {email.received_at ? new Date(email.received_at).toLocaleString() : ''}
          </div>
        </div>
      </div>
      {email.job_title && (
        <div className="text-xs text-fg-secondary flex items-center gap-1">
          Matched: <b className="text-fg-primary">{email.job_title}</b> at {email.company}
          {email.job_url && <a href={email.job_url} target="_blank" rel="noreferrer" className="text-accent"><ExternalLink size={11} /></a>}
        </div>
      )}
      <p className="text-sm text-fg-secondary line-clamp-3 whitespace-pre-wrap">{email.preview}</p>
      <div className="flex gap-2 pt-1">
        {email.type !== 'confirmation' && (
          <button onClick={makeDraft} disabled={drafting}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-white text-xs font-medium disabled:opacity-50">
            {drafting ? <Loader2 size={12} className="animate-spin" /> : <Reply size={12} />} Draft reply
          </button>
        )}
        <button onClick={() => onHandled(email.id)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs text-fg-muted hover:text-fg-primary">
          <Check size={12} /> Done
        </button>
      </div>
      {draft && (
        <div className="mt-2 rounded-xl bg-bg-tertiary p-3 text-sm text-fg-secondary">
          <div className="flex items-center justify-between mb-1">
            <b className="text-fg-primary text-xs">{draft.subject}</b>
            <button onClick={copy} className="inline-flex items-center gap-1 text-xs text-fg-muted hover:text-fg-primary">
              {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />} {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <p className="whitespace-pre-wrap">{draft.body}</p>
          <p className="text-[11px] text-fg-muted mt-2">Fill in the [placeholders], then paste into Gmail.</p>
        </div>
      )}
    </div>
  )
}

export default function JobInbox() {
  const { toast } = useToast()
  const [emails, setEmails] = useState(null)
  const [filter, setFilter] = useState('')
  const [scanning, setScanning] = useState(false)

  const load = useCallback(
    () => api.getJobEmails().then((r) => setEmails(r.emails)).catch((e) => toast({ title: e.message, type: 'error' })),
    [toast],
  )
  useEffect(() => { load() }, [load])

  const scan = async () => {
    setScanning(true)
    try {
      const r = await api.scanInbox()
      if (r.status === 'error') throw new Error(r.error)
      const u = r.updated || {}
      toast({
        title: `Scanned ${r.scanned} emails, ${r.found.length} new job emails`,
        description: `${u.interviews || 0} interviews · ${u.offers || 0} offers · ${u.rejections || 0} rejections matched to applications`,
        type: 'success',
      })
      await load()
    } catch (e) {
      toast({ title: e.message || 'Inbox scan failed', type: 'error' })
    } finally {
      setScanning(false)
    }
  }

  const markHandled = async (id) => {
    try {
      await api.setJobEmailHandled(id)
      setEmails((list) => list.filter((e) => e.id !== id))
    } catch (e) {
      toast({ title: e.message, type: 'error' })
    }
  }

  const counts = Object.fromEntries(TYPES.map((t) => [t.key, (emails || []).filter((e) => e.type === t.key).length]))
  const shown = (emails || []).filter((e) => !filter || e.type === filter)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-fg-primary flex items-center gap-2"><Inbox size={22} className="text-accent" /> Job Inbox</h1>
          <p className="text-sm text-fg-muted mt-1">Job emails from Gmail, sorted and matched to your applications.</p>
        </div>
        <button onClick={scan} disabled={scanning}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent text-white text-sm font-medium disabled:opacity-50">
          {scanning ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />} {scanning ? 'Scanning…' : 'Check Gmail'}
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button onClick={() => setFilter('')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${!filter ? 'bg-accent text-white' : 'bg-bg-secondary text-fg-muted'}`}>
          All ({emails?.length || 0})
        </button>
        {TYPES.map((t) => (
          <button key={t.key} onClick={() => setFilter(t.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filter === t.key ? 'bg-accent text-white' : 'bg-bg-secondary text-fg-muted'}`}>
            {t.label} ({counts[t.key]})
          </button>
        ))}
      </div>

      {!emails ? <Loader2 className="animate-spin text-accent" /> : shown.length === 0 ? (
        <p className="text-sm text-fg-muted">Nothing here. Click <b>Check Gmail</b> to scan the last 14 days.</p>
      ) : (
        <div className="space-y-3">{shown.map((e) => <EmailCard key={e.id} email={e} onHandled={markHandled} />)}</div>
      )}
    </div>
  )
}
