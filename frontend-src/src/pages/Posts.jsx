import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Download,
  RefreshCw,
  Mail,
  Eye,
  ChevronDown,
  ChevronUp,
  Database,
  X,
  Play,
  Square,
  Terminal,
  Loader2,
  SearchCheck,
  Zap,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";

const RELEVANCE_OPTIONS = [
  { label: "All Job Relevance", value: "" },
  { label: "High", value: "high" },
  { label: "Medium", value: "medium" },
  { label: "Low", value: "low" },
];

const HIRING_OPTIONS = [
  { label: "All", value: "" },
  { label: "Yes", value: "true" },
  { label: "No", value: "false" },
];

const SOURCE_OPTIONS = [
  { label: "All Sources", value: "" },
  { label: "LinkedIn", value: "linkedin" },
  { label: "Naukri", value: "naukri" },
  { label: "Wellfound", value: "wellfound" },
];

function HiringBadge({ value }) {
  if (value === true || value === "yes" || value === "true") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-bg text-success">
        Yes
      </span>
    );
  }
  if (value === "maybe") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-bg text-warning">
        Maybe
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-bg-tertiary text-fg-muted">
      No
    </span>
  );
}

function RelevanceBadge({ value }) {
  if (!value) return <span className="text-fg-muted">&mdash;</span>;
  const lower = value.toLowerCase();
  if (lower === "high") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-bg text-accent">
        High
      </span>
    );
  }
  if (lower === "medium") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-bg text-warning">
        Medium
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-bg-tertiary text-fg-muted">
      Low
    </span>
  );
}

function Select({ value, onChange, options }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-bg-secondary border border-border text-fg-primary text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={14}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-fg-muted pointer-events-none"
      />
    </div>
  );
}

