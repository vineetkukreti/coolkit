import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3, RefreshCw, Download, CheckCircle, Clock, AlertCircle,
  Mail, MessageSquare, Award, XCircle, Eye, AlertTriangle, Send,
  Trophy, FlaskConical, Loader2, Inbox, Square, X,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";

const STATUS_CONFIG = {
  replied: { label: "Replied", bg: "bg-success-bg", color: "text-success", border: "border-success" },
  "follow-up": { label: "Follow-up", bg: "bg-warning-bg", color: "text-warning", border: "border-warning" },
  interviewing: { label: "Interview", bg: "bg-info-bg", color: "text-info", border: "border-info" },
  sent: { label: "Sent", bg: "bg-bg-tertiary", color: "text-fg-muted", border: "border-border" },
  "no-reply": { label: "No Reply", bg: "bg-danger-bg", color: "text-danger", border: "border-danger" },
  offer: { label: "Hired", bg: "bg-accent-bg", color: "text-accent", border: "border-accent" },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.sent;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function FunnelBar({ label, value, max, color }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-fg-secondary">{label}</span>
        <span className="text-fg-primary font-medium font-mono">{value}</span>
      </div>
      <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const URGENCY_CONFIG = {
  OVERDUE: { label: "OVERDUE", bg: "bg-danger-bg", color: "text-danger", border: "border-danger" },
  URGENT: { label: "URGENT", bg: "bg-warning-bg", color: "text-warning", border: "border-warning" },
  WAITING: { label: "WAITING", bg: "bg-[#fef9c3]", color: "text-yellow-600", border: "border-yellow-400" },
  COLD: { label: "COLD", bg: "bg-bg-tertiary", color: "text-fg-muted", border: "border-border" },
};

function UrgencyBadge({ urgency }) {
  const cfg = URGENCY_CONFIG[urgency] || URGENCY_CONFIG.COLD;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function FollowUpTab() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingIds, setSendingIds] = useState(new Set());
  const [workerStatus, setWorkerStatus] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [previewingId, setPreviewingId] = useState(null);

  useEffect(() => {
    loadFollowups();
  }, []);

  async function loadFollowups() {
    setLoading(true);
    try {
      const res = await api.getFollowupStatus();
      setData(res);
    } catch (err) {
      toast({ type: "error", title: "Failed to load follow-ups", description: err.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const poll = setInterval(async () => {
      try {
        const ws = await api.getFollowupWorkerStatus();
        setWorkerStatus(ws);
      } catch {}
    }, 3000);
    return () => clearInterval(poll);
  }, []);

  async function handleSendFollowup(outreachId) {
    setSendingIds((prev) => new Set(prev).add(outreachId));
    try {
      await api.recordFollowup(outreachId);
      toast({ type: "success", title: "Follow-up sent" });
      loadFollowups();
    } catch (err) {
      toast({ type: "error", title: "Failed to send follow-up", description: err.message });
    } finally {
      setSendingIds((prev) => {
        const next = new Set(prev);
        next.delete(outreachId);
        return next;
      });
    }
  }

  const entries = data?.entries || [];
  const summary = data?.summary || { overdue: 0, urgent: 0, waiting: 0, cold: 0 };

  const urgencyOrder = { OVERDUE: 0, URGENT: 1, WAITING: 2, COLD: 3 };
  const sorted = [...entries].sort((a, b) => (urgencyOrder[a.urgency] ?? 4) - (urgencyOrder[b.urgency] ?? 4));

  const overdueCount = summary.overdue || 0;
  const urgentCount = summary.urgent || 0;

  return (
    <>
      {/* Auto Follow-up Controls */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-fg-primary text-sm font-medium">Follow-up Queue</p>
          <p className="text-fg-muted text-xs">{overdueCount} overdue, {urgentCount} urgent</p>
        </div>
        <button
          onClick={async () => {
            try {
              await api.autoFollowup();
              toast({ title: "Auto follow-up started", description: "Sending overdue follow-ups...", type: "success" });
              loadFollowups();
            } catch (e) {
              toast({ title: "Failed", description: e.message, type: "error" });
            }
          }}
          disabled={overdueCount === 0}
          className="flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-40"
        >
          <Send size={13} />
          Send All Overdue
        </button>
        {workerStatus?.running && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-fg-muted">
              Worker: {workerStatus.current}/{workerStatus.total}
            </span>
            <button
              onClick={async () => {
                await api.stopFollowupWorker();
                toast({ title: "Follow-up worker stopped", type: "info" });
              }}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-danger/10 text-danger text-xs hover:bg-danger/20 transition-colors"
            >
              <Square size={10} /> Stop
            </button>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "Overdue", value: summary.overdue, bg: "bg-danger-bg", color: "text-danger", icon: AlertCircle },
          { label: "Urgent", value: summary.urgent, bg: "bg-warning-bg", color: "text-warning", icon: AlertTriangle },
          { label: "Waiting", value: summary.waiting, bg: "bg-[#fef9c3]", color: "text-yellow-600", icon: Clock },
          { label: "Cold", value: summary.cold, bg: "bg-bg-tertiary", color: "text-fg-muted", icon: XCircle },
        ].map((s, i) => (
          <div key={i} className={`${s.bg} rounded-lg border border-border px-4 py-3`}>
            <div className="flex items-center gap-1.5">
              <s.icon size={14} className={s.color} />
              <p className={`text-xs font-medium ${s.color} opacity-80`}>{s.label}</p>
            </div>
            <p className={`text-2xl font-bold font-mono ${s.color} mt-1`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Follow-up List */}
      <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
        <div className="flex items-center px-4 py-3 bg-bg-tertiary border-b border-border text-xs font-semibold text-fg-muted">
          <span className="w-24">Urgency</span>
          <span className="w-48">Recipient</span>
          <span className="flex-1">Role @ Company</span>
          <span className="w-24 text-center">Days Ago</span>
          <span className="w-20 text-center">Follow-ups</span>
          <span className="w-28 text-center">Next F/U</span>
          <span className="w-28 text-center">Action</span>
        </div>
        <div className="max-h-[calc(100vh-420px)] overflow-y-auto">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3 border-b border-border">
                <div className="h-3 bg-bg-tertiary rounded animate-pulse w-20" />
                <div className="h-3 bg-bg-tertiary rounded animate-pulse w-40" />
                <div className="h-3 bg-bg-tertiary rounded animate-pulse flex-1" />
                <div className="h-3 bg-bg-tertiary rounded animate-pulse w-16" />
              </div>
            ))
          ) : sorted.length === 0 ? (
            <div className="px-4 py-12 text-center text-fg-muted text-sm">No follow-up entries found.</div>
          ) : (
            sorted.map((item, idx) => (
              <div key={item.outreach_id || idx} className="flex items-center px-4 py-2.5 border-b border-border last:border-0 hover:bg-bg-tertiary/40 transition-colors text-xs">
                <span className="w-24">
                  <UrgencyBadge urgency={item.urgency} />
                </span>
                <span className="w-48 text-fg-primary font-medium truncate">{item.recipient_email}</span>
                <span className="flex-1 text-fg-secondary truncate px-2">
                  {item.role ? `${item.role} @ ${item.company || "—"}` : item.company || "—"}
                </span>
                <span className="w-24 text-center text-fg-muted font-mono">{item.days_since_sent ?? "—"}d</span>
                <span className="w-20 text-center text-fg-muted font-mono">{item.followup_count ?? 0} f/u</span>
                <span className="w-28 text-center text-fg-muted">
                  {item.next_followup_date
                    ? new Date(item.next_followup_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                    : "—"}
                </span>
                <span className="w-28 text-center">
                  {(item.urgency === "OVERDUE" || item.urgency === "URGENT") ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={async () => {
                          setPreviewingId(item.outreach_id);
                          try {
                            const preview = await api.previewFollowup(item.outreach_id);
                            setPreviewData({ ...preview, outreach_id: item.outreach_id });
                          } catch (e) {
                            toast({ title: "Preview failed", description: e.message, type: "error" });
                          } finally {
                            setPreviewingId(null);
                          }
                        }}
                        disabled={previewingId === item.outreach_id}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-border text-fg-secondary text-[10px] hover:text-fg-primary transition-colors disabled:opacity-50"
                      >
                        <Eye size={10} />
                        {previewingId === item.outreach_id ? "..." : "Preview"}
                      </button>
                      <button
                        onClick={() => handleSendFollowup(item.outreach_id)}
                        disabled={sendingIds.has(item.outreach_id)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-accent-bg text-accent text-[10px] font-medium hover:opacity-80 transition-opacity disabled:opacity-50"
                      >
                        <Send size={10} />
                        {sendingIds.has(item.outreach_id) ? "..." : "Send"}
                      </button>
                    </div>
                  ) : (
                    <span className="text-fg-muted">—</span>
                  )}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {previewData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setPreviewData(null)}>
          <div className="bg-bg-secondary border border-border rounded-xl w-full max-w-lg mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <span className="text-sm font-semibold text-fg-primary">Follow-up Preview</span>
              <button onClick={() => setPreviewData(null)} className="text-fg-muted hover:text-fg-primary"><X size={14} /></button>
            </div>
            <div className="px-5 py-4 space-y-3">
              <div>
                <p className="text-xs text-fg-muted mb-1">Subject</p>
                <p className="text-sm text-fg-primary">{previewData.subject}</p>
              </div>
              <div>
                <p className="text-xs text-fg-muted mb-1">Body</p>
                <p className="text-sm text-fg-secondary whitespace-pre-wrap font-mono leading-relaxed">{previewData.body}</p>
              </div>
            </div>
            <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
              <button onClick={() => setPreviewData(null)} className="px-3 py-1.5 rounded-lg border border-border text-fg-secondary text-xs hover:text-fg-primary">Close</button>
              <button onClick={async () => {
                await handleSendFollowup(previewData.outreach_id);
                setPreviewData(null);
              }} className="px-3 py-1.5 rounded-lg bg-accent text-white text-xs font-medium hover:bg-accent/90">Send Follow-up</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ABTestingTab() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAbStats().then((d) => { setStats(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center gap-2 py-12 justify-center text-fg-muted"><Loader2 size={16} className="animate-spin" /> Loading A/B stats...</div>;
  if (!stats?.variants || Object.keys(stats.variants).length === 0) return <div className="py-12 text-center text-fg-muted text-sm">No A/B test data yet. Generate emails to start tracking variants.</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(stats.variants).map(([key, v]) => (
          <div key={key} className="bg-bg-secondary border border-border rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${key === 'A' ? 'bg-accent-bg text-accent border border-accent/20' : 'bg-info-bg text-info border border-info/20'}`}>{key}</span>
                <span className="text-fg-secondary text-sm font-medium">{v.strategy || (key === 'A' ? 'Proof-first' : 'Challenge-first')}</span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-fg-muted text-xs uppercase tracking-wider">Sent</p>
                <p className="text-2xl font-bold text-fg-primary font-mono mt-1">{v.sent || 0}</p>
              </div>
              <div>
                <p className="text-fg-muted text-xs uppercase tracking-wider">Replies</p>
                <p className="text-2xl font-bold text-success font-mono mt-1">{v.replies || 0}</p>
              </div>
              <div>
                <p className="text-fg-muted text-xs uppercase tracking-wider">Rate</p>
                <p className="text-2xl font-bold text-accent font-mono mt-1">{v.sent > 0 ? ((v.replies / v.sent) * 100).toFixed(1) : '0'}%</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      {(stats.winner?.variant === 'A' || stats.winner?.variant === 'B') && (
        <div className="bg-success-bg border border-success/20 rounded-xl p-4 flex items-center gap-3">
          <Trophy size={18} className="text-success" />
          <div>
            <p className="text-fg-primary text-sm font-semibold">Winner: Variant {stats.winner.variant}</p>
            <p className="text-fg-muted text-xs">{stats.winner.reason}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function SendTimeCard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSendTimeStats().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center gap-2 py-6 justify-center text-fg-muted text-sm"><Loader2 size={14} className="animate-spin" /> Loading send time stats...</div>
  if (!data || (!data.hourly && !data.daily)) return null

  const hours = Object.fromEntries((data.hourly || []).map(h => [h.hour, h.rate]))
  const days = Object.fromEntries((data.daily || []).map(d => [d.day, d.rate]))
  const maxHour = Math.max(...Object.values(hours), 1)
  const maxDay = Math.max(...Object.values(days), 1)

  return (
    <div className="grid grid-cols-2 gap-4 mt-6">
      <div className="bg-bg-secondary rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-fg-primary mb-3">Reply Rate by Hour</h3>
        {data.recommendation?.best_hour != null && (
          <p className="text-xs text-success mb-3">Best hour: <strong>{data.recommendation.best_hour}:00</strong></p>
        )}
        <div className="space-y-1">
          {Object.entries(hours).slice(0, 12).map(([hour, rate]) => (
            <div key={hour} className="flex items-center gap-2">
              <span className="text-[10px] text-fg-muted w-8 text-right font-mono">{hour}:00</span>
              <div className="flex-1 h-3 bg-bg-tertiary rounded-full overflow-hidden">
                <div className="h-full bg-accent rounded-full" style={{ width: `${(rate / maxHour) * 100}%` }} />
              </div>
              <span className="text-[10px] text-fg-secondary w-8 text-right font-mono">{typeof rate === 'number' ? rate.toFixed(1) : rate}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-fg-primary mb-3">Reply Rate by Day</h3>
        {data.recommendation?.best_day && (
          <p className="text-xs text-success mb-3">Best day: <strong>{data.recommendation.best_day}</strong></p>
        )}
        <div className="space-y-1.5">
          {Object.entries(days).map(([day, rate]) => (
            <div key={day} className="flex items-center gap-2">
              <span className="text-xs text-fg-muted w-12 text-right">{day.slice(0, 3)}</span>
              <div className="flex-1 h-4 bg-bg-tertiary rounded-full overflow-hidden">
                <div className="h-full bg-info rounded-full" style={{ width: `${(rate / maxDay) * 100}%` }} />
              </div>
              <span className="text-xs text-fg-secondary w-10 text-right font-mono">{typeof rate === 'number' ? rate.toFixed(1) : rate}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function AddressQualityCard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAddressQuality().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading || !data) return null

  return (
    <div className="bg-bg-secondary rounded-xl border border-border p-5 mt-4">
      <h3 className="text-sm font-semibold text-fg-primary mb-3">Address Quality Report</h3>
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-warning font-mono">{data.generic_count || 0}</p>
          <p className="text-xs text-fg-muted mt-1">Generic</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-danger font-mono">{data.bounced_count || 0}</p>
          <p className="text-xs text-fg-muted mt-1">Bounced</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-info font-mono">{data.multi_count || 0}</p>
          <p className="text-xs text-fg-muted mt-1">Multi-address</p>
        </div>
      </div>
      {((data.generic?.length > 0) || (data.bounced?.length > 0) || (data.multi_address?.length > 0)) && (
        <div className="mt-3 max-h-32 overflow-y-auto">
          {[...(data.generic || []).map(e => ({ email: e, reason: 'Generic address' })),
            ...(data.bounced || []).map(e => ({ email: e, reason: 'Bounced' })),
            ...(data.multi_address || []).map(e => ({ email: e, reason: 'Multi-address' }))
          ].slice(0, 10).map((issue, i) => (
            <div key={i} className="flex items-center gap-2 py-1 text-xs">
              <AlertCircle size={11} className="text-warning shrink-0" />
              <span className="text-fg-secondary truncate">{issue.email}</span>
              <span className="text-fg-muted ml-auto">{issue.reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function EmailAnalytics() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [stats, setStats] = useState({});
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("analytics");
  const [imapStatus, setImapStatus] = useState(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    load();
    api.getImapStatus().then(setImapStatus).catch(() => {});
  }, []);

  async function load() {
    setLoading(true);
    try {
      const [pStats, hist] = await Promise.all([api.getPipelineStats(), api.getEmailHistory()]);
      setStats(pStats);
      setHistory(hist.history || []);
    } catch (err) {
      toast({ type: "error", title: "Failed to load analytics", description: err.message });
    } finally {
      setLoading(false);
    }
  }

  const totalSent = history.filter((h) => h.status === "sent").length;
  const replied = stats.replied || 0;
  const interviewing = stats.interviewing || 0;
  const offers = stats.offer || 0;
  const noReply = totalSent - replied - interviewing - offers;
  const conversionRate = totalSent > 0 ? ((replied + interviewing + offers) / totalSent * 100).toFixed(1) : "0.0";

  // Map pipeline stage to email status for display
  function getLeadStatus(item) {
    // Check pipeline_leads for this post
    if (item.status === "sent") return "sent";
    return item.status;
  }

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-bg"><BarChart3 size={20} className="text-accent" /></div>
            <div>
              <h1 className="text-2xl font-semibold text-fg-primary">Email Analytics</h1>
              <p className="text-sm text-fg-secondary mt-0.5">Track email performance, replies, and follow-up conversions.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                setChecking(true);
                try {
                  const res = await api.checkReplies();
                  setImapStatus(prev => ({ ...prev, last_checked: res.last_checked }));
                  if (res.replies_found > 0) {
                    toast({ title: `${res.replies_found} new replies detected!`, type: "success" });
                    load();
                  } else {
                    toast({ title: "No new replies found", type: "info" });
                  }
                } catch (e) {
                  toast({ title: "Reply check failed", description: e.message, type: "error" });
                } finally {
                  setChecking(false);
                }
              }}
              disabled={checking}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent hover:bg-accent/90 text-white text-sm font-medium transition-colors disabled:opacity-50"
            >
              {checking ? <Loader2 size={14} className="animate-spin" /> : <Inbox size={14} />}
              {checking ? "Checking..." : "Check Replies"}
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await api.classifyFailures();
                  toast({ title: `Classified ${res.classified || 0} failures`, type: "success" });
                } catch (e) {
                  toast({ title: "Classification failed", description: e.message, type: "error" });
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors"
            >
              <AlertCircle size={14} />
              Classify Failures
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await api.checkBounces();
                  toast({ title: `Found ${res.replies_found || 0} bounces`, type: res.replies_found > 0 ? "warning" : "success" });
                  load();
                } catch (e) {
                  toast({ title: "Bounce check failed", description: e.message, type: "error" });
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors"
            >
              <XCircle size={14} />
              Check Bounces
            </button>
            {imapStatus?.last_checked && (
              <span className="text-fg-muted text-xs">Last: {new Date(imapStatus.last_checked).toLocaleTimeString()}</span>
            )}
            <button onClick={load} disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors">
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-6 border-b border-border">
          {[
            { key: "analytics", label: "Analytics", icon: BarChart3 },
            { key: "followups", label: "Follow-ups", icon: Clock },
            { key: "ab", label: "A/B Testing", icon: FlaskConical },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                activeTab === tab.key
                  ? "border-accent text-accent"
                  : "border-transparent text-fg-muted hover:text-fg-primary"
              }`}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "ab" ? (
          <ABTestingTab />
        ) : activeTab === "followups" ? (
          <FollowUpTab />
        ) : (
        <>
        {/* Stats */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "Emails Sent", value: totalSent, sub: "total", bg: "bg-bg-secondary", color: "text-fg-primary" },
            { label: "Replied", value: replied, sub: totalSent > 0 ? `${Math.round(replied / totalSent * 100)}%` : "0%", bg: "bg-success-bg", color: "text-success" },
            { label: "Follow-ups Sent", value: stats.applied || 0, sub: "pending", bg: "bg-warning-bg", color: "text-warning" },
            { label: "Converted", value: offers, sub: totalSent > 0 ? `${Math.round(offers / totalSent * 100)}%` : "0%", bg: "bg-info-bg", color: "text-info" },
            { label: "No Reply", value: noReply > 0 ? noReply : 0, sub: totalSent > 0 ? `${Math.round(Math.max(0, noReply) / totalSent * 100)}%` : "0%", bg: "bg-danger-bg", color: "text-danger" },
          ].map((s, i) => (
            <div key={i} className={`${s.bg} rounded-lg border border-border px-4 py-3`}>
              <p className={`text-xs font-medium ${s.color} opacity-80`}>{s.label}</p>
              <div className="flex items-end gap-2">
                <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
                <p className={`text-xs ${s.color} opacity-60 mb-0.5`}>{s.sub}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Body: Funnel + Table */}
        <div className="flex gap-4 items-start">
          {/* Left: Conversion Funnel */}
          <div className="w-80 shrink-0 bg-bg-secondary rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-fg-primary mb-4">Conversion Funnel</h3>
            <div className="space-y-3">
              <FunnelBar label="Sent" value={totalSent} max={totalSent} color="bg-fg-muted" />
              <FunnelBar label="Replied" value={replied} max={totalSent} color="bg-success" />
              <FunnelBar label="Interviewing" value={interviewing} max={totalSent} color="bg-info" />
              <FunnelBar label="Offer" value={offers} max={totalSent} color="bg-accent" />
            </div>
            <div className="mt-4 bg-bg-tertiary rounded-lg px-4 py-3 flex items-center justify-between">
              <span className="text-xs text-fg-secondary font-medium">Overall Conversion Rate</span>
              <span className="text-base font-bold font-mono text-success">{conversionRate}%</span>
            </div>
          </div>

          {/* Right: Email Table */}
          <div className="flex-1 bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="flex items-center px-4 py-3 bg-bg-tertiary border-b border-border text-xs font-semibold text-fg-muted">
              <span className="w-40">Recipient</span>
              <span className="flex-1">Subject</span>
              <span className="w-24 text-center">Status</span>
              <span className="w-20 text-center">Sent</span>
              <span className="w-16 text-center">Action</span>
            </div>
            <div className="max-h-[calc(100vh-420px)] overflow-y-auto">
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-3 border-b border-border">
                    <div className="h-3 bg-bg-tertiary rounded animate-pulse w-32" />
                    <div className="h-3 bg-bg-tertiary rounded animate-pulse flex-1" />
                    <div className="h-3 bg-bg-tertiary rounded animate-pulse w-16" />
                  </div>
                ))
              ) : history.filter((h) => h.status === "sent").length === 0 ? (
                <div className="px-4 py-12 text-center text-fg-muted text-sm">No emails sent yet.</div>
              ) : (
                history.filter((h) => h.status === "sent").map((item, idx) => (
                  <div key={item.id || idx} className="flex items-center px-4 py-2.5 border-b border-border last:border-0 hover:bg-bg-tertiary/40 transition-colors text-xs">
                    <span className="w-40 text-fg-primary font-medium truncate">{item.to_name || item.to_email}</span>
                    <span className="flex-1 text-fg-secondary truncate px-2">{item.subject}</span>
                    <span className="w-24 text-center">
                      <StatusBadge status="sent" />
                    </span>
                    <span className="w-20 text-center text-fg-muted">
                      {item.sent_at ? new Date(item.sent_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—"}
                    </span>
                    <span className="w-16 text-center">
                      <button className="text-accent hover:underline text-xs">View</button>
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Send Time & Address Quality */}
        <SendTimeCard />
        <AddressQualityCard />
        </>
        )}
      </div>
    </div>
  );
}
