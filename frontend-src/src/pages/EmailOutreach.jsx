import { useState, useEffect, useRef } from "react";
import {
  Mail,
  Sparkles,
  RefreshCw,
  Send,
  Zap,
  Clock,
  CheckCircle,
  AlertCircle,
  User,
  X,
  Eye,
  Paperclip,
  Save,
  FileText,
  ChevronDown,
  ChevronUp,
  Square,
  Search,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }) {
  const s = status?.toLowerCase();
  if (s === "sent")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-success-bg text-success">
        <CheckCircle size={10} /> Sent
      </span>
    );
  if (s === "draft")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-accent-bg text-accent">
        <FileText size={10} /> Draft
      </span>
    );
  if (s === "generating")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-warning-bg text-warning">
        <RefreshCw size={10} className="animate-spin" /> Generating
      </span>
    );
  if (s === "failed")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-danger-bg text-danger">
        <AlertCircle size={10} /> Failed
      </span>
    );
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-bg-tertiary text-fg-muted">
      {status || "Pending"}
    </span>
  );
}

function RelevanceDot({ value }) {
  const v = value?.toLowerCase();
  if (v === "high") return <span className="w-2 h-2 rounded-full bg-accent inline-block" title="High" />;
  if (v === "medium") return <span className="w-2 h-2 rounded-full bg-warning inline-block" title="Medium" />;
  return <span className="w-2 h-2 rounded-full bg-fg-muted/30 inline-block" title="Low" />;
}

