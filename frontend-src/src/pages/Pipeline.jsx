import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  GitBranch, RefreshCw, SlidersHorizontal, LayoutGrid, List,
  Mail, CheckCircle, Clock, AlertCircle, XCircle, Award, Search, X,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";
import FilterBar, { useFilters, applyFilters, dateRangeMatch } from "../components/FilterBar";

const STAGES = [
  { key: "applied", label: "Applied", color: "fg-muted", dot: "bg-fg-muted" },
  { key: "replied", label: "Replied", color: "info", dot: "bg-info" },
  { key: "interviewing", label: "Interviewing", color: "success", dot: "bg-success" },
  { key: "offer", label: "Offer", color: "accent", dot: "bg-accent" },
  { key: "rejected", label: "Rejected", color: "danger", dot: "bg-danger" },
];

function StageBadge({ stage }) {
  const s = STAGES.find((st) => st.key === stage) || STAGES[0];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-${s.color}-bg text-${s.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  const days = Math.floor(diff / 86400);
  if (days === 1) return "1d ago";
  if (days < 7) return `${days}d ago`;
  return `${Math.floor(days / 7)}w ago`;
}

function KanbanCard({ lead, onClick, onStageChange }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div
      className="cursor-pointer rounded-lg bg-bg-tertiary border border-border p-3 hover:border-fg-muted transition-colors relative"
    >
      <div onClick={() => onClick(lead)}>
        <p className="text-sm font-medium text-fg-primary truncate">{lead.role || "Unknown Role"}</p>
        <p className="text-xs text-fg-muted mt-0.5 truncate">{lead.company || "—"}</p>
        <p className="text-xs text-fg-muted truncate">{lead.recipient_name || lead.recipient_email}</p>
      </div>
      <div className="flex items-center justify-between mt-2">
        {/* Clickable stage badge to change stage */}
        <div className="relative">
          <button onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}>
            <StageBadge stage={lead.stage} />
          </button>
          {menuOpen && (
            <div className="absolute left-0 top-full mt-1 bg-bg-secondary border border-border rounded-lg shadow-xl z-30 py-1 w-36"
              onClick={(e) => e.stopPropagation()}>
              {STAGES.filter((s) => s.key !== lead.stage).map((s) => (
                <button key={s.key}
                  onClick={() => { onStageChange(lead.id, s.key); setMenuOpen(false); }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-fg-secondary hover:bg-bg-tertiary transition-colors">
                  <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                  Move to {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <span className="text-xs text-fg-muted">{timeAgo(lead.updated_at || lead.created_at)}</span>
      </div>
    </div>
  );
}

function KanbanColumn({ stage, leads, onCardClick, onStageChange }) {
  const s = STAGES.find((st) => st.key === stage.key);
  const colLeads = leads.filter((l) => l.stage === stage.key);

  return (
    <div className="flex-1 min-w-[220px] bg-bg-secondary rounded-lg border border-border flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3.5 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${s.dot}`} />
          <span className="text-sm font-medium text-fg-primary">{stage.label}</span>
        </div>
        <span className="text-xs text-fg-muted bg-bg-tertiary rounded-full px-2 py-0.5">{colLeads.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {colLeads.length === 0 ? (
          <div className="text-center py-8 text-xs text-fg-muted">No leads</div>
        ) : (
          colLeads.map((lead) => (
            <KanbanCard key={lead.id} lead={lead} onClick={onCardClick} onStageChange={onStageChange} />
          ))
        )}
      </div>
    </div>
  );
}

function ListRow({ lead, onClick }) {
  return (
    <div
      onClick={() => onClick(lead)}
      className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-bg-tertiary/50 cursor-pointer transition-colors"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-fg-primary truncate">{lead.role || "Unknown Role"}</span>
          {lead.company && <span className="text-xs text-fg-muted">@ {lead.company}</span>}
        </div>
        <p className="text-xs text-fg-muted mt-0.5 truncate">{lead.recipient_name} &mdash; {lead.recipient_email}</p>
      </div>
      <StageBadge stage={lead.stage} />
      <span className="text-xs text-fg-muted shrink-0 w-16 text-right">{timeAgo(lead.updated_at || lead.created_at)}</span>
    </div>
  );
}

export default function Pipeline() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState("board"); // board | list
  const [syncing, setSyncing] = useState(false);
  const [search, setSearch] = useState("");

  const pipelineFilterDefs = [
    { key: 'stage', type: 'select', label: 'Stage', options: [
      { label: 'All Stages', value: '' },
      ...STAGES.map(s => ({ label: s.label, value: s.key })),
    ], match: (item, v) => item.stage === v },
    { key: 'date_range', type: 'dateRange', match: dateRangeMatch('created_at') },
  ];
  const pipelineFilters = useFilters(pipelineFilterDefs);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [pipeline, pStats] = await Promise.all([api.getPipeline(), api.getPipelineStats()]);
      setLeads(pipeline.leads || []);
      setStats(pStats);
    } catch (err) {
      setError(err.message);
      toast({ type: "error", title: "Failed to load pipeline", description: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      const res = await api.syncPipeline();
      toast({ type: "success", title: "Pipeline synced", description: res.message });
      await load();
    } catch (err) {
      toast({ type: "error", title: "Sync failed", description: err.message });
    } finally {
      setSyncing(false);
    }
  }

  async function handleStageChange(leadId, newStage) {
    try {
      await api.updatePipelineStage({ lead_id: leadId, stage: newStage });
      // Update local state immediately
      setLeads((prev) => prev.map((l) => l.id === leadId ? { ...l, stage: newStage, updated_at: new Date().toISOString() } : l));
      setStats((prev) => {
        const old = leads.find((l) => l.id === leadId)?.stage;
        if (!old) return prev;
        return { ...prev, [old]: (prev[old] || 1) - 1, [newStage]: (prev[newStage] || 0) + 1 };
      });
      toast({ type: "success", title: `Moved to ${newStage}` });
    } catch (err) {
      toast({ type: "error", title: "Update failed", description: err.message });
    }
  }

  function handleCardClick(lead) {
    navigate(`/pipeline/${lead.id}`);
  }

  const q = search.trim().toLowerCase();
  let filteredLeads = q
    ? leads.filter((l) => [l.recipient_name, l.recipient_email, l.role, l.company, l.location, l.stage]
        .filter(Boolean).join(" ").toLowerCase().includes(q))
    : leads;
  filteredLeads = applyFilters(filteredLeads, pipelineFilters.values, pipelineFilterDefs);

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-bg"><GitBranch size={20} className="text-accent" /></div>
            <div>
              <h1 className="text-2xl font-semibold text-fg-primary">Pipeline Tracker</h1>
              <p className="text-sm text-fg-secondary mt-0.5">Track every application from first contact to final outcome.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleSync} disabled={syncing}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-fg-secondary text-sm hover:text-fg-primary transition-colors disabled:opacity-50">
              <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
              {syncing ? "Syncing..." : "Sync Emails"}
            </button>
            {/* View toggle */}
            <div className="flex rounded-lg border border-border overflow-hidden">
              <button onClick={() => setView("board")}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors ${view === "board" ? "bg-accent-bg text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
                <LayoutGrid size={13} /> Board
              </button>
              <button onClick={() => setView("list")}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors ${view === "list" ? "bg-accent-bg text-accent" : "text-fg-muted hover:text-fg-primary"}`}>
                <List size={13} /> List
              </button>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
          <input type="text" placeholder="Search leads — name, company, role, email..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-bg-secondary border border-border text-fg-primary text-sm rounded-lg pl-9 pr-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-fg-muted" />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg-primary">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="mb-4">
          <FilterBar
            filters={pipelineFilterDefs}
            values={pipelineFilters.values}
            onChange={pipelineFilters.setFilter}
            onClear={pipelineFilters.clearFilters}
            isFiltered={pipelineFilters.isFiltered}
            resultCount={filteredLeads.length}
            totalCount={leads.length}
          />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "Total Tracked", value: stats.total || 0, bg: "bg-bg-secondary", color: "text-fg-primary" },
            { label: "Interviewing", value: stats.interviewing || 0, bg: "bg-success-bg", color: "text-success" },
            { label: "Replied", value: stats.replied || 0, bg: "bg-info-bg", color: "text-info" },
            { label: "Pending", value: stats.applied || 0, bg: "bg-warning-bg", color: "text-warning" },
            { label: "Rejected", value: stats.rejected || 0, bg: "bg-danger-bg", color: "text-danger" },
          ].map((s, i) => (
            <div key={i} className={`${s.bg} rounded-lg border border-border px-4 py-3`}>
              <p className={`text-xs font-medium ${s.color} opacity-80`}>{s.label}</p>
              <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-fg-muted text-sm">
            <RefreshCw size={16} className="animate-spin mr-2" /> Loading pipeline...
          </div>
        ) : error ? (
          <div className="bg-danger-bg border border-danger/20 rounded-xl p-6 text-center">
            <p className="text-danger font-medium">Failed to load pipeline</p>
            <p className="text-fg-muted text-sm mt-1">{error}</p>
            <button onClick={load} className="mt-3 px-4 py-2 bg-accent text-white text-sm rounded-lg">Retry</button>
          </div>
        ) : leads.length === 0 ? (
          <div className="bg-bg-secondary rounded-xl border border-border px-8 py-16 text-center">
            <GitBranch size={32} className="text-fg-muted mx-auto mb-3" />
            <p className="text-fg-primary font-medium mb-1">No leads in pipeline yet</p>
            <p className="text-fg-muted text-sm mb-4">Click "Sync Emails" to import your sent emails into the pipeline tracker.</p>
            <button onClick={handleSync} disabled={syncing}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90">
              <RefreshCw size={14} className={syncing ? "animate-spin" : ""} /> Sync Now
            </button>
          </div>
        ) : view === "board" ? (
          /* Kanban Board */
          <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: "calc(100vh - 340px)" }}>
            {STAGES.map((stage) => (
              <KanbanColumn key={stage.key} stage={stage} leads={filteredLeads} onCardClick={handleCardClick} onStageChange={handleStageChange} />
            ))}
          </div>
        ) : (
          /* List View */
          <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="flex items-center px-4 py-2.5 bg-bg-tertiary border-b border-border text-xs font-medium text-fg-muted">
              <span className="flex-1">Role / Contact</span>
              <span className="w-24 text-center">Status</span>
              <span className="w-16 text-right">When</span>
            </div>
            <div className="max-h-[calc(100vh-380px)] overflow-y-auto">
              {filteredLeads.map((lead) => (
                <ListRow key={lead.id} lead={lead} onClick={handleCardClick} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
