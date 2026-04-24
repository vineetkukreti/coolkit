import { useState, useRef } from "react";
import {
  Search,
  MapPin,
  Briefcase,
  CheckCircle,
  XCircle,
  ExternalLink,
  Undo2,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../components/Toast";

const PLATFORMS = ["LinkedIn", "Naukri", "Wellfound"];

function MatchBadge({ score }) {
  if (score >= 80) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-success-bg text-success">
        {score}%
      </span>
    );
  }
  if (score >= 60) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-warning-bg text-warning">
        {score}%
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold text-fg-muted bg-bg-tertiary">
      {score}%
    </span>
  );
}

function PlatformChip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-sm font-medium border transition-all duration-150 cursor-pointer ${
        active
          ? "border-accent bg-accent-bg text-accent"
          : "border-border bg-bg-tertiary text-fg-secondary hover:border-fg-muted"
      }`}
    >
      {label}
    </button>
  );
}

function Spinner({ size = 16 }) {
  return (
    <svg
      className="animate-spin"
      style={{ width: size, height: size }}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v8z"
      />
    </svg>
  );
}

export default function JobSearch() {
  const { toast } = useToast();

  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [maxJobs, setMaxJobs] = useState(20);
  const [activePlatforms, setActivePlatforms] = useState(new Set(PLATFORMS));
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [searchError, setSearchError] = useState(null);

  // Per-row action loading state: { [url]: 'apply' | 'skip' | 'queue' | null }
  const [rowLoading, setRowLoading] = useState({});

  // Undo skip — stores { job, timeoutId }
  const skipUndoRef = useRef({});

  function togglePlatform(platform) {
    setActivePlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(platform)) {
        if (next.size === 1) return prev;
        next.delete(platform);
      } else {
        next.add(platform);
      }
      return next;
    });
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!keywords.trim()) return;
    setLoading(true);
    setSearched(true);
    setSearchError(null);
    setJobs([]);
    setTotal(0);
    try {
      const result = await api.searchJobs({
        keywords: keywords.trim(),
        location: location.trim(),
        platforms: Array.from(activePlatforms),
        max_jobs: Number(maxJobs),
      });
      setJobs(result.jobs || []);
      setTotal(result.total || 0);
    } catch (err) {
      setSearchError(err?.message || "Search failed. Please try again.");
      toast({
        type: "error",
        title: "Search failed",
        description: err?.message || "Could not fetch jobs. Check your connection.",
      });
    } finally {
      setLoading(false);
    }
  }

  function setRowState(url, state) {
    setRowLoading((prev) => ({ ...prev, [url]: state }));
  }

  async function handleApply(job) {
    setRowState(job.url, "apply");
    try {
      // Open the job URL in a new tab
      window.open(job.url, "_blank", "noopener,noreferrer");

      // Mark as applied in the backend
      await api.markApplied({
        url: job.url,
        title: job.title,
        company: job.company,
        location: job.location,
        platform: job.platform,
      });

      setJobs((prev) => prev.filter((j) => j.url !== job.url));
      toast({
        type: "success",
        title: "Marked as applied",
        description: `${job.title} at ${job.company || "Unknown"}`,
      });
    } catch (err) {
      toast({
        type: "error",
        title: "Could not mark as applied",
        description: err?.message || "Please try again.",
      });
    } finally {
      setRowState(job.url, null);
    }
  }

  function handleSkip(job) {
    // Optimistically remove job
    setJobs((prev) => prev.filter((j) => j.url !== job.url));

    // Show undo toast — we implement undo by re-inserting the job
    // We use a ref to track the commit timeout
    let undone = false;

    const doCommit = async () => {
      if (undone) return;
      try {
        await api.markSkipped({
          url: job.url,
          title: job.title,
          company: job.company,
          location: job.location,
          platform: job.platform,
        });
      } catch (err) {
        toast({
          type: "error",
          title: "Could not skip job",
          description: err?.message || "Please try again.",
        });
        // Re-insert if commit failed
        setJobs((prev) => {
          const exists = prev.some((j) => j.url === job.url);
          return exists ? prev : [...prev, job];
        });
      }
    };

    // We can't easily hook into toast's action button with the current Toast
    // implementation, so we show an info toast and re-insert if user acts within 5s.
    // The undo mechanism is triggered by a separate "Undo" in-page mechanism.
    // Since the Toast doesn't support action buttons, we show the message only.
    const tid = setTimeout(doCommit, 5000);

    skipUndoRef.current[job.url] = {
      job,
      timeoutId: tid,
      undone: false,
      doCommit,
      cancel: () => {
        clearTimeout(tid);
        skipUndoRef.current[job.url].undone = true;
        undone = true;
      },
    };

    toast({
      type: "warning",
      title: "Job skipped",
      description: `"${job.title}" will be skipped in 5 seconds.`,
    });
  }

  const filteredJobs = jobs.filter((j) => activePlatforms.has(j.platform));

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary font-sans px-6 py-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-fg-primary">
            Job Search
          </h1>
          <p className="mt-1 text-fg-secondary text-sm">
            Search for jobs across platforms and manage your applications.
          </p>
        </div>

      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-4">
        <div className="flex items-center gap-3">
          {/* Keywords */}
          <div className="flex-1 relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted"
              size={16}
            />
            <input
              type="text"
              placeholder="Keywords, job title, skills..."
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-bg-tertiary border border-border rounded-lg text-fg-primary placeholder-fg-muted text-sm focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Location */}
          <div className="relative" style={{ width: 200 }}>
            <MapPin
              className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted"
              size={16}
            />
            <input
              type="text"
              placeholder="Location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-bg-tertiary border border-border rounded-lg text-fg-primary placeholder-fg-muted text-sm focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Max Jobs */}
          <div className="relative" style={{ width: 120 }}>
            <Briefcase
              className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted"
              size={16}
            />
            <input
              type="number"
              min={1}
              max={100}
              placeholder="Max Jobs"
              value={maxJobs}
              onChange={(e) => setMaxJobs(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 bg-bg-tertiary border border-border rounded-lg text-fg-primary placeholder-fg-muted text-sm focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Search Button */}
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-accent hover:bg-accent/90 text-white font-semibold rounded-lg text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer"
          >
            {loading ? (
              <>
                <Spinner size={16} />
                Searching...
              </>
            ) : (
              <>
                <Search size={16} />
                Search
              </>
            )}
          </button>
        </div>
      </form>

      {/* Filter Chips Row */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <span className="text-fg-muted text-sm font-medium">Platforms:</span>
          <div className="flex items-center gap-2">
            {PLATFORMS.map((p) => (
              <PlatformChip
                key={p}
                label={p}
                active={activePlatforms.has(p)}
                onClick={() => togglePlatform(p)}
              />
            ))}
          </div>
        </div>
        {searched && !loading && !searchError && (
          <span className="text-fg-muted text-sm">
            Showing{" "}
            <span className="text-fg-secondary font-semibold">
              {filteredJobs.length}
            </span>{" "}
            results
          </span>
        )}
      </div>

      {/* Results Table Card */}
      <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden">
        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 text-fg-muted">
            <Spinner size={32} />
            <p className="text-sm mt-4">Searching for jobs...</p>
          </div>
        )}

        {/* Not yet searched */}
        {!loading && !searched && (
          <div className="flex flex-col items-center justify-center py-20 text-fg-muted">
            <Search size={40} className="mb-4 opacity-30" />
            <p className="text-sm">Enter keywords and search to see results.</p>
          </div>
        )}

        {/* Error state */}
        {!loading && searched && searchError && (
          <div className="flex flex-col items-center justify-center py-20 text-fg-muted">
            <XCircle size={40} className="mb-4 text-danger opacity-70" />
            <p className="text-sm font-semibold text-danger">Search failed</p>
            <p className="text-xs text-fg-muted mt-1">{searchError}</p>
          </div>
        )}

        {/* Empty results */}
        {!loading && searched && !searchError && filteredJobs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-fg-muted">
            <Briefcase size={40} className="mb-4 opacity-30" />
            <p className="text-sm">
              No jobs found. Try different keywords or filters.
            </p>
          </div>
        )}

        {/* Table */}
        {!loading && !searchError && filteredJobs.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg-tertiary border-b border-border">
                <th className="text-left px-5 py-3 text-fg-muted font-semibold tracking-wide uppercase text-xs">
                  Job Title
                </th>
                <th className="text-left px-5 py-3 text-fg-muted font-semibold tracking-wide uppercase text-xs">
                  Company
                </th>
                <th className="text-left px-5 py-3 text-fg-muted font-semibold tracking-wide uppercase text-xs">
                  Location
                </th>
                <th className="text-left px-5 py-3 text-fg-muted font-semibold tracking-wide uppercase text-xs">
                  Match
                </th>
                <th className="text-left px-5 py-3 text-fg-muted font-semibold tracking-wide uppercase text-xs">
                  Platform
                </th>
                <th className="text-right px-5 py-3 text-fg-muted font-semibold tracking-wide uppercase text-xs">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredJobs.map((job, idx) => {
                const rowState = rowLoading[job.url] || null;
                const isRowBusy = rowState !== null;

                return (
                  <tr
                    key={job.url || idx}
                    className="border-b border-border last:border-0 hover:bg-bg-tertiary/50 transition-colors"
                  >
                    {/* Job Title */}
                    <td className="px-5 py-4 max-w-xs">
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-fg-primary hover:text-accent transition-colors line-clamp-1"
                      >
                        {job.title}
                      </a>
                      {job.matched_skills && job.matched_skills.length > 0 && (
                        <p className="text-fg-muted text-xs mt-0.5 line-clamp-1">
                          {job.matched_skills.join(", ")}
                        </p>
                      )}
                    </td>

                    {/* Company */}
                    <td className="px-5 py-4 text-fg-secondary whitespace-nowrap">
                      {job.company || "—"}
                    </td>

                    {/* Location */}
                    <td className="px-5 py-4 text-fg-secondary whitespace-nowrap">
                      {job.location || "—"}
                    </td>

                    {/* Match */}
                    <td className="px-5 py-4">
                      {job.match_score !== undefined &&
                      job.match_score !== null ? (
                        <MatchBadge score={job.match_score} />
                      ) : (
                        <span className="text-fg-muted">—</span>
                      )}
                    </td>

                    {/* Platform */}
                    <td className="px-5 py-4 text-fg-secondary whitespace-nowrap">
                      {job.platform || "—"}
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {/* Open & Apply */}
                        <button
                          onClick={() => handleApply(job)}
                          disabled={isRowBusy}
                          className="px-3 py-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {rowState === "apply" ? (
                            <Spinner size={12} />
                          ) : (
                            <ExternalLink size={12} />
                          )}
                          Open &amp; Apply
                        </button>

                        {/* Skip */}
                        <button
                          onClick={() => handleSkip(job)}
                          disabled={isRowBusy}
                          className="px-3 py-1.5 border border-border hover:border-fg-muted text-fg-secondary hover:text-fg-primary text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {rowState === "skip" ? (
                            <Spinner size={12} />
                          ) : (
                            <XCircle size={12} />
                          )}
                          Skip
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