function ConfirmModal({ title, description, confirmLabel = "Confirm", cancelLabel = "Cancel", onConfirm, onCancel, danger = false }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onCancel}>
      <div className="relative bg-bg-secondary border border-border rounded-xl w-full max-w-md mx-4 shadow-2xl shadow-black/60" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between px-5 py-4 border-b border-border">
          <p className="text-base font-semibold text-fg-primary">{title}</p>
          <button onClick={onCancel} className="p-1 rounded-lg text-fg-muted hover:text-fg-primary hover:bg-bg-tertiary transition-colors"><X size={16} /></button>
        </div>
        <div className="px-5 py-4"><p className="text-sm text-fg-secondary leading-relaxed">{description}</p></div>
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-border">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors">{cancelLabel}</button>
          <button onClick={onConfirm} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${danger ? "bg-danger text-white hover:bg-danger/90" : "bg-accent text-white hover:bg-accent/90"}`}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

/** Expandable email row */
function EmailRow({ post, onGenerate, onSend, onSaveDraft, attachResume, generatingId }) {
  const [expanded, setExpanded] = useState(false);
  const [editSubject, setEditSubject] = useState(post.draft_subject || "");
  const [editBody, setEditBody] = useState(post.draft_body || "");
  const [sending, setSending] = useState(false);

  const isGenerating = generatingId === post.id;
  const hasDraft = !!(post.draft_subject && post.draft_body);
  const isSent = post.email_status === "sent";

  useEffect(() => {
    if (post.draft_subject) setEditSubject(post.draft_subject);
    if (post.draft_body) setEditBody(post.draft_body);
  }, [post.draft_subject, post.draft_body]);

  const handleSend = async () => {
    setSending(true);
    await onSend(post, editSubject, editBody);
    setSending(false);
  };

  const contentPreview = (post.content || "").slice(0, 120).replace(/\n/g, " ");

  return (
    <div className={`border-b border-border last:border-0 ${isSent ? "opacity-60" : ""}`}>
      <div className="flex items-center gap-3 px-5 py-3.5 hover:bg-bg-tertiary/40 cursor-pointer transition-colors" onClick={() => setExpanded((v) => !v)}>
        <RelevanceDot value={post.domain_relevance} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-fg-primary truncate max-w-[160px]">{post.author_name || "Unknown"}</span>
            {post.company && <span className="text-xs text-fg-muted truncate max-w-[120px]">@ {post.company}</span>}
            {post.role && <span className="text-xs text-accent bg-accent-bg px-1.5 py-0.5 rounded truncate max-w-[150px]">{post.role}</span>}
            {post.source_type === "startup_lead" && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-success/10 text-success font-medium">Company</span>
            )}
          </div>
          <p className="text-xs text-fg-muted mt-0.5 truncate">{contentPreview}...</p>
        </div>
        <span className="font-mono text-xs text-info shrink-0">{post.email}</span>
        <StatusBadge status={isGenerating ? "generating" : post.email_status} />
        {expanded ? <ChevronUp size={14} className="text-fg-muted shrink-0" /> : <ChevronDown size={14} className="text-fg-muted shrink-0" />}
      </div>

      {expanded && (
        <div className="px-5 pb-4 pt-1 bg-bg-tertiary/20">
          <details className="mb-3">
            <summary className="text-xs text-fg-muted cursor-pointer hover:text-fg-secondary">View original post</summary>
            <p className="mt-2 text-xs text-fg-secondary whitespace-pre-wrap leading-relaxed bg-bg-primary rounded-lg p-3 max-h-40 overflow-y-auto border border-border">{post.content || "No content"}</p>
            {post.links && (
              <div className="mt-2 px-3 py-2 bg-bg-primary rounded-lg border border-border">
                <span className="text-xs font-medium text-fg-muted">Links: </span>
                {post.links.split(", ").map((link, i) => (
                  <a key={i} href={link} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline mr-2 break-all">{link}</a>
                ))}
              </div>
            )}
          </details>

          <div className="mb-2">
            <label className="block text-xs font-medium text-fg-muted mb-1">Subject</label>
            <input type="text" value={editSubject} onChange={(e) => setEditSubject(e.target.value)} placeholder="Generate email first..." disabled={isSent}
              className="w-full bg-bg-primary border border-border text-fg-primary text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50 placeholder:text-fg-muted" />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-fg-muted mb-1">Email Body</label>
            <textarea value={editBody} onChange={(e) => setEditBody(e.target.value)} placeholder="Generate email first..." disabled={isSent} rows={8}
              className="w-full bg-bg-primary border border-border text-fg-primary text-sm font-mono rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50 placeholder:text-fg-muted resize-none" />
          </div>

          {!isSent && (
            <div className="flex items-center gap-2 flex-wrap">
              <button onClick={() => onGenerate(post.id)} disabled={isGenerating}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-fg-secondary text-xs hover:text-fg-primary disabled:opacity-50 transition-colors">
                {isGenerating ? <RefreshCw size={12} className="animate-spin" /> : <Sparkles size={12} />}
                {isGenerating ? "Generating..." : hasDraft ? "Regenerate" : "Generate Email"}
              </button>
              {hasDraft && (
                <>
                  <button onClick={() => onSaveDraft(post, editSubject, editBody)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-fg-secondary text-xs hover:text-fg-primary transition-colors">
                    <Save size={12} /> Save Draft
                  </button>
                  <button onClick={handleSend} disabled={sending || !editSubject || !editBody}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-white text-xs font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors">
                    {sending ? <RefreshCw size={12} className="animate-spin" /> : <Send size={12} />}
                    {sending ? "Sending..." : "Send Email"}
                  </button>
                </>
              )}
              <span className="ml-auto flex items-center gap-1.5 text-xs text-fg-muted">
                <Paperclip size={11} /> {attachResume ? "Resume attached" : "No resume"}
              </span>
            </div>
          )}
          {isSent && (
            <div className="flex items-center gap-2 text-xs text-success">
              <CheckCircle size={12} /> Sent {post.sent_at ? new Date(post.sent_at).toLocaleString() : ""}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Sent email row — expandable to show original post + email sent */
function SentEmailRow({ item }) {
  const [expanded, setExpanded] = useState(false);
  const sentDate = item.sent_at
    ? new Date(item.sent_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <div className="border-b border-border last:border-0">
      {/* Collapsed */}
      <div
        className="flex items-center gap-2.5 px-4 py-3 hover:bg-bg-tertiary/40 cursor-pointer transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="w-7 h-7 rounded-full bg-success-bg flex items-center justify-center shrink-0">
          <CheckCircle size={12} className="text-success" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-fg-primary truncate">
              {item.to_name || item.to_email}
            </span>
            {item.company && (
              <span className="text-xs text-fg-muted">@ {item.company}</span>
            )}
          </div>
          <p className="text-xs text-fg-muted truncate mt-0.5">{item.subject}</p>
          <p className="text-xs text-info font-mono truncate mt-0.5">{item.to_email}</p>
        </div>
        <span className="text-xs text-fg-muted/60 shrink-0">{sentDate}</span>
        {expanded ? <ChevronUp size={12} className="text-fg-muted shrink-0" /> : <ChevronDown size={12} className="text-fg-muted shrink-0" />}
      </div>

      {/* Expanded — full width detail view */}
      {expanded && (
        <div className="px-5 pb-4 space-y-3">
          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {item.role && (
              <span className="px-2 py-0.5 rounded bg-accent-bg text-accent font-medium">{item.role}</span>
            )}
            {item.company && (
              <span className="px-2 py-0.5 rounded bg-bg-tertiary text-fg-secondary">@ {item.company}</span>
            )}
            {item.location && (
              <span className="text-fg-muted">{item.location}</span>
            )}
            {item.domain_relevance && (
              <span className={`px-2 py-0.5 rounded ${item.domain_relevance === "High" ? "bg-accent-bg text-accent" : item.domain_relevance === "Medium" ? "bg-warning-bg text-warning" : "bg-bg-tertiary text-fg-muted"}`}>
                {item.domain_relevance}
              </span>
            )}
            {item.author_headline && (
              <span className="text-fg-muted italic truncate max-w-[300px]">{item.author_headline}</span>
            )}
            <span className="text-info font-mono ml-auto">{item.to_email}</span>
          </div>

          {/* Two-column: Original Post | Email Sent */}
          <div className="grid grid-cols-2 gap-4">
            {/* Original post */}
            <div className="rounded-lg border border-border overflow-hidden flex flex-col">
              <div className="px-4 py-2.5 bg-bg-tertiary border-b border-border flex items-center gap-1.5">
                <Eye size={12} className="text-fg-muted" />
                <span className="text-xs font-semibold text-fg-primary">Original Post</span>
                {item.post_url && (
                  <a href={item.post_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline ml-auto">Open on LinkedIn</a>
                )}
              </div>
              {item.post_content ? (
                <div className="flex-1 overflow-y-auto max-h-64 px-4 py-3">
                  <p className="text-xs text-fg-secondary whitespace-pre-wrap leading-relaxed">
                    {item.post_content}
                  </p>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center px-4 py-8 text-xs text-fg-muted">
                  No post content available
                </div>
              )}
              {item.post_links && (
                <div className="px-4 py-2 border-t border-border bg-bg-tertiary/50">
                  <span className="text-xs text-fg-muted font-medium">Links: </span>
                  <div className="flex flex-col gap-0.5 mt-1">
                    {item.post_links.split(", ").map((link, i) => (
                      <a key={i} href={link} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-accent hover:underline break-all">{link}</a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Email sent */}
            <div className="rounded-lg border border-border overflow-hidden flex flex-col">
              <div className="px-4 py-2.5 bg-bg-tertiary border-b border-border flex items-center gap-1.5">
                <Mail size={12} className="text-fg-muted" />
                <span className="text-xs font-semibold text-fg-primary">Email You Sent</span>
                <span className="text-xs text-fg-muted/60 ml-auto">{sentDate}</span>
              </div>
              <div className="px-4 py-2 border-b border-border">
                <div className="flex items-baseline gap-2 text-xs">
                  <span className="text-fg-muted shrink-0">To:</span>
                  <span className="text-info font-mono">{item.to_email}</span>
                </div>
                <div className="flex items-baseline gap-2 text-xs mt-1">
                  <span className="text-fg-muted shrink-0">Subject:</span>
                  <span className="text-fg-primary font-medium">{item.subject}</span>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto max-h-64 px-4 py-3">
                <p className="text-xs text-fg-secondary whitespace-pre-wrap leading-relaxed font-mono">
                  {item.body}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function EmailOutreach() {
  const { toast } = useToast();

  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [attachResume, setAttachResume] = useState(true);
  const [generatingId, setGeneratingId] = useState(null);

  // Background worker state (polled)
  const [worker, setWorker] = useState({ running: false, task: null, current: 0, total: 0, current_label: "", succeeded: 0, failed: 0 });
  const pollRef = useRef(null);

  // Confirmation modals
  const [bulkGenConfirm, setBulkGenConfirm] = useState(false);
  const [bulkSendConfirm, setBulkSendConfirm] = useState(false);

  // Tabs & search
  const [activeTab, setActiveTab] = useState("queue");
  const [search, setSearch] = useState("");

  // History
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    loadPosts();
    loadHistory();
    startPolling();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const prevRunningRef = useRef(false);

  function startPolling() {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const ws = await api.getEmailWorkerStatus();
        setWorker(ws);
        // Auto-refresh only on transition: running → finished (not every tick)
        if (prevRunningRef.current && !ws.running && ws.total > 0) {
          loadPosts();
          loadHistory();
        }
        prevRunningRef.current = ws.running;
      } catch { /* ignore */ }
    }, 2000);
  }

  async function loadPosts() {
    setLoading(true);
    try {
      const data = await api.getOutreachReady();
      setPosts(data.posts || []);
    } catch (err) {
      toast({ type: "error", title: "Failed to load posts", description: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    setHistoryLoading(true);
    try {
      const data = await api.getEmailHistory();
      setHistory((data.history || []).filter((h) => h.status === "sent"));
    } catch { /* silent */ }
    finally { setHistoryLoading(false); }
  }

  // Generate single email (non-blocking for other operations)
  async function handleGenerate(postId) {
    setGeneratingId(postId);
    try {
      const data = await api.generateEmail({ post_id: postId });
      setPosts((prev) => prev.map((p) => p.id === postId ? { ...p, draft_subject: data.subject, draft_body: data.body, email_status: "draft" } : p));
      const post = posts.find((p) => p.id === postId);
      if (post) await api.saveDraft({ post_id: postId, to_email: post.email, subject: data.subject, body: data.body });
      toast({ type: "success", title: "Email generated" });
    } catch (err) {
      toast({ type: "error", title: "Generation failed", description: err.message });
    } finally {
      setGeneratingId(null);
    }
  }

  // Bulk generate — fires & forgets, UI polls for progress
  async function handleBulkGenerate() {
    setBulkGenConfirm(false);
    try {
      const res = await api.bulkGenerate({ post_ids: [] });
      toast({ type: "success", title: "Bulk generation started", description: res.message });
    } catch (err) {
      toast({ type: "error", title: "Failed to start", description: err.message });
    }
  }

  // Send single email
  async function handleSend(post, subject, body) {
    try {
      await api.sendEmail({ post_id: post.id, to_email: post.email, subject, body, attach_resume: attachResume });
      setPosts((prev) => prev.map((p) => p.id === post.id ? { ...p, email_status: "sent", sent_at: new Date().toISOString() } : p));
      toast({ type: "success", title: "Email sent!", description: `Delivered to ${post.email}` });
      loadHistory();
    } catch (err) {
      toast({ type: "error", title: "Send failed", description: err.message });
    }
  }

  // Save draft
  async function handleSaveDraft(post, subject, body) {
    try {
      await api.saveDraft({ post_id: post.id, to_email: post.email, subject, body });
      setPosts((prev) => prev.map((p) => p.id === post.id ? { ...p, draft_subject: subject, draft_body: body, email_status: "draft" } : p));
      toast({ type: "success", title: "Draft saved" });
    } catch (err) {
      toast({ type: "error", title: "Save failed", description: err.message });
    }
  }

  // Bulk send — fires & forgets
  async function handleBulkSend() {
    setBulkSendConfirm(false);
    try {
      const res = await api.bulkSend({ attach_resume: attachResume });
      toast({ type: "success", title: "Bulk send started", description: res.message });
    } catch (err) {
      toast({ type: "error", title: "Failed to start", description: err.message });
    }
  }

  // Stop worker
  async function handleStopWorker() {
    try {
      await api.stopEmailWorker();
      toast({ type: "info", title: "Worker stopped" });
    } catch { /* ignore */ }
  }

  // Search filter — full text across all fields
  const q = search.trim().toLowerCase();
  const filteredPosts = q
    ? posts.filter((p) =>
        [p.author_name, p.company, p.role, p.email, p.content, p.draft_subject, p.draft_body, p.domain_relevance, p.links]
          .filter(Boolean).join(" ").toLowerCase().includes(q)
      )
    : posts;
  const filteredHistory = q
    ? history.filter((h) =>
        [h.to_name, h.to_email, h.company, h.role, h.subject, h.body, h.post_content, h.location, h.post_links, h.author_headline]
          .filter(Boolean).join(" ").toLowerCase().includes(q)
      )
    : history;

  // Stats
  const totalPosts = posts.length;
  const draftCount = posts.filter((p) => p.email_status === "draft").length;
  const sentCount = posts.filter((p) => p.email_status === "sent").length;
  const pendingCount = totalPosts - draftCount - sentCount;
  const workerPct = worker.total > 0 ? Math.round((worker.current / worker.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-bg"><Mail size={20} className="text-accent" /></div>
            <div>
              <h1 className="text-2xl font-semibold text-fg-primary">Email Outreach</h1>
              <p className="text-sm text-fg-secondary mt-0.5">Generate, review, edit &amp; send personalized emails</p>
            </div>
          </div>
          <button onClick={loadPosts} disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-bg-secondary rounded-xl border border-border px-4 py-3">
            <div className="text-2xl font-bold text-fg-primary">{totalPosts}</div>
            <div className="text-xs text-fg-muted mt-0.5">Ready to Email</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-accent font-medium">{posts.filter(p => p.source_type === "post").length} posts</span>
              <span className="text-xs text-fg-muted">+</span>
              <span className="text-xs text-success font-medium">{posts.filter(p => p.source_type === "startup_lead").length} companies</span>
            </div>
          </div>
          <div className="bg-bg-secondary rounded-xl border border-border px-4 py-3">
            <div className="text-2xl font-bold text-warning">{pendingCount}</div>
            <div className="text-xs text-fg-muted mt-0.5">Not Generated</div>
          </div>
          <div className="bg-bg-secondary rounded-xl border border-border px-4 py-3">
            <div className="text-2xl font-bold text-accent">{draftCount}</div>
            <div className="text-xs text-fg-muted mt-0.5">Drafts Ready</div>
          </div>
          <div className="bg-bg-secondary rounded-xl border border-border px-4 py-3">
            <div className="text-2xl font-bold text-success">{history.length}</div>
            <div className="text-xs text-fg-muted mt-0.5">Sent</div>
          </div>
        </div>

        {/* Background worker progress bar */}
        {worker.running && (
          <div className="mb-4 bg-bg-secondary rounded-xl border border-border px-4 py-3">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2 text-sm">
                <RefreshCw size={13} className="animate-spin text-accent" />
                <span className="text-fg-primary font-medium">
                  {worker.task === "generating" ? "Generating emails" : "Sending emails"}
                </span>
                <span className="text-fg-muted text-xs">
                  {worker.current}/{worker.total} — {worker.current_label}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-fg-muted">{workerPct}% — {worker.succeeded} ok, {worker.failed} failed</span>
                <button onClick={handleStopWorker}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-danger/10 text-danger text-xs hover:bg-danger/20 transition-colors">
                  <Square size={11} /> Stop
                </button>
              </div>
            </div>
            <div className="w-full h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-500 ${worker.task === "sending" ? "bg-success" : "bg-accent"}`}
                style={{ width: `${workerPct}%` }} />
            </div>
          </div>
        )}

        {/* Search bar */}
        <div className="relative mb-4">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
          <input
            type="text"
            placeholder="Search everything — name, company, role, email, post content, links..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-bg-secondary border border-border text-fg-primary text-sm rounded-lg pl-9 pr-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent placeholder:text-fg-muted"
          />
          {search && (
            <button onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg-primary">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Search results count */}
        {q && (
          <div className="mb-3 flex items-center gap-3 text-xs text-fg-muted">
            <span>Found <strong className="text-fg-secondary">{filteredPosts.length}</strong> in queue + <strong className="text-fg-secondary">{filteredHistory.length}</strong> in sent for "{search}"</span>
            {filteredHistory.length > 0 && activeTab !== "history" && (
              <button onClick={() => setActiveTab("history")}
                className="text-accent hover:underline">View in Sent History</button>
            )}
          </div>
        )}

        {/* Controls bar */}
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" checked={attachResume} onChange={(e) => setAttachResume(e.target.checked)}
              className="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-1" />
            <Paperclip size={13} className="text-fg-muted" />
            <span className="text-sm text-fg-secondary">Attach resume</span>
          </label>

          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => setBulkGenConfirm(true)} disabled={worker.running}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary disabled:opacity-50 transition-colors">
              <Sparkles size={14} /> Generate All
            </button>
            <button onClick={() => setBulkSendConfirm(true)} disabled={worker.running || draftCount === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors">
              <Zap size={14} /> Send All Drafts ({draftCount})
            </button>
          </div>
        </div>

        {/* Tabs: Queue | Sent History */}
        <div className="flex items-center gap-0 mb-4 border-b border-border">
          <button
            onClick={() => setActiveTab("queue")}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${activeTab === "queue" ? "border-accent text-accent" : "border-transparent text-fg-muted hover:text-fg-primary"}`}
          >
            Outreach Queue
            <span className="ml-1.5 text-xs opacity-70">({filteredPosts.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${activeTab === "history" ? "border-accent text-accent" : "border-transparent text-fg-muted hover:text-fg-primary"}`}
          >
            Sent History
            <span className="ml-1.5 text-xs opacity-70">({q ? `${filteredHistory.length}/` : ""}{history.length})</span>
          </button>
        </div>

        {/* Tab content */}
        {activeTab === "queue" && (
          <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="max-h-[calc(100vh-420px)] overflow-y-auto">
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="px-5 py-4 border-b border-border flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-bg-tertiary animate-pulse" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3.5 bg-bg-tertiary rounded animate-pulse w-3/4" />
                      <div className="h-3 bg-bg-tertiary rounded animate-pulse w-full" />
                    </div>
                  </div>
                ))
              ) : filteredPosts.length === 0 ? (
                <div className="px-5 py-16 text-center text-fg-muted text-sm">{q ? `No posts matching "${search}"` : "No eligible posts found."}</div>
              ) : (
                filteredPosts.map((post) => (
                  <EmailRow key={post.id} post={post} onGenerate={handleGenerate} onSend={handleSend}
                    onSaveDraft={handleSaveDraft} attachResume={attachResume} generatingId={generatingId} />
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === "history" && (
          <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="max-h-[calc(100vh-420px)] overflow-y-auto">
              {historyLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="px-5 py-4 border-b border-border flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-bg-tertiary animate-pulse" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3.5 bg-bg-tertiary rounded animate-pulse w-2/3" />
                      <div className="h-3 bg-bg-tertiary rounded animate-pulse w-full" />
                      <div className="h-3 bg-bg-tertiary rounded animate-pulse w-1/3" />
                    </div>
                  </div>
                ))
              ) : filteredHistory.length === 0 ? (
                <div className="px-5 py-16 text-center text-fg-muted text-sm">{q ? `No sent emails matching "${search}"` : "No emails sent yet."}</div>
              ) : (
                filteredHistory.map((item, idx) => (
                  <SentEmailRow key={item.id || idx} item={item} />
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {bulkGenConfirm && (
        <ConfirmModal title="Generate All Emails"
          description={`This will generate personalized emails for ${pendingCount} posts in the background. You can continue using the app while it runs. Continue?`}
          confirmLabel={`Generate ${pendingCount} Emails`} onConfirm={handleBulkGenerate} onCancel={() => setBulkGenConfirm(false)} />
      )}
      {bulkSendConfirm && (
        <ConfirmModal title="Send All Draft Emails"
          description={`This will send ${draftCount} draft emails in the background${attachResume ? " with your resume attached" : ""}. You can continue using the app. This cannot be undone.`}
          confirmLabel={`Send ${draftCount} Emails`} onConfirm={handleBulkSend} onCancel={() => setBulkSendConfirm(false)} danger />
      )}
    </div>
  );
}
