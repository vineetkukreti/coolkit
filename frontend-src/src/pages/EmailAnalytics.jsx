import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3, RefreshCw, Download, CheckCircle, Clock, AlertCircle,
  Mail, MessageSquare, Award, XCircle, Eye, AlertTriangle, Send,
  Trophy, FlaskConical, Loader2, Inbox,
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
                    <button
                      onClick={() => handleSendFollowup(item.outreach_id)}
                      disabled={sendingIds.has(item.outreach_id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-accent-bg text-accent text-xs font-medium hover:opacity-80 transition-opacity disabled:opacity-50"
                    >
                      <Send size={12} />
                      {sendingIds.has(item.outreach_id) ? "Sending..." : "Send F/U"}
                    </button>
                  ) : (
                    <span className="text-fg-muted">—</span>
                  )}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
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
                <p className="text-2xl font-bold text-fg-primary font-mono mt-1">{v.total || 0}</p>
              </div>
              <div>
                <p className="text-fg-muted text-xs uppercase tracking-wider">Replies</p>
                <p className="text-2xl font-bold text-success font-mono mt-1">{v.replies || 0}</p>
              </div>
              <div>
                <p className="text-fg-muted text-xs uppercase tracking-wider">Rate</p>
                <p className="text-2xl font-bold text-accent font-mono mt-1">{v.total > 0 ? ((v.replies / v.total) * 100).toFixed(1) : '0'}%</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      {stats.winner?.has_winner && (
        <div className="bg-success-bg border border-success/20 rounded-xl p-4 flex items-center gap-3">
          <Trophy size={18} className="text-success" />
          <div>
            <p className="text-fg-primary text-sm font-semibold">Winner: Variant {stats.winner.winner}</p>
            <p className="text-fg-muted text-xs">{stats.winner.margin}% better performance with {stats.winner.confidence} confidence</p>
          </div>
        </div>
      )}
    </div>
  );
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
        </>
        )}
      </div>
    </div>
  );
}