function PostViewModal({ post, onClose, onEmailFound }) {
  if (!post) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative bg-bg-secondary border border-border rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl shadow-black/60 mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-border">
          <div>
            <p className="text-base font-semibold text-fg-primary">
              {post.author_name || "Unknown Author"}
            </p>
            {post.author_headline && (
              <p className="text-xs text-fg-muted mt-0.5">
                {post.author_headline}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-fg-muted hover:text-fg-primary hover:bg-bg-tertiary transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Badges row */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-border">
          <div className="flex items-center gap-1.5 text-xs text-fg-muted">
            <span>Hiring:</span>
            <HiringBadge value={post.is_hiring} />
          </div>
          <div className="flex items-center gap-1.5 text-xs text-fg-muted">
            <span>Job Relevance:</span>
            <RelevanceBadge value={post.domain_relevance} />
          </div>
          {post.email ? (
            <span className="font-mono text-xs text-info ml-auto">
              {post.email}
            </span>
          ) : (
            <FindEmailBtn postId={post.id} onFound={(email) => { onEmailFound(post.id, email); }} />
          )}
        </div>

        {/* Full post content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <p className="text-sm text-fg-secondary whitespace-pre-wrap leading-relaxed">
            {post.content || "No content available."}
          </p>
          {post.links && (
            <div className="mt-3 px-3 py-2 bg-bg-tertiary rounded-lg border border-border">
              <span className="text-xs font-medium text-fg-muted block mb-1">Links found in post:</span>
              <div className="flex flex-col gap-1">
                {post.links.split(", ").map((link, i) => (
                  <a key={i} href={link} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline break-all">{link}</a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary hover:border-fg-muted transition-colors"
          >
            Close
          </button>
          {post.email ? (
            <EmailButton post={post} />
          ) : (
            <FindEmailBtn postId={post.id} onFound={(email) => { onEmailFound(post.id, email); }} />
          )}
        </div>
      </div>
    </div>
  );
}

function EmailButton({ post }) {
  const navigate = useNavigate();
  const handleEmail = () => {
    const params = new URLSearchParams();
    params.set("to", post.email);
    if (post.id || post.post_id) params.set("postId", String(post.id || post.post_id));
    if (post.author_name) params.set("author", post.author_name);
    navigate(`/email?${params.toString()}`);
  };
  return (
    <button
      onClick={handleEmail}
      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors"
    >
      <Mail size={13} />
      Email
    </button>
  );
}

function FindEmailBtn({ postId, onFound }) {
  const [finding, setFinding] = useState(false);
  const [result, setResult] = useState(null);

  const handleFind = async (e) => {
    e.stopPropagation();
    setFinding(true);
    setResult(null);
    try {
      const data = await api.findEmailForPost(postId);
      setResult(data);
      if (data.saved && onFound) onFound(data.saved);
    } catch (err) {
      setResult({ status: "error", message: err.message });
    } finally {
      setFinding(false);
    }
  };

  if (result?.saved) {
    return (
      <span className="inline-flex items-center gap-1 ml-auto text-xs text-success font-mono">
        <SearchCheck size={12} />
        {result.saved}
      </span>
    );
  }

  return (
    <button
      onClick={handleFind}
      disabled={finding}
      className="inline-flex items-center gap-1 ml-auto px-2.5 py-1 rounded-md text-xs
        bg-accent/10 hover:bg-accent/20 text-accent transition-colors disabled:opacity-50"
    >
      {finding ? (
        <><Loader2 size={11} className="animate-spin" /> Searching...</>
      ) : (
        <><Zap size={11} /> Find Email</>
      )}
    </button>
  );
}

// ── Log entry formatting ──

function formatLogEntry(entry) {
  const t = entry.type;
  switch (t) {
    case "search":
      return {
        icon: "\u{1F50D}",
        color: "text-info",
        text: `Searching: ${entry.query} (${entry.index}/${entry.total})`,
      };
    case "found":
      return {
        icon: "\u2705",
        color: "text-success",
        text: `#${entry.sno} ${entry.author} | ${entry.role || "?"} @ ${entry.company || "?"} | ${entry.domain} | ${entry.email || "no email"}`,
      };
    case "skip":
      return {
        icon: "\u23ED\uFE0F",
        color: "text-fg-muted",
        text: `SKIP: ${entry.author} | ${entry.reason}`,
      };
    case "dedup":
      return {
        icon: "\u{1F504}",
        color: "text-warning",
        text: `DUP: ${entry.author} | Already seen`,
      };
    case "llm":
      return {
        icon: "\u{1F9E0}",
        color: "text-purple-400",
        text: `LLM extracting: ${entry.author}...`,
      };
    case "extract":
      return {
        icon: "\u{1F4E6}",
        color: "text-fg-secondary",
        text: `Extracted ${entry.count} raw posts from page`,
      };
    case "scroll":
      return {
        icon: "\u{1F4DC}",
        color: "text-fg-muted",
        text: entry.message,
      };
    case "saved":
      return {
        icon: "\u{1F4BE}",
        color: "text-success font-semibold",
        text: `Saved ${entry.count} posts (${entry.inserted} new, ${entry.skipped} duplicates)`,
      };
    case "query_done":
      return {
        icon: "\u2714\uFE0F",
        color: "text-fg-secondary",
        text: `Query done: ${entry.query} (${entry.found_count} total so far)`,
      };
    case "done":
      return {
        icon: "\u2705",
        color: "text-success font-bold",
        text: `Done! ${entry.total} posts from ${entry.queries_searched || "?"} queries`,
      };
    case "error":
      return {
        icon: "\u274C",
        color: "text-danger",
        text: `Error: ${entry.message}`,
      };
    default:
      return {
        icon: "\u2022",
        color: "text-fg-muted",
        text: JSON.stringify(entry),
      };
  }
}

// ── Scraper Panel ──

function ScraperPanel({ onScrapeDone }) {
  const { toast } = useToast();
  const [expanded, setExpanded] = useState(false);
  const [maxPosts, setMaxPosts] = useState(200);
  const [status, setStatus] = useState(null);
  const [starting, setStarting] = useState(false);
  const logEndRef = useRef(null);
  const pollRef = useRef(null);
  const prevLogCountRef = useRef(0);

  const isRunning = status?.running === true;
  const isDone = status?.status === "done";
  const isError = status?.status === "error";

  // Poll scraper status
  useEffect(() => {
    if (!expanded) return;

    const poll = async () => {
      try {
        const data = await api.getScraperStatus();
        setStatus(data);

        // Auto-stop polling when done
        if (data.status === "done" || data.status === "error") {
          if (data.status === "done" && prevLogCountRef.current > 0) {
            onScrapeDone?.();
          }
        }
        const sources = data.sources || {};
        const sourceKeys = Object.keys(sources);
        const activeSource = sourceKeys.find(k => sources[k].running) || sourceKeys[0];
        const sourceData = activeSource ? sources[activeSource] : {};
        prevLogCountRef.current = sourceData.log_count || 0;
      } catch {
        // ignore polling errors
      }
    };

    poll(); // initial
    pollRef.current = setInterval(poll, 1500);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [expanded, onScrapeDone]);

  // Auto-scroll log
  useEffect(() => {
    if (logEndRef.current && status?.log?.length) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [status?.log?.length]);

  const handleStart = async () => {
    setStarting(true);
    try {
      await api.startScraper({ max_posts: maxPosts });
      toast({ type: "success", title: "Scraper started", description: `Scraping up to ${maxPosts} posts...` });
    } catch (err) {
      toast({ type: "error", title: "Failed to start", description: err.message });
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    try {
      await api.stopScraper();
      toast({ type: "info", title: "Scraper stopped" });
    } catch (err) {
      toast({ type: "error", title: "Failed to stop", description: err.message });
    }
  };

  // Aggregate from status.sources - pick the active/first source
  const sources = status?.sources || {};
  const sourceKeys = Object.keys(sources);
  const activeSourceKey = sourceKeys.find(k => sources[k].running) || sourceKeys[0];
  const activeSourceData = activeSourceKey ? sources[activeSourceKey] : {};
  const progress = activeSourceData.progress || {};
  const logs = activeSourceData.log || [];
  const progressPct = progress.total_queries
    ? Math.round((progress.query_index / progress.total_queries) * 100)
    : 0;

  return (
    <div className="bg-bg-secondary border border-border rounded-xl mb-6 overflow-hidden">
      {/* Header bar */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-bg-tertiary/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Terminal size={16} className="text-accent" />
          <span className="text-sm font-medium text-fg-primary">Post Scraper</span>
          {isRunning && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-success-bg text-success">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
              Running
            </span>
          )}
          {isDone && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-success-bg text-success">
              Done
            </span>
          )}
          {isError && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-danger-bg text-danger">
              Error
            </span>
          )}
          {progress.posts_found > 0 && (
            <span className="text-xs text-fg-muted">
              {progress.posts_found} posts found
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp size={16} className="text-fg-muted" />
        ) : (
          <ChevronDown size={16} className="text-fg-muted" />
        )}
      </button>

      {/* Expanded panel */}
      {expanded && (
        <div className="border-t border-border">
          {/* Controls row */}
          <div className="flex items-center gap-3 px-5 py-3 border-b border-border">
            <label className="text-xs text-fg-muted whitespace-nowrap">Max posts:</label>
            <input
              type="number"
              min={10}
              max={2000}
              value={maxPosts}
              onChange={(e) => setMaxPosts(Number(e.target.value) || 100)}
              disabled={isRunning}
              className="w-20 bg-bg-primary border border-border text-fg-primary text-sm rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
            />
            {!isRunning ? (
              <button
                onClick={handleStart}
                disabled={starting}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-60 transition-colors"
              >
                {starting ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Play size={14} />
                )}
                Start Scraper
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-danger/90 text-white text-sm font-medium hover:bg-danger transition-colors"
              >
                <Square size={14} />
                Stop
              </button>
            )}

            {/* Progress info */}
            {(isRunning || isDone) && progress.current_query && (
              <div className="flex items-center gap-2 ml-auto text-xs text-fg-muted">
                <span>Query {progress.query_index}/{progress.total_queries}</span>
                <span className="text-fg-primary font-medium truncate max-w-[200px]">
                  {progress.current_query}
                </span>
              </div>
            )}
          </div>

          {/* Progress bar */}
          {(isRunning || isDone) && progress.total_queries > 0 && (
            <div className="px-5 py-2 border-b border-border">
              <div className="flex items-center justify-between text-xs text-fg-muted mb-1">
                <span>{progress.posts_found} posts found</span>
                <span>{progressPct}%</span>
              </div>
              <div className="w-full h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Log area */}
          <div className="max-h-72 overflow-y-auto bg-bg-primary font-mono text-xs">
            {logs.length === 0 ? (
              <div className="px-5 py-8 text-center text-fg-muted">
                {isRunning ? (
                  <div className="flex items-center justify-center gap-2">
                    <Loader2 size={14} className="animate-spin" />
                    Waiting for events...
                  </div>
                ) : (
                  "No scraper activity yet. Click Start Scraper to begin."
                )}
              </div>
            ) : (
              <div className="px-4 py-2 space-y-0.5">
                {logs.map((entry, i) => {
                  const fmt = formatLogEntry(entry);
                  return (
                    <div key={i} className={`flex items-start gap-2 py-0.5 ${fmt.color}`}>
                      <span className="shrink-0 w-5 text-center">{fmt.icon}</span>
                      <span className="break-all leading-relaxed">{fmt.text}</span>
                    </div>
                  );
                })}
                <div ref={logEndRef} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Posts page ──

export default function Posts() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [domain, setDomain] = useState("");
  const [hiring, setHiring] = useState("");
  const [hasEmail, setHasEmail] = useState(false);
  const [source, setSource] = useState("");
  const [locationFilter, setLocationFilter] = useState("");

  const [offset, setOffset] = useState(0);
  const limit = 50;

  const [viewPost, setViewPost] = useState(null);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit, offset };
      if (domain) params.domain = domain.charAt(0).toUpperCase() + domain.slice(1);
      if (hiring !== "") params.is_hiring = hiring === "true";
      if (hasEmail) params.has_email = true;
      if (source) params.source = source;
      if (locationFilter) params.location = locationFilter;
      const data = await api.getPosts(params);
      setPosts(data.posts || []);
      setTotal(data.total || 0);
    } catch (err) {
      const msg = err?.message || "Failed to load posts.";
      setError(msg);
      toast({ type: "error", title: "Failed to load posts", description: msg });
    } finally {
      setLoading(false);
    }
  }, [domain, hiring, hasEmail, source, locationFilter, offset]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  // ── Bulk email finder state ──
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkStatus, setBulkStatus] = useState(null);
  const bulkPollRef = useRef(null);

  const _postsWorker = (data) => data?.posts_worker || data;

  const startBulkFind = async () => {
    try {
      await api.startEnrichment({ max_leads: 500, target: "posts" });
      setBulkRunning(true);
      bulkPollRef.current = setInterval(async () => {
        try {
          const data = await api.getEnrichmentStatus();
          const pw = _postsWorker(data);
          setBulkStatus(pw);
          if (!pw.running && pw.summary) {
            clearInterval(bulkPollRef.current);
            bulkPollRef.current = null;
            setBulkRunning(false);
            fetchPosts();
            toast({
              type: "success",
              title: "Bulk email search done",
              description: `Found emails for ${pw.summary.enriched} posts (${pw.summary.total_emails_found} emails total)`,
            });
          }
        } catch {}
      }, 2000);
    } catch (err) {
      toast({ type: "error", title: "Failed to start", description: err.message });
    }
  };

  const stopBulkFind = async () => {
    try { await api.stopEnrichment("posts"); } catch {}
    if (bulkPollRef.current) clearInterval(bulkPollRef.current);
    bulkPollRef.current = null;
    setBulkRunning(false);
    fetchPosts();
  };

  // Check if bulk finder already running on mount
  useEffect(() => {
    const check = async () => {
      try {
        const data = await api.getEnrichmentStatus();
        const pw = _postsWorker(data);
        if (pw?.running) {
          setBulkRunning(true);
          setBulkStatus(pw);
          bulkPollRef.current = setInterval(async () => {
            try {
              const d = await api.getEnrichmentStatus();
              const pw2 = _postsWorker(d);
              setBulkStatus(pw2);
              if (!pw2.running) {
                clearInterval(bulkPollRef.current);
                bulkPollRef.current = null;
                setBulkRunning(false);
                fetchPosts();
              }
            } catch {}
          }, 2000);
        }
      } catch {}
    };
    check();
    return () => { if (bulkPollRef.current) clearInterval(bulkPollRef.current); };
  }, []);

  const handleRefresh = async () => {
    await fetchPosts();
    toast({ type: "success", title: "Refreshed", description: "Showing latest posts." });
  };

  const handleEmailClick = (post) => {
    const params = new URLSearchParams();
    params.set("to", post.email);
    if (post.id || post.post_id) params.set("postId", String(post.id || post.post_id));
    if (post.author_name) params.set("author", post.author_name);
    navigate(`/email?${params.toString()}`);
  };

  const filteredPosts = search.trim()
    ? posts.filter((p) => {
        const q = search.toLowerCase();
        return (
          p.author_name?.toLowerCase().includes(q) ||
          p.author_headline?.toLowerCase().includes(q) ||
          p.content?.toLowerCase().includes(q) ||
          p.email?.toLowerCase().includes(q)
        );
      })
    : posts;

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-bg">
              <Database size={20} className="text-accent" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-fg-primary">
                LinkedIn Posts Database
              </h1>
              <p className="text-sm text-fg-secondary mt-0.5">
                Browse and manage scraped LinkedIn posts
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {!bulkRunning ? (
              <button
                onClick={startBulkFind}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent hover:bg-accent-dim text-fg-inverse text-sm font-semibold transition-colors"
              >
                <Zap size={15} />
                Bulk Find Emails
              </button>
            ) : (
              <button
                onClick={stopBulkFind}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-danger/10 text-danger text-sm font-semibold hover:bg-danger/20 transition-colors"
              >
                <Square size={12} />
                Stop
              </button>
            )}
            <button onClick={() => {
              try {
                const headers = ['Title','Company','Location','Platform','URL','Relevance','Created']
                const rows = posts.map(p => [p.job_title||'',p.company||'',p.location||'',p.platform||'',p.job_url||'',(p.domain_relevance||''),p.created_at||''])
                const csv = [headers,...rows].map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n')
                const blob = new Blob([csv],{type:'text/csv'})
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `posts_${new Date().toISOString().slice(0,10)}.csv`; document.body.appendChild(a); a.click(); document.body.removeChild(a)
              } catch(e) { console.error(e) }
            }} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary hover:border-fg-muted transition-colors">
              <Download size={15} />
              Export
            </button>
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary hover:border-fg-muted disabled:opacity-60 transition-colors"
            >
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        </div>

        {/* Bulk Email Finder Progress */}
        {(bulkRunning || bulkStatus?.summary) && (
          <div className="mb-6 bg-bg-secondary border border-border rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Zap size={14} className="text-accent" />
                <span className="text-sm font-medium text-fg-primary">
                  {bulkRunning ? "Finding emails..." : "Email search complete"}
                </span>
              </div>
              {bulkStatus && (
                <div className="flex items-center gap-4 text-xs text-fg-muted">
                  <span className="text-success">{bulkStatus.found || 0} found</span>
                  <span>{bulkStatus.not_found || 0} not found</span>
                  {bulkStatus.errors > 0 && <span className="text-danger">{bulkStatus.errors} errors</span>}
                </div>
              )}
            </div>
            {bulkRunning && bulkStatus?.total > 0 && (
              <>
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex-1 h-2 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all duration-500"
                      style={{ width: `${Math.round((bulkStatus.current / bulkStatus.total) * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-fg-secondary">
                    {bulkStatus.current}/{bulkStatus.total}
                  </span>
                </div>
                {bulkStatus.current_company && (
                  <div className="flex items-center gap-2 text-xs text-fg-muted">
                    <Loader2 size={11} className="animate-spin text-accent" />
                    Searching: <span className="text-fg-primary font-medium">{bulkStatus.current_company}</span>
                  </div>
                )}
              </>
            )}
            {bulkStatus?.summary && !bulkRunning && (
              <div className="text-xs text-fg-secondary mt-1">
                Enriched <strong>{bulkStatus.summary.enriched}</strong> posts with <strong>{bulkStatus.summary.total_emails_found}</strong> emails found
              </div>
            )}
          </div>
        )}

        {/* Scraper Panel */}
        <ScraperPanel onScrapeDone={fetchPosts} />

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted"
            />
            <input
              type="text"
              placeholder="Search posts, authors, emails..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-bg-secondary border border-border text-fg-primary text-sm rounded-lg pl-9 pr-4 py-2 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent placeholder:text-fg-muted"
            />
          </div>
          <Select value={domain} onChange={setDomain} options={RELEVANCE_OPTIONS} />
          <Select value={hiring} onChange={setHiring} options={HIRING_OPTIONS} />
          <Select value={source} onChange={setSource} options={SOURCE_OPTIONS} />
          <div className="relative min-w-[140px]">
            <input
              type="text"
              placeholder="Location..."
              value={locationFilter}
              onChange={(e) => { setLocationFilter(e.target.value); setOffset(0); }}
              className="w-full bg-bg-secondary border border-border text-fg-primary text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent placeholder:text-fg-muted"
            />
          </div>
          <button
            onClick={() => setHasEmail((v) => !v)}
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
              hasEmail
                ? "bg-accent-bg border-accent text-accent"
                : "bg-bg-secondary border-border text-fg-secondary hover:text-fg-primary"
            }`}
          >
            <Mail size={14} />
            Has Email
          </button>
          <span className="text-sm text-fg-muted ml-auto">
            {loading ? "Loading..." : `${total} posts total`}
          </span>
        </div>

        {/* Inline error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-danger-bg border border-danger/30 text-danger text-sm">
            {error}
          </div>
        )}

        {/* Table */}
        <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg-tertiary border-b border-border">
                <th className="text-left px-4 py-3 text-fg-muted font-medium">
                  Author
                </th>
                <th className="text-left px-4 py-3 text-fg-muted font-medium">
                  Content Preview
                </th>
                <th className="text-left px-4 py-3 text-fg-muted font-medium">
                  Hiring
                </th>
                <th className="text-left px-4 py-3 text-fg-muted font-medium">
                  Job Relevance
                </th>
                <th className="text-left px-4 py-3 text-fg-muted font-medium">
                  Email
                </th>
                <th className="text-left px-4 py-3 text-fg-muted font-medium">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-bg-tertiary rounded animate-pulse w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filteredPosts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-fg-muted">
                    No posts found.
                  </td>
                </tr>
              ) : (
                filteredPosts.map((post) => (
                  <tr
                    key={post.id || post.post_id}
                    className="border-b border-border last:border-0 hover:bg-bg-tertiary/50 transition-colors"
                  >
                    <td className="px-4 py-3 min-w-[160px]">
                      <div className="font-medium text-fg-primary truncate max-w-[160px]">
                        {post.author_name || "\u2014"}
                      </div>
                      <div className="text-xs text-fg-muted truncate max-w-[160px] mt-0.5">
                        {post.author_headline || ""}
                      </div>
                    </td>
                    <td className="px-4 py-3 max-w-[300px]">
                      <p className="text-fg-secondary truncate">
                        {post.content || "\u2014"}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <HiringBadge value={post.is_hiring} />
                    </td>
                    <td className="px-4 py-3">
                      <RelevanceBadge value={post.domain_relevance} />
                    </td>
                    <td className="px-4 py-3">
                      {post.email ? (
                        <span className="font-mono text-xs text-info">
                          {post.email}
                        </span>
                      ) : (
                        <FindEmailBtn
                          postId={post.id}
                          onFound={(email) => {
                            setPosts(prev => prev.map(p => p.id === post.id ? { ...p, email } : p));
                          }}
                        />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setViewPost(post)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border text-fg-secondary text-xs hover:text-fg-primary hover:border-fg-muted transition-colors"
                        >
                          <Eye size={12} />
                          View
                        </button>
                        {post.email ? (
                          <button
                            onClick={() => handleEmailClick(post)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-white text-xs font-medium hover:bg-accent/90 transition-colors"
                          >
                            <Mail size={12} />
                            Email
                          </button>
                        ) : (
                          <FindEmailBtn
                            postId={post.id}
                            onFound={(email) => {
                              setPosts(prev => prev.map(p => p.id === post.id ? { ...p, email } : p));
                            }}
                          />
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && total > limit && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-fg-muted">
              Showing {offset + 1}&ndash;{Math.min(offset + limit, total)} of {total}
            </span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - limit))}
                className="px-3 py-1.5 rounded-lg border border-border text-sm text-fg-secondary disabled:opacity-40 hover:text-fg-primary hover:border-fg-muted transition-colors"
              >
                Previous
              </button>
              <button
                disabled={offset + limit >= total}
                onClick={() => setOffset((o) => o + limit)}
                className="px-3 py-1.5 rounded-lg border border-border text-sm text-fg-secondary disabled:opacity-40 hover:text-fg-primary hover:border-fg-muted transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Post view modal */}
      {viewPost && (
        <PostViewModal post={viewPost} onClose={() => setViewPost(null)} onEmailFound={(postId, email) => setPosts(prev => prev.map(p => p.id === postId ? { ...p, email } : p))} />
      )}
    </div>
  );
}
