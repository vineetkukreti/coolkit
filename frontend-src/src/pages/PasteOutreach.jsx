import { useState, useEffect } from "react";
import {
  Sparkles, Send, Save, ArrowLeft, ArrowRight, X, Check, Mail, FileText, Phone,
  Loader2, ClipboardPaste, Paperclip, AlertCircle, CheckCircle, MapPin, Briefcase,
  Clock, Building2, Hash, ChevronDown, ChevronUp, Eye, Database, History,
  Search, Copy, ExternalLink,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";

// ═══════════════════════════════════════════════════════════════════════════
// SHARED SUB-COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════

const STEPS = [
  { key: "paste", label: "Paste Posts", icon: ClipboardPaste },
  { key: "review", label: "Review & Select", icon: Eye },
  { key: "emails", label: "Generate & Send", icon: Send },
];

function StepIndicator({ current }) {
  const idx = STEPS.findIndex(s => s.key === current);
  return (
    <div className="flex items-center gap-1 mb-6">
      {STEPS.map((step, i) => {
        const Icon = step.icon;
        const done = i < idx;
        const active = i === idx;
        return (
          <div key={step.key} className="flex items-center gap-1">
            {i > 0 && <div className={`w-12 h-px ${done ? "bg-accent" : "bg-border"}`} />}
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
              ${active ? "bg-accent/10 text-accent border border-accent/20" : done ? "bg-success/10 text-success" : "text-fg-muted"}`}>
              {done ? <CheckCircle size={12} /> : <Icon size={12} />}
              {step.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Field({ icon: Icon, label, value, accent, children }) {
  return (
    <div>
      <div className="flex items-center gap-1 mb-1">
        <Icon size={10} className="text-fg-muted" />
        <span className="text-[10px] font-medium text-fg-muted uppercase tracking-wider">{label}</span>
      </div>
      {children || <div className={`text-xs ${accent ? "text-accent" : "text-fg-secondary"}`}>{value || "—"}</div>}
    </div>
  );
}

function ContactCard({ post, selected, onToggle, onEmailChange, defaultCollapsed }) {
  const [expanded, setExpanded] = useState(!defaultCollapsed);
  const isBank = !post.fit;
  const alreadySent = post.already_contacted;
  return (
    <div className={`bg-bg-secondary border rounded-xl transition-all ${alreadySent ? "opacity-40" : isBank ? "opacity-60 hover:opacity-80" : ""} ${selected ? "border-accent/30 shadow-sm shadow-accent/5" : "border-border"}`}>
      <div className="flex items-center gap-3 px-4 py-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <button onClick={(e) => { e.stopPropagation(); onToggle(); }}
          className={`w-5 h-5 rounded flex items-center justify-center shrink-0 transition-colors ${selected ? "bg-accent" : "bg-bg-tertiary border border-border hover:border-fg-muted"}`}>
          {selected && <Check size={13} className="text-white" />}
        </button>
        <div className="flex-1 min-w-0 flex items-center gap-3">
          <Building2 size={14} className={alreadySent ? "text-fg-muted shrink-0" : isBank ? "text-fg-muted shrink-0" : "text-accent shrink-0"} />
          <span className={`text-sm font-semibold truncate ${alreadySent ? "text-fg-muted line-through" : "text-fg-primary"}`}>{post.company || "Unknown"}</span>
          <span className="text-xs text-fg-muted hidden sm:inline">·</span>
          <span className="text-xs text-fg-secondary truncate hidden sm:inline">{post.role || "—"}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {alreadySent && <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium bg-success/10 text-success whitespace-nowrap"><CheckCircle size={9} /> Already Sent</span>}
          {post.email && !alreadySent && <span className="text-xs text-accent truncate max-w-[180px]">{post.email}</span>}
          {post.phone && <Phone size={11} className="text-success" />}
          {!alreadySent && isBank && <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-warning-bg text-warning whitespace-nowrap">{post.fit_reason?.replace(/^(exp-too-high:|irrelevant-role:|location:)/, "")}</span>}
          {!alreadySent && !isBank && post.domain_relevance === "High" && <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-accent-bg text-accent">High</span>}
          {expanded ? <ChevronUp size={14} className="text-fg-muted" /> : <ChevronDown size={14} className="text-fg-muted" />}
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-border/50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-3 mt-3">
            <Field icon={Mail} label="Email" accent>
              <input type="text" value={post.email || ""} onChange={(e) => onEmailChange(e.target.value)}
                className="w-full text-xs text-accent bg-bg-primary border border-accent/20 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-accent" onClick={(e) => e.stopPropagation()} />
            </Field>
            <Field icon={Phone} label="Phone" value={post.phone} />
            <Field icon={MapPin} label="Location" value={post.location} />
            <Field icon={Clock} label="Experience" value={post.experience} />
            <Field icon={Briefcase} label="Role" value={post.role} />
            <Field icon={Building2} label="Work Mode" value={post.work_mode} />
            <Field icon={Sparkles} label="Relevance" value={post.domain_relevance} />
            <Field icon={Clock} label="Posted" value={post.posted_ago ? `${post.posted_ago} ago` : post.posted_at || "—"} />
          </div>
          {post.skills && Object.keys(post.skills).length > 0 && (
            <div className="mt-3 space-y-1.5">
              {Object.entries(post.skills).map(([cat, skills]) => (
                <div key={cat} className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[9px] font-semibold text-fg-muted uppercase w-16 shrink-0">{cat.replace(/_/g, " ")}</span>
                  {skills.map((s, i) => <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-accent/8 text-accent/80">{s}</span>)}
                </div>
              ))}
            </div>
          )}
          {!post.skills && post.hashtags && (
            <div className="mt-3 flex items-center gap-1 flex-wrap">
              <Hash size={11} className="text-fg-muted" />
              {post.hashtags.split(", ").map((tag, i) => <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-accent/8 text-accent/80">{tag}</span>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmailCard({ email, onSubjectChange, onBodyChange, onSend, onSaveDraft, sending, attachResume, onToggleResume }) {
  const [collapsed, setCollapsed] = useState(false);
  if (email.status === "sent") return (
    <div className="flex items-center gap-3 px-4 py-3 bg-bg-secondary border border-success/20 rounded-xl">
      <CheckCircle size={15} className="text-success shrink-0" />
      <span className="text-sm text-fg-primary flex-1">Sent to <span className="text-accent">{email.to_email}</span></span>
      <span className="text-xs text-fg-muted">{email.company}</span>
    </div>
  );
  if (email.status === "saved") return (
    <div className="flex items-center gap-3 px-4 py-3 bg-bg-secondary border border-accent/20 rounded-xl">
      <Save size={15} className="text-accent shrink-0" />
      <span className="text-sm text-fg-primary flex-1">Draft saved for <span className="text-accent">{email.to_email}</span></span>
      <span className="text-xs text-fg-muted">{email.company}</span>
    </div>
  );
  if (email.status === "error") return (
    <div className="flex items-center gap-3 px-4 py-3 bg-bg-secondary border border-danger/20 rounded-xl">
      <AlertCircle size={15} className="text-danger shrink-0" />
      <span className="text-sm text-fg-primary flex-1">{email.company} — <span className="text-danger text-xs">{email.error}</span></span>
    </div>
  );
  return (
    <div className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 cursor-pointer" onClick={() => setCollapsed(!collapsed)}>
        <div className="flex items-center gap-2">
          <Mail size={14} className="text-accent" />
          <span className="text-sm font-medium text-fg-primary">{email.to_email}</span>
          <span className="text-xs text-fg-muted">· {email.company} · {email.role}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={(e) => { e.stopPropagation(); onSaveDraft(); }} disabled={sending} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-border text-fg-muted text-[11px] hover:text-fg-primary transition-colors disabled:opacity-50"><Save size={11} /> Draft</button>
          <button onClick={(e) => { e.stopPropagation(); onSend(); }} disabled={sending} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-success text-white text-[11px] font-semibold hover:bg-success/90 transition-colors disabled:opacity-50">{sending ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />} Send</button>
        </div>
      </div>
      {!collapsed && (
        <div className="px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-fg-muted uppercase w-14 shrink-0">Subject</span>
            <input type="text" value={email.subject} onChange={(e) => onSubjectChange(e.target.value)} className="flex-1 bg-bg-primary border border-border rounded-md px-2.5 py-1.5 text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent" />
          </div>
          <textarea value={email.body} onChange={(e) => onBodyChange(e.target.value)} rows={5} className="w-full bg-bg-primary border border-border rounded-md px-2.5 py-1.5 text-sm text-fg-primary font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-accent resize-none" />
          <label className="flex items-center gap-1.5 text-[11px] text-fg-muted cursor-pointer select-none">
            <input type="checkbox" checked={attachResume} onChange={onToggleResume} className="rounded border-border text-accent focus:ring-accent w-3.5 h-3.5" />
            <Paperclip size={10} /> Resume
          </label>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// HISTORY DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════

function SkillDemandPanel() {
  const [demand, setDemand] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backfilling, setBackfilling] = useState(false);
  const { toast } = useToast();

  useEffect(() => { loadDemand(); }, []);

  async function loadDemand() {
    setLoading(true);
    try { const res = await api.getSkillDemand(); setDemand(res); }
    catch {} finally { setLoading(false); }
  }

  async function handleBackfill() {
    setBackfilling(true);
    try {
      const res = await api.backfillSkills();
      toast({ type: "success", title: "Backfill complete", description: `${res.pasted_updated} pasted + ${res.posts_updated} scraped posts updated` });
      loadDemand();
    } catch (err) { toast({ type: "error", title: "Backfill failed", description: err.message }); }
    finally { setBackfilling(false); }
  }

  if (loading) return <div className="flex items-center justify-center py-12 text-fg-muted"><Loader2 size={16} className="animate-spin mr-2" /> Loading skill demand...</div>;

  const CAT_LABELS = { language: "Languages", ai_ml: "AI / ML", ml_framework: "ML Frameworks", deep_learning: "Deep Learning", backend: "Backend", frontend: "Frontend", database: "Databases", cloud: "Cloud", devops: "DevOps", data_engineering: "Data Eng", mlops: "MLOps", tools: "Tools" };
  const CAT_COLORS = { language: "bg-blue-500/20 text-blue-400", ai_ml: "bg-purple-500/20 text-purple-400", ml_framework: "bg-pink-500/20 text-pink-400", deep_learning: "bg-red-500/20 text-red-400", backend: "bg-green-500/20 text-green-400", frontend: "bg-cyan-500/20 text-cyan-400", database: "bg-amber-500/20 text-amber-400", cloud: "bg-sky-500/20 text-sky-400", devops: "bg-orange-500/20 text-orange-400", data_engineering: "bg-emerald-500/20 text-emerald-400", mlops: "bg-violet-500/20 text-violet-400", tools: "bg-gray-500/20 text-gray-400" };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-fg-primary">Skill Demand Analysis</h3>
          <p className="text-xs text-fg-muted mt-0.5">Based on {demand?.total_posts || 0} job posts — what recruiters are asking for</p>
        </div>
        <button onClick={handleBackfill} disabled={backfilling}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-fg-muted text-xs hover:text-fg-primary transition-colors disabled:opacity-50">
          {backfilling ? <Loader2 size={11} className="animate-spin" /> : <Database size={11} />}
          {backfilling ? "Backfilling..." : "Backfill All Posts"}
        </button>
      </div>
      {demand?.demand && Object.keys(demand.demand).length > 0 ? (
        <div className="grid grid-cols-2 gap-4">
          {Object.entries(demand.demand).sort((a, b) => b[1].length - a[1].length).map(([cat, skills]) => (
            <div key={cat} className="bg-bg-secondary border border-border rounded-xl p-4">
              <h4 className="text-xs font-semibold text-fg-muted uppercase tracking-wider mb-3">{CAT_LABELS[cat] || cat}</h4>
              <div className="space-y-1.5">
                {skills.slice(0, 8).map((s, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${CAT_COLORS[cat] || "bg-gray-500/20 text-gray-400"}`}>{s.skill}</span>
                        <span className="text-[10px] text-fg-muted">{s.count} ({s.pct}%)</span>
                      </div>
                      <div className="w-full h-1 bg-bg-tertiary rounded-full overflow-hidden">
                        <div className="h-full bg-accent/40 rounded-full" style={{ width: `${s.pct}%` }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-10 text-fg-muted text-sm">No skill data yet. Click "Backfill All Posts" to extract skills from existing posts.</div>
      )}
    </div>
  );
}

function HistoryDashboard() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState(null);
  const [historyView, setHistoryView] = useState("contacts"); // "contacts" | "skills"

  useEffect(() => { loadHistory(); }, []);

  async function loadHistory() {
    setLoading(true);
    try {
      const res = await api.getPasteHistory();
      setData(res);
    } catch (err) {
      toast({ type: "error", title: "Failed to load history", description: err.message });
    } finally {
      setLoading(false);
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    toast({ type: "success", title: "Copied!" });
  }

  if (loading) return <div className="flex items-center justify-center py-20 text-fg-muted"><Loader2 size={20} className="animate-spin mr-2" /> Loading history...</div>;
  if (!data || data.contacts.length === 0) return (
    <div className="flex flex-col items-center justify-center py-20 text-fg-muted space-y-3">
      <Database size={32} className="opacity-30" />
      <p className="text-sm">No pasted contacts yet. Use the Paste tab to get started.</p>
    </div>
  );

  const { stats, contacts } = data;
  const q = search.trim().toLowerCase();
  let filtered = contacts;
  if (filter === "sent") filtered = filtered.filter(c => c.status === "sent");
  else if (filter === "draft") filtered = filtered.filter(c => c.status === "draft" && c.subject);
  else if (filter === "bank") filtered = filtered.filter(c => !c.subject && c.status === "draft");
  else if (filter === "contacted") filtered = filtered.filter(c => c.already_contacted);
  else if (filter === "new") filtered = filtered.filter(c => !c.already_contacted && c.status !== "sent");
  if (q) filtered = filtered.filter(c =>
    [c.recipient_email, c.company, c.role, c.location, c.phone, c.hashtags].filter(Boolean).join(" ").toLowerCase().includes(q)
  );

  return (
    <div className="space-y-5">
      {/* Contacts / Skills toggle */}
      <div className="flex items-center gap-1 bg-bg-secondary border border-border rounded-lg p-0.5 w-fit">
        <button onClick={() => setHistoryView("contacts")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${historyView === "contacts" ? "bg-accent/10 text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
          <Mail size={12} /> Contacts
        </button>
        <button onClick={() => setHistoryView("skills")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${historyView === "skills" ? "bg-accent/10 text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
          <Sparkles size={12} /> Skill Demand
        </button>
      </div>

      {historyView === "skills" && <SkillDemandPanel />}

      {historyView === "contacts" && <>
      {/* Stats row */}
      <div className="grid grid-cols-7 gap-2">
        {[
          { label: "Total Contacts", value: stats.total, color: "text-fg-primary" },
          { label: "Emails Sent", value: stats.sent, color: "text-success" },
          { label: "Drafts", value: stats.drafted, color: "text-accent" },
          { label: "Failed", value: stats.failed, color: "text-danger" },
          { label: "Contacted", value: stats.already_contacted || 0, color: "text-success" },
          { label: "With Phone", value: stats.with_phone, color: "text-success" },
          { label: "Companies", value: stats.unique_companies, color: "text-warning" },
        ].map((s, i) => (
          <div key={i} className="bg-bg-secondary border border-border rounded-xl px-3 py-2.5 text-center">
            <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[9px] text-fg-muted mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search + Filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by email, company, role, phone, hashtags..."
            className="w-full pl-9 pr-3 py-2 bg-bg-secondary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none focus:ring-1 focus:ring-accent" />
        </div>
        <div className="flex items-center gap-1 bg-bg-secondary border border-border rounded-lg p-0.5">
          {[
            { key: "all", label: "All" },
            { key: "new", label: "New" },
            { key: "sent", label: "Sent" },
            { key: "contacted", label: "Contacted" },
            { key: "draft", label: "Drafts" },
            { key: "bank", label: "HR Bank" },
          ].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${filter === f.key ? "bg-accent/10 text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
              {f.label}
            </button>
          ))}
        </div>
        <button onClick={loadHistory} className="p-2 rounded-lg border border-border text-fg-muted hover:text-fg-primary transition-colors">
          <Loader2 size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Results count */}
      <div className="text-xs text-fg-muted">{filtered.length} contact{filtered.length !== 1 ? "s" : ""}{q && ` matching "${search}"`}</div>

      {/* Contact table */}
      <div className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-12 gap-2 px-4 py-2.5 border-b border-border text-[10px] font-semibold text-fg-muted uppercase tracking-wider">
          <div className="col-span-2">Company</div>
          <div className="col-span-2">Role</div>
          <div className="col-span-2">Email</div>
          <div className="col-span-1">Phone</div>
          <div className="col-span-1">Location</div>
          <div className="col-span-1">Exp</div>
          <div className="col-span-1">Mode</div>
          <div className="col-span-1">Status</div>
          <div className="col-span-1">Posted</div>
        </div>

        {/* Rows */}
        {filtered.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-fg-muted">No contacts match your filters.</div>
        ) : (
          filtered.slice(0, 100).map((c) => (
            <div key={c.id}>
              {/* Summary row */}
              <div className="grid grid-cols-12 gap-2 px-4 py-2.5 border-b border-border/30 hover:bg-bg-tertiary/30 cursor-pointer items-center text-xs"
                onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}>
                <div className="col-span-2 font-medium text-fg-primary truncate">{c.company || "—"}</div>
                <div className="col-span-2 text-fg-secondary truncate">{c.role || "—"}</div>
                <div className="col-span-2 text-accent truncate">{c.recipient_email}</div>
                <div className="col-span-1 truncate">
                  {c.phone ? <span className="text-success">{c.phone.split(",")[0]}</span> : <span className="text-fg-muted">—</span>}
                </div>
                <div className="col-span-1 text-fg-secondary truncate">{c.location || "—"}</div>
                <div className="col-span-1 text-fg-secondary">{c.experience || "—"}</div>
                <div className="col-span-1 text-fg-secondary">{c.work_mode || "—"}</div>
                <div className="col-span-1 space-y-0.5">
                  {c.status === "sent" && <span className="inline-flex items-center gap-0.5 text-success text-[10px]"><CheckCircle size={10} /> Sent</span>}
                  {c.status === "draft" && c.subject && <span className="inline-flex items-center gap-0.5 text-accent text-[10px]"><FileText size={10} /> Draft</span>}
                  {c.status === "draft" && !c.subject && <span className="inline-flex items-center gap-0.5 text-warning text-[10px]"><Database size={10} /> Bank</span>}
                  {c.status === "failed" && <span className="inline-flex items-center gap-0.5 text-danger text-[10px]"><AlertCircle size={10} /> Failed</span>}
                  {c.already_contacted && c.status !== "sent" && <span className="inline-flex items-center gap-0.5 text-success/60 text-[9px]"><Mail size={9} /> Contacted</span>}
                </div>
                <div className="col-span-1 text-fg-muted text-[10px]">{c.posted_at?.slice(5) || c.created_at?.split("T")[0]?.slice(5) || "—"}</div>
              </div>

              {/* Expanded detail */}
              {expandedId === c.id && (
                <div className="px-4 py-4 bg-bg-tertiary/20 border-b border-border/30 space-y-3">
                  <div className="grid grid-cols-4 gap-4">
                    <div>
                      <div className="text-[10px] text-fg-muted uppercase mb-1">Email</div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm text-accent">{c.recipient_email}</span>
                        <button onClick={() => copyToClipboard(c.recipient_email)} className="text-fg-muted hover:text-fg-primary"><Copy size={11} /></button>
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-fg-muted uppercase mb-1">Phone</div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm text-fg-secondary">{c.phone || "—"}</span>
                        {c.phone && <button onClick={() => copyToClipboard(c.phone)} className="text-fg-muted hover:text-fg-primary"><Copy size={11} /></button>}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-fg-muted uppercase mb-1">Company</div>
                      <span className="text-sm text-fg-primary font-medium">{c.company || "—"}</span>
                    </div>
                    <div>
                      <div className="text-[10px] text-fg-muted uppercase mb-1">Status</div>
                      <span className="text-sm text-fg-secondary">{c.status} {c.sent_at ? `on ${c.sent_at.split("T")[0]}` : ""}</span>
                    </div>
                  </div>
                  {c.hashtags && (
                    <div className="flex items-center gap-1 flex-wrap">
                      <Hash size={11} className="text-fg-muted" />
                      {c.hashtags.split(", ").map((tag, i) => <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-accent/8 text-accent/80">{tag}</span>)}
                    </div>
                  )}
                  {c.subject && (
                    <div className="mt-2 p-3 bg-bg-primary rounded-lg border border-border">
                      <div className="text-[10px] text-fg-muted uppercase mb-1">Email Sent</div>
                      <div className="text-sm font-medium text-fg-primary mb-1">{c.subject}</div>
                      <div className="text-xs text-fg-secondary whitespace-pre-line leading-relaxed">{c.body?.slice(0, 300)}{c.body?.length > 300 ? "..." : ""}</div>
                    </div>
                  )}
                  {c.error_message && (
                    <div className="text-xs text-danger flex items-center gap-1"><AlertCircle size={11} /> {c.error_message}</div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
      </>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT — with Paste / History top tabs
// ═══════════════════════════════════════════════════════════════════════════

export default function PasteOutreach() {
  const { toast } = useToast();
  const [view, setView] = useState("paste"); // "paste" | "history"

  const [stage, setStage] = useState("paste");
  const [rawText, setRawText] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extractProgress, setExtractProgress] = useState("");

  const [posts, setPosts] = useState([]);
  const [selected, setSelected] = useState(new Set());

  const [emails, setEmails] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState({ current: 0, total: 0 });
  const [attachResume, setAttachResume] = useState(true);
  const [sendingIdx, setSendingIdx] = useState(null);
  const [doneStats, setDoneStats] = useState({ sent: 0, drafted: 0 });

  const _extra = (p) => ({
    source: "pasted", phone: p.phone || "", hashtags: p.hashtags || "",
    work_mode: p.work_mode || "", company: p.company || "", role: p.role || "",
    location: p.location || "", experience: p.experience || "", posted_at: p.posted_at || "",
    skills_json: p.skills ? JSON.stringify(p.skills) : (p.skills_json || ""),
  });

  function splitIntoPosts(text) {
    const explicit = text.split(/\n\s*---+\s*\n|\n\s*===+\s*\n|\n\s*\n\s*\n/);
    if (explicit.length > 1) return explicit.map(c => c.trim()).filter(c => c.length >= 30);
    const lines = text.split('\n');
    const emojiRe = /^[\u{1F300}-\u{1FAD6}\u2600-\u27BF\u2B50]/u;
    const chunks = []; let current = [];
    for (const line of lines) {
      if (emojiRe.test(line.trim()) && current.length && current.join('\n').length >= 50) { chunks.push(current.join('\n')); current = [line]; }
      else current.push(line);
    }
    if (current.length) chunks.push(current.join('\n'));
    return chunks.length > 1 ? chunks.map(c => c.trim()).filter(c => c.length >= 30) : [text.trim()];
  }

  async function handleExtract() {
    if (!rawText.trim()) return;
    setExtracting(true);
    setExtractProgress("Analyzing posts...");
    try {
      const chunks = splitIntoPosts(rawText.trim());
      const BATCH_SIZE = 5;
      const allPosts = [];
      for (let batch = 0; batch < chunks.length; batch += BATCH_SIZE) {
        const batchChunks = chunks.slice(batch, batch + BATCH_SIZE);
        setExtractProgress(`Extracting ${Math.min(batch + BATCH_SIZE, chunks.length)}/${chunks.length} posts...`);
        const data = await api.pasteExtract(batchChunks.join("\n\n\n"));
        if (data.posts) for (const post of data.posts) { post.index = allPosts.length; allPosts.push(post); }
      }
      if (allPosts.length === 0) { toast({ type: "warning", title: "No contacts found" }); return; }
      setPosts(allPosts);
      // Auto-select only fit posts that haven't been contacted yet
      setSelected(new Set(allPosts.map((p, i) => (p.fit && !p.already_contacted) ? i : null).filter(i => i !== null)));
      setStage("review");
      setExtractProgress("Saving contacts...");
      for (const post of allPosts.filter(p => p.email)) {
        try { await api.saveDraft({ post_id: 0, to_email: post.email, subject: "", body: "", ..._extra(post) }); } catch {}
      }
      const fitCount = allPosts.filter(p => p.fit).length;
      toast({ type: "success", title: `${allPosts.length} contacts extracted`, description: `${fitCount} eligible, ${allPosts.length - fitCount} saved to HR bank` });
    } catch (err) { toast({ type: "error", title: "Extraction failed", description: err.message }); }
    finally { setExtracting(false); setExtractProgress(""); }
  }

  async function handleGenerate() {
    const postsWithEmail = posts.filter((_, i) => selected.has(i)).filter(p => p.email);
    if (postsWithEmail.length === 0) { toast({ type: "warning", title: "No emails to generate" }); return; }
    setGenerating(true);
    setGenProgress({ current: 0, total: postsWithEmail.length });
    const generated = [];
    for (let i = 0; i < postsWithEmail.length; i++) {
      const post = postsWithEmail[i];
      setGenProgress({ current: i + 1, total: postsWithEmail.length });
      try {
        const result = await api.generateEmail({ post_id: 0, author_name: post.author_name || "", author_headline: post.author_headline || "", role: post.role || "", company: post.company || "", location: post.location || "", domain_relevance: post.domain_relevance || "", is_hiring: post.is_hiring ?? true, content: post.content || "", to_email: post.email });
        generated.push({ ...post, to_email: post.email, subject: result.subject || "", body: result.body || "", status: "draft" });
      } catch (err) { generated.push({ ...post, to_email: post.email, subject: "", body: "", status: "error", error: err.message }); }
    }
    setEmails(generated);
    setGenerating(false);
    setStage("emails");
    toast({ type: "success", title: `${generated.filter(e => e.status !== "error").length} emails generated` });
  }

  async function handleSend(idx) {
    setSendingIdx(idx);
    try {
      await api.sendEmail({ post_id: 0, to_email: emails[idx].to_email, subject: emails[idx].subject, body: emails[idx].body, attach_resume: attachResume, ..._extra(emails[idx]) });
      setEmails(prev => prev.map((e, i) => i === idx ? { ...e, status: "sent" } : e));
      toast({ type: "success", title: `Sent to ${emails[idx].to_email}` });
    } catch (err) { toast({ type: "error", title: "Send failed", description: err.message }); }
    finally { setSendingIdx(null); }
  }

  async function handleSaveDraft(idx) {
    try {
      await api.saveDraft({ post_id: 0, to_email: emails[idx].to_email, subject: emails[idx].subject, body: emails[idx].body, ..._extra(emails[idx]) });
      setEmails(prev => prev.map((e, i) => i === idx ? { ...e, status: "saved" } : e));
      toast({ type: "success", title: "Draft saved" });
    } catch (err) { toast({ type: "error", title: "Save failed" }); }
  }

  async function handleSendAll() {
    let sent = 0, failed = 0;
    for (let i = 0; i < emails.length; i++) {
      if (emails[i].status !== "draft" || !emails[i].subject) continue;
      setSendingIdx(i);
      try { await api.sendEmail({ post_id: 0, to_email: emails[i].to_email, subject: emails[i].subject, body: emails[i].body, attach_resume: attachResume, ..._extra(emails[i]) }); setEmails(prev => prev.map((em, j) => j === i ? { ...em, status: "sent" } : em)); sent++; }
      catch { failed++; }
      setSendingIdx(null);
    }
    setDoneStats({ sent, drafted: 0 });
    if (sent > 0) setStage("done");
    toast({ type: sent > 0 ? "success" : "error", title: `${sent} sent${failed > 0 ? `, ${failed} failed` : ""}` });
  }

  async function handleSaveAllDrafts() {
    let saved = 0;
    for (let i = 0; i < emails.length; i++) {
      if (emails[i].status !== "draft" || !emails[i].subject) continue;
      try { await api.saveDraft({ post_id: 0, to_email: emails[i].to_email, subject: emails[i].subject, body: emails[i].body, ..._extra(emails[i]) }); setEmails(prev => prev.map((em, j) => j === i ? { ...em, status: "saved" } : em)); saved++; }
      catch {}
    }
    setDoneStats({ sent: 0, drafted: saved });
    if (saved > 0) setStage("done");
    toast({ type: "success", title: `${saved} drafts saved` });
  }

  function handleReset() {
    setStage("paste"); setRawText(""); setPosts([]); setSelected(new Set()); setEmails([]); setDoneStats({ sent: 0, drafted: 0 });
  }

  const postCount = rawText.trim() ? splitIntoPosts(rawText.trim()).length : 0;
  const fitPosts = posts.map((p, i) => ({ ...p, _idx: i })).filter(p => p.fit);
  const bankPosts = posts.map((p, i) => ({ ...p, _idx: i })).filter(p => !p.fit);
  const draftEmails = emails.filter(e => e.status === "draft");

  return (
    <div className="px-10 py-6 max-w-5xl">

      {/* ── Top tabs: Paste | History ── */}
      <div className="flex items-center gap-1 mb-6 bg-bg-secondary border border-border rounded-lg p-0.5 w-fit">
        <button onClick={() => setView("paste")}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors ${view === "paste" ? "bg-accent/10 text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
          <ClipboardPaste size={14} /> Paste & Send
        </button>
        <button onClick={() => setView("history")}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors ${view === "history" ? "bg-accent/10 text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
          <History size={14} /> Contact History
        </button>
      </div>

      {/* ── History view ── */}
      {view === "history" && <HistoryDashboard />}

      {/* ── Paste flow ── */}
      {view === "paste" && (
        <>
          <StepIndicator current={stage === "done" ? "emails" : stage} />

          {/* STAGE 1: PASTE */}
          {stage === "paste" && (
            <div className="space-y-4">
              <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-border/50">
                  <div className="flex items-center gap-2">
                    <FileText size={15} className="text-accent" />
                    <span className="text-sm font-semibold text-fg-primary">Paste LinkedIn Hiring Posts</span>
                  </div>
                  <span className="text-[11px] text-fg-muted">Separate posts with <code className="px-1.5 py-0.5 rounded bg-bg-tertiary text-fg-secondary font-mono">---</code></span>
                </div>
                <textarea value={rawText} onChange={(e) => setRawText(e.target.value)} rows={16} autoFocus
                  placeholder={"3d\n🚀 Company A is Hiring – AI Engineer\nExperience: 2-3 years | Remote\n📩 hr@company-a.com\n---\n1w\n🔥 Company B – ML Engineer\n📩 jobs@company-b.com\n\n(Tip: add 3d, 1w, 2mo at the start of each post for when it was posted)"}
                  className="w-full bg-bg-primary px-5 py-4 text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none resize-y font-mono leading-relaxed" />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {postCount > 0 && <span className="inline-flex items-center gap-1.5 text-xs text-fg-muted"><FileText size={11} />{postCount} post{postCount > 1 ? "s" : ""}</span>}
                </div>
                <div className="flex items-center gap-2">
                  {rawText.trim() && <button onClick={() => setRawText("")} className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-fg-muted text-xs hover:text-fg-primary transition-colors"><X size={12} /> Clear</button>}
                  <button onClick={handleExtract} disabled={!rawText.trim() || extracting}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-accent text-white text-sm font-semibold hover:bg-accent/90 transition-all disabled:opacity-50 shadow-lg shadow-accent/20">
                    {extracting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                    {extracting ? extractProgress : "Extract & Analyze"}
                    {!extracting && <ArrowRight size={14} />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STAGE 2: REVIEW */}
          {stage === "review" && (
            <div className="space-y-5">
              <div className="grid grid-cols-4 gap-3">
                {[
                  { v: posts.length, l: "Total Extracted", c: "text-fg-primary" },
                  { v: fitPosts.length, l: "Eligible", c: "text-success" },
                  { v: bankPosts.length, l: "HR Bank", c: "text-warning" },
                  { v: selected.size, l: "Selected", c: "text-accent" },
                ].map((s, i) => (
                  <div key={i} className="bg-bg-secondary border border-border rounded-xl px-4 py-3 text-center">
                    <div className={`text-xl font-bold ${s.c}`}>{s.v}</div>
                    <div className="text-[10px] text-fg-muted mt-0.5">{s.l}</div>
                  </div>
                ))}
              </div>
              {fitPosts.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-fg-muted uppercase tracking-wider flex items-center gap-1.5"><CheckCircle size={12} className="text-success" /> Ready for Outreach ({fitPosts.length})</h3>
                    <button onClick={() => { const all = fitPosts.every(p => selected.has(p._idx)); setSelected(prev => { const n = new Set(prev); fitPosts.forEach(p => all ? n.delete(p._idx) : n.add(p._idx)); return n; }); }} className="text-[11px] text-accent hover:underline">{fitPosts.every(p => selected.has(p._idx)) ? "Deselect all" : "Select all"}</button>
                  </div>
                  {fitPosts.map(post => <ContactCard key={post._idx} post={post} selected={selected.has(post._idx)} defaultCollapsed={fitPosts.length > 5} onToggle={() => setSelected(prev => { const n = new Set(prev); n.has(post._idx) ? n.delete(post._idx) : n.add(post._idx); return n; })} onEmailChange={(val) => setPosts(prev => prev.map((p, j) => j === post._idx ? { ...p, email: val } : p))} />)}
                </div>
              )}
              {bankPosts.length > 0 && (
                <details className="group">
                  <summary className="flex items-center gap-1.5 cursor-pointer text-xs font-semibold text-fg-muted uppercase tracking-wider list-none select-none py-2">
                    <ChevronDown size={12} className="text-warning group-open:rotate-180 transition-transform" /> <Database size={12} className="text-warning" /> HR Email Bank ({bankPosts.length}) — saved for future cold emailing
                  </summary>
                  <div className="space-y-2 mt-2">
                    {bankPosts.map(post => <ContactCard key={post._idx} post={post} selected={selected.has(post._idx)} defaultCollapsed onToggle={() => setSelected(prev => { const n = new Set(prev); n.has(post._idx) ? n.delete(post._idx) : n.add(post._idx); return n; })} onEmailChange={(val) => setPosts(prev => prev.map((p, j) => j === post._idx ? { ...p, email: val } : p))} />)}
                  </div>
                </details>
              )}
              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <button onClick={() => setStage("paste")} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-fg-muted text-sm hover:text-fg-primary transition-colors"><ArrowLeft size={13} /> Edit Posts</button>
                <button onClick={handleGenerate} disabled={selected.size === 0 || generating}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-accent text-white text-sm font-semibold hover:bg-accent/90 transition-all disabled:opacity-50 shadow-lg shadow-accent/20">
                  {generating ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                  {generating ? `Generating ${genProgress.current}/${genProgress.total}...` : `Generate ${selected.size} Email${selected.size > 1 ? "s" : ""}`}
                  {!generating && <ArrowRight size={14} />}
                </button>
              </div>
            </div>
          )}

          {/* STAGE 3: EMAILS */}
          {stage === "emails" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-fg-primary">{draftEmails.length > 0 ? `${draftEmails.length} email${draftEmails.length > 1 ? "s" : ""} ready` : "All processed"}</h2>
                  <p className="text-xs text-fg-muted mt-0.5">Review, edit, then send or save as drafts</p>
                </div>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1.5 text-xs text-fg-muted cursor-pointer select-none mr-2">
                    <input type="checkbox" checked={attachResume} onChange={() => setAttachResume(!attachResume)} className="rounded border-border text-accent focus:ring-accent w-3.5 h-3.5" />
                    <Paperclip size={11} /> Resume
                  </label>
                  <button onClick={handleSaveAllDrafts} disabled={draftEmails.length === 0} className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-border text-fg-muted text-xs hover:text-fg-primary transition-colors disabled:opacity-50"><Save size={12} /> Save All</button>
                  <button onClick={handleSendAll} disabled={draftEmails.length === 0} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-success text-white text-xs font-semibold hover:bg-success/90 transition-colors disabled:opacity-50 shadow-lg shadow-success/20"><Send size={12} /> Send All ({draftEmails.length})</button>
                </div>
              </div>
              <div className="space-y-2.5">
                {emails.map((email, i) => <EmailCard key={i} email={email} attachResume={attachResume} onToggleResume={() => setAttachResume(!attachResume)} onSubjectChange={(val) => setEmails(prev => prev.map((e, j) => j === i ? { ...e, subject: val } : e))} onBodyChange={(val) => setEmails(prev => prev.map((e, j) => j === i ? { ...e, body: val } : e))} onSend={() => handleSend(i)} onSaveDraft={() => handleSaveDraft(i)} sending={sendingIdx === i} />)}
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <button onClick={() => setStage("review")} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-fg-muted text-sm hover:text-fg-primary transition-colors"><ArrowLeft size={13} /> Back to Review</button>
                <button onClick={() => setView("history")} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-fg-muted text-sm hover:text-fg-primary transition-colors"><History size={13} /> View History</button>
              </div>
            </div>
          )}

          {/* STAGE 4: DONE */}
          {stage === "done" && (
            <div className="flex flex-col items-center justify-center py-16 space-y-5">
              <div className="w-16 h-16 rounded-2xl bg-success/10 flex items-center justify-center"><CheckCircle size={32} className="text-success" /></div>
              <div className="text-center">
                <h2 className="text-xl font-semibold text-fg-primary">All Done!</h2>
                <p className="text-sm text-fg-muted mt-2 max-w-sm">
                  {doneStats.sent > 0 && <><span className="text-success font-medium">{doneStats.sent}</span> email{doneStats.sent > 1 ? "s" : ""} sent. </>}
                  {doneStats.drafted > 0 && <><span className="text-accent font-medium">{doneStats.drafted}</span> draft{doneStats.drafted > 1 ? "s" : ""} saved. </>}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={handleReset} className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-accent text-white text-sm font-semibold hover:bg-accent/90 transition-all shadow-lg shadow-accent/20"><ClipboardPaste size={14} /> Paste More</button>
                <button onClick={() => setView("history")} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border text-fg-secondary text-sm font-medium hover:text-fg-primary transition-colors"><History size={14} /> View History</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
