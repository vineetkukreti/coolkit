import { useState, useEffect, useRef } from "react";
import { Terminal, RefreshCw, AlertTriangle, Info, Bug, Search, X, Filter, Download } from "lucide-react";
import { api } from "../lib/api";

const LEVEL_STYLES = {
  ERROR: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/30", badge: "bg-red-500/20 text-red-400" },
  WARNING: { bg: "bg-yellow-500/10", text: "text-yellow-400", border: "border-yellow-500/30", badge: "bg-yellow-500/20 text-yellow-400" },
  INFO: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30", badge: "bg-blue-500/20 text-blue-400" },
  DEBUG: { bg: "bg-gray-500/10", text: "text-gray-400", border: "border-gray-500/30", badge: "bg-gray-500/20 text-gray-400" },
};

function LevelBadge({ level }) {
  const s = LEVEL_STYLES[level] || LEVEL_STYLES.DEBUG;
  return <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${s.badge}`}>{level}</span>;
}

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState(""); // "" = all, or ERROR, WARNING, INFO, DEBUG
  const [search, setSearch] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [tab, setTab] = useState("live"); // live | errors | file
  const [fileLines, setFileLines] = useState([]);
  const [expandedIdx, setExpandedIdx] = useState(null);
  const bottomRef = useRef(null);

  async function loadLogs() {
    try {
      const data = await api.getLogs(filter, 200, search);
      setLogs(data.logs || []);
    } catch (err) {
      console.error("Failed to load logs:", err);
    } finally {
      setLoading(false);
    }
  }

  async function loadErrors() {
    try {
      const data = await api.getErrors(100);
      setErrors(data.errors || []);
    } catch {}
  }

  async function loadFile() {
    try {
      const data = await api.getLogFile(300);
      setFileLines(data.lines || []);
    } catch {}
  }

  useEffect(() => {
    loadLogs();
    loadErrors();
  }, [filter, search]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      if (tab === "live") loadLogs();
      else if (tab === "errors") loadErrors();
      else if (tab === "file") loadFile();
    }, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, tab, filter, search]);

  useEffect(() => {
    if (tab === "file" && fileLines.length === 0) loadFile();
  }, [tab]);

  const errorCount = logs.filter(l => l.level === "ERROR").length;

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-bg"><Terminal size={20} className="text-accent" /></div>
            <div>
              <h1 className="text-2xl font-semibold text-fg-primary">Server Logs</h1>
              <p className="text-sm text-fg-secondary mt-0.5">
                Real-time backend logs, errors, and diagnostics.
                {errorCount > 0 && <span className="ml-2 text-red-400">{errorCount} errors</span>}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setAutoRefresh(!autoRefresh)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-colors ${autoRefresh ? "border-success/40 text-success bg-success-bg" : "border-border text-fg-muted"}`}>
              <RefreshCw size={14} className={autoRefresh ? "animate-spin" : ""} />
              {autoRefresh ? "Live" : "Paused"}
            </button>
            <button onClick={() => { loadLogs(); loadErrors(); if (tab === "file") loadFile(); }}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors">
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-border">
          {[
            { key: "live", label: "Live Logs", icon: Terminal },
            { key: "errors", label: `Errors (${errors.length})`, icon: AlertTriangle },
            { key: "file", label: "Log File", icon: Download },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${tab === t.key ? "border-accent text-accent" : "border-transparent text-fg-muted hover:text-fg-primary"}`}>
              <t.icon size={14} /> {t.label}
            </button>
          ))}
        </div>

        {/* Filters (for live tab) */}
        {tab === "live" && (
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input type="text" placeholder="Search logs..."
                value={search} onChange={e => setSearch(e.target.value)}
                className="w-full bg-bg-secondary border border-border text-fg-primary text-sm rounded-lg pl-9 pr-8 py-2 focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-fg-muted" />
              {search && <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg-primary"><X size={14} /></button>}
            </div>
            <div className="flex rounded-lg border border-border overflow-hidden">
              {["", "ERROR", "WARNING", "INFO", "DEBUG"].map(level => (
                <button key={level} onClick={() => setFilter(level)}
                  className={`px-3 py-2 text-xs font-medium transition-colors ${filter === level ? "bg-accent-bg text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
                  {level || "All"}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        {tab === "live" && (
          <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="max-h-[calc(100vh-320px)] overflow-y-auto font-mono text-xs">
              {loading ? (
                <div className="flex items-center justify-center py-20 text-fg-muted text-sm">
                  <RefreshCw size={16} className="animate-spin mr-2" /> Loading logs...
                </div>
              ) : logs.length === 0 ? (
                <div className="text-center py-16 text-fg-muted">
                  <Terminal size={28} className="mx-auto mb-2 opacity-50" />
                  <p>No logs yet. Start the server to see logs here.</p>
                </div>
              ) : (
                logs.map((entry, i) => {
                  const s = LEVEL_STYLES[entry.level] || LEVEL_STYLES.DEBUG;
                  const hasTb = entry.traceback && entry.traceback.length > 0;
                  return (
                    <div key={i}
                      onClick={() => hasTb && setExpandedIdx(expandedIdx === i ? null : i)}
                      className={`flex items-start gap-2 px-4 py-1.5 border-b border-border/50 ${s.bg} ${hasTb ? "cursor-pointer hover:brightness-110" : ""}`}>
                      <span className="text-fg-muted shrink-0 w-16">{entry.time?.split(" ")[1] || ""}</span>
                      <LevelBadge level={entry.level} />
                      <div className="flex-1 min-w-0">
                        <span className={`${s.text} break-all`}>{entry.message}</span>
                        {hasTb && expandedIdx === i && (
                          <pre className="mt-2 p-2 bg-bg-primary rounded text-red-300 text-[10px] overflow-x-auto whitespace-pre-wrap">
                            {entry.traceback.join("")}
                          </pre>
                        )}
                        {hasTb && expandedIdx !== i && (
                          <span className="ml-2 text-[10px] text-red-400/60">[click to expand traceback]</span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={bottomRef} />
            </div>
          </div>
        )}

        {tab === "errors" && (
          <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="max-h-[calc(100vh-280px)] overflow-y-auto font-mono text-xs">
              {errors.length === 0 ? (
                <div className="text-center py-16 text-fg-muted">
                  <AlertTriangle size={28} className="mx-auto mb-2 opacity-50" />
                  <p>No errors! Everything is running smoothly.</p>
                </div>
              ) : errors.map((entry, i) => (
                <div key={i}
                  onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                  className="px-4 py-2.5 border-b border-border/50 bg-red-500/5 cursor-pointer hover:bg-red-500/10 transition-colors">
                  <div className="flex items-start gap-2">
                    <span className="text-fg-muted shrink-0 w-32">{entry.time}</span>
                    <AlertTriangle size={12} className="text-red-400 mt-0.5 shrink-0" />
                    <span className="text-red-400 break-all">{entry.message}</span>
                  </div>
                  {entry.traceback && expandedIdx === i && (
                    <pre className="mt-2 ml-36 p-3 bg-bg-primary rounded text-red-300 text-[10px] overflow-x-auto whitespace-pre-wrap border border-red-500/20">
                      {entry.traceback.join("")}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "file" && (
          <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="max-h-[calc(100vh-280px)] overflow-y-auto font-mono text-[11px] p-4">
              {fileLines.length === 0 ? (
                <div className="text-center py-16 text-fg-muted">
                  <Download size={28} className="mx-auto mb-2 opacity-50" />
                  <p>Log file empty or not found. Start the server first.</p>
                </div>
              ) : fileLines.map((line, i) => {
                const isError = line.includes("ERROR");
                const isWarn = line.includes("WARNING");
                return (
                  <div key={i} className={`py-0.5 ${isError ? "text-red-400" : isWarn ? "text-yellow-400" : "text-fg-secondary"}`}>
                    {line}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
