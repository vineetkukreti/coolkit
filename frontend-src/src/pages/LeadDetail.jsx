import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Mail, MessageSquare, Calendar, Paperclip, XCircle,
  CheckCircle, Clock, AlertCircle, ChevronDown, Plus, Send, Eye,
  FileText, User, MapPin, Briefcase, Globe, Award,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";

const STAGES = [
  { key: "applied", label: "Applied", color: "fg-muted", bg: "bg-bg-tertiary", border: "border-border" },
  { key: "replied", label: "Replied", color: "info", bg: "bg-info-bg", border: "border-info" },
  { key: "interviewing", label: "Interviewing", color: "success", bg: "bg-success-bg", border: "border-success" },
  { key: "offer", label: "Offer", color: "accent", bg: "bg-accent-bg", border: "border-accent" },
  { key: "rejected", label: "Rejected", color: "danger", bg: "bg-danger-bg", border: "border-danger" },
];

const EVENT_ICONS = {
  email_sent: { icon: Send, color: "text-accent", bg: "bg-accent-bg" },
  reply_received: { icon: MessageSquare, color: "text-success", bg: "bg-success-bg" },
  stage_change: { icon: Award, color: "text-warning", bg: "bg-warning-bg" },
  note: { icon: FileText, color: "text-info", bg: "bg-info-bg" },
  follow_up: { icon: Mail, color: "text-accent", bg: "bg-accent-bg" },
};

function TimelineEvent({ event }) {
  const cfg = EVENT_ICONS[event.event_type] || EVENT_ICONS.note;
  const Icon = cfg.icon;
  const date = event.created_at
    ? new Date(event.created_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <div className="flex gap-3.5 py-4 border-b border-border last:border-0">
      <div className={`w-8 h-8 rounded-full ${cfg.bg} flex items-center justify-center shrink-0 mt-0.5`}>
        <Icon size={14} className={cfg.color} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${cfg.color}`}>{event.title || event.event_type}</span>
          <span className="text-xs text-fg-muted">{date}</span>
        </div>
        {event.content && (
          <p className="text-xs text-fg-secondary mt-1 leading-relaxed whitespace-pre-wrap">{event.content}</p>
        )}
      </div>
    </div>
  );
}

function ContactRow({ label, value, icon: Icon }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-fg-muted flex items-center gap-1.5">
        {Icon && <Icon size={11} />} {label}
      </span>
      <span className="text-xs text-fg-primary font-medium text-right truncate max-w-[160px]">{value || "—"}</span>
    </div>
  );
}

export default function LeadDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stageMenuOpen, setStageMenuOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  useEffect(() => {
    loadLead();
  }, [id]);

  async function loadLead() {
    setLoading(true);
    try {
      const data = await api.getPipelineLead(id);
      setLead(data);
    } catch (err) {
      toast({ type: "error", title: "Failed to load lead", description: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleStageChange(newStage) {
    setStageMenuOpen(false);
    try {
      await api.updatePipelineStage({ lead_id: parseInt(id), stage: newStage });
      toast({ type: "success", title: `Moved to ${newStage}` });
      await loadLead();
    } catch (err) {
      toast({ type: "error", title: "Update failed", description: err.message });
    }
  }

  async function handleAddNote() {
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      await api.addPipelineNote({ lead_id: parseInt(id), content: noteText.trim() });
      setNoteText("");
      toast({ type: "success", title: "Note added" });
      await loadLead();
    } catch (err) {
      toast({ type: "error", title: "Failed to add note", description: err.message });
    } finally {
      setAddingNote(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center text-fg-muted text-sm">
        <Clock size={16} className="animate-spin mr-2" /> Loading lead...
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center text-fg-muted text-sm">
        Lead not found.
        <button onClick={() => navigate("/pipeline")} className="ml-2 text-accent hover:underline">Back to Pipeline</button>
      </div>
    );
  }

  const currentStage = STAGES.find((s) => s.key === lead.stage) || STAGES[0];
  const initials = (lead.recipient_name || "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans">
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3.5">
            <button onClick={() => navigate("/pipeline")}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border text-fg-secondary text-xs hover:text-fg-primary transition-colors">
              <ArrowLeft size={13} /> Back
            </button>
            <div className="w-11 h-11 rounded-full bg-accent flex items-center justify-center shrink-0">
              <span className="text-fg-inverse font-bold text-sm">{initials}</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-fg-primary">{lead.recipient_name || "Unknown"}</h1>
              <div className="flex items-center gap-2 text-xs text-fg-muted">
                {lead.author_headline && <span>{lead.author_headline}</span>}
                {lead.recipient_email && <span className="text-info font-mono">{lead.recipient_email}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Stage selector */}
            <div className="relative">
              <button onClick={() => setStageMenuOpen(!stageMenuOpen)}
                className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold ${currentStage.bg} ${currentStage.border} border text-${currentStage.color}`}>
                <span className={`w-2 h-2 rounded-full bg-${currentStage.color}`} />
                {currentStage.label}
                <ChevronDown size={12} />
              </button>
              {stageMenuOpen && (
                <div className="absolute right-0 top-full mt-1 bg-bg-secondary border border-border rounded-lg shadow-xl z-20 py-1 w-40">
                  {STAGES.map((s) => (
                    <button key={s.key} onClick={() => handleStageChange(s.key)}
                      className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-bg-tertiary transition-colors ${s.key === lead.stage ? "font-semibold text-fg-primary" : "text-fg-secondary"}`}>
                      <span className={`w-2 h-2 rounded-full bg-${s.color}`} />
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Add Note button */}
            <button onClick={() => document.getElementById("note-input")?.focus()}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent text-fg-inverse text-xs font-semibold hover:bg-accent/90 transition-colors">
              <Plus size={13} /> Add Note
            </button>
          </div>
        </div>

        {/* Body: Timeline + Detail Panel */}
        <div className="flex gap-4 items-start">
          {/* Left: Conversation Timeline */}
          <div className="flex-1 bg-bg-secondary rounded-xl border border-border overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 bg-bg-tertiary border-b border-border">
              <h2 className="text-sm font-semibold text-fg-primary">Conversation Timeline</h2>
              <span className="text-xs text-fg-muted bg-accent-bg text-accent px-2 py-0.5 rounded-full font-medium">
                {(lead.events || []).length} interactions
              </span>
            </div>
            <div className="px-5 max-h-[calc(100vh-340px)] overflow-y-auto">
              {(lead.events || []).length === 0 ? (
                <div className="py-12 text-center text-fg-muted text-sm">No timeline events yet.</div>
              ) : (
                (lead.events || []).map((ev, i) => <TimelineEvent key={ev.id || i} event={ev} />)
              )}
            </div>
          </div>

          {/* Right: Detail Panel */}
          <div className="w-80 shrink-0 space-y-4">
            {/* Contact Details */}
            <div className="bg-bg-secondary rounded-xl border border-border p-5">
              <h3 className="text-xs font-semibold text-fg-primary mb-3">Contact Details</h3>
              <div className="space-y-1">
                <ContactRow label="Company" value={lead.company} icon={Briefcase} />
                <ContactRow label="Role" value={lead.role} icon={Award} />
                <ContactRow label="Location" value={lead.location} icon={MapPin} />
                <ContactRow label="Source" value={lead.source === "email" ? "LinkedIn Post" : lead.source} icon={Globe} />
                <ContactRow label="First Contact" value={lead.created_at ? new Date(lead.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"} icon={Calendar} />
                <ContactRow label="Last Activity" value={lead.updated_at ? new Date(lead.updated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"} icon={Clock} />
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-bg-secondary rounded-xl border border-border p-5">
              <h3 className="text-xs font-semibold text-fg-primary mb-3">Quick Actions</h3>
              <div className="space-y-1.5">
                {[
                  { icon: Send, label: "Send Follow-up Email", color: "text-accent" },
                  { icon: Calendar, label: "Schedule Interview", color: "text-info" },
                  { icon: Paperclip, label: "Attach Resume", color: "text-fg-secondary" },
                  { icon: XCircle, label: "Mark as Rejected", color: "text-danger" },
                ].map((action, i) => (
                  <button key={i} onClick={() => {
                    if (action.label === "Mark as Rejected") handleStageChange("rejected");
                  }}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium ${action.color} hover:bg-bg-tertiary transition-colors text-left`}>
                    <action.icon size={13} /> {action.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div className="bg-bg-secondary rounded-xl border border-border p-5">
              <h3 className="text-xs font-semibold text-fg-primary mb-3">Notes</h3>
              {/* Add note input */}
              <div className="flex gap-2 mb-3">
                <input
                  id="note-input"
                  type="text"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddNote()}
                  placeholder="Add a note..."
                  className="flex-1 bg-bg-tertiary border border-border text-fg-primary text-xs rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-fg-muted"
                />
                <button onClick={handleAddNote} disabled={addingNote || !noteText.trim()}
                  className="px-2.5 py-2 rounded-lg bg-accent text-fg-inverse text-xs disabled:opacity-50 hover:bg-accent/90">
                  <Plus size={13} />
                </button>
              </div>
              {/* Note list */}
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {(lead.notes || []).length === 0 ? (
                  <p className="text-xs text-fg-muted text-center py-4">No notes yet.</p>
                ) : (
                  (lead.notes || []).map((note, i) => (
                    <div key={note.id || i} className="bg-bg-tertiary rounded-lg p-3">
                      <p className="text-xs text-fg-muted mb-1">
                        {note.created_at ? new Date(note.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                      </p>
                      <p className="text-xs text-fg-secondary leading-relaxed">{note.content}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
