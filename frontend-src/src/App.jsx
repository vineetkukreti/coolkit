import { useState, useEffect, useRef } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import { ToastProvider } from './components/Toast'
import BrowserBar from './components/BrowserBar'
import ConnectGate, { useLinkedInStatus } from './components/ConnectGate'
import Dashboard from './pages/Dashboard'
import JobSearch from './pages/JobSearch'
import Posts from './pages/Posts'
import EmailOutreach from './pages/EmailOutreach'
import AppHistory from './pages/AppHistory'
import SettingsPage from './pages/Settings'
import Scraper from './pages/Scraper'
import Pipeline from './pages/Pipeline'
import EmailAnalytics from './pages/EmailAnalytics'
import AITools from './pages/AITools'
import StartupLeads from './pages/StartupLeads'
import LeadDetail from './pages/LeadDetail'
import AutoApply from './pages/AutoApply'
import { api } from './lib/api'
import { AlertTriangle, X } from 'lucide-react'

function AppShell() {
  const { running, logged_in, checking, unreachable, refresh } = useLinkedInStatus()

  const isConnected = running && logged_in

  // Track whether the user was ever connected in this session
  const wasEverConnected = useRef(false)
  const prevConnected = useRef(false)

  // Session-expired banner: running but not logged in, while user was previously connected
  const [showSessionBanner, setShowSessionBanner] = useState(false)
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)

  useEffect(() => {
    if (isConnected) {
      wasEverConnected.current = true
      // Clear the banner once the user is connected again
      setShowSessionBanner(false)
      setBannerDismissed(false)
    }

    if (prevConnected.current && !isConnected && !checking) {
      // Transition: was connected → now not connected
      if (running && !logged_in) {
        // Browser still alive but session expired — soft banner, not a hard gate
        if (!bannerDismissed) {
          setShowSessionBanner(true)
        }
      }
      // If running is false, we fall through to the hard gate below
    }

    prevConnected.current = isConnected
  }, [isConnected, running, logged_in, checking, bannerDismissed])

  const handleReconnect = async () => {
    setReconnecting(true)
    try {
      await api.openLogin()
      await api.checkLogin()
      refresh()
    } catch {
      // Ignore — the poll will catch when they log in
    } finally {
      setReconnecting(false)
    }
  }

  const handleDismissBanner = () => {
    setShowSessionBanner(false)
    setBannerDismissed(true)
  }

  // ── P0: Guard order — checking first ──────────────────────────────────────
  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-primary">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center">
            <span className="text-fg-inverse font-bold text-sm">JA</span>
          </div>
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  // ── Hard gate: browser is completely dead ──────────────────────────────────
  // Show ConnectGate when not connected AND it's not a soft session-expiry
  // (soft expiry = running is still true, handled by the banner above)
  const isHardDisconnect = !isConnected && !running
  const isSoftExpiry = !isConnected && running && !logged_in

  if (!isConnected && !isSoftExpiry) {
    // Hard gate — browser is stopped or unreachable
    return (
      <div className="flex min-h-screen">
        {/* Minimal sidebar logo */}
        <aside className="w-60 min-h-screen bg-bg-secondary border-r border-border flex flex-col px-4 py-6 shrink-0">
          <div className="flex items-center gap-2.5 px-2">
            <div className="w-9 h-9 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-fg-inverse font-bold text-sm">JA</span>
            </div>
            <span className="text-lg font-bold text-fg-primary">JobAutomate</span>
          </div>
        </aside>
        <ConnectGate wasConnected={wasEverConnected.current} />
      </div>
    )
  }

  // ── Full app (connected, or soft session expiry with banner) ──────────────
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Session expired soft banner */}
        {isSoftExpiry && showSessionBanner && (
          <div className="shrink-0 flex items-center gap-3 px-4 py-2.5 bg-warning-bg border-b border-warning/20">
            <AlertTriangle size={15} className="text-warning shrink-0" />
            <span className="flex-1 text-sm text-fg-primary">
              Your LinkedIn session has expired.
            </span>
            <button
              onClick={handleReconnect}
              disabled={reconnecting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent hover:bg-accent-dim
                text-fg-inverse text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {reconnecting ? 'Reconnecting…' : 'Reconnect'}
            </button>
            <button
              onClick={handleDismissBanner}
              className="text-fg-muted hover:text-fg-secondary transition-colors ml-1"
              aria-label="Dismiss"
            >
              <X size={14} />
            </button>
          </div>
        )}

        <BrowserBar />

        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/leads" element={<StartupLeads />} />
            <Route path="/search" element={<JobSearch />} />
            <Route path="/posts" element={<Posts />} />
            <Route path="/email" element={<EmailOutreach />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/pipeline/:id" element={<LeadDetail />} />
            <Route path="/analytics" element={<EmailAnalytics />} />
            <Route path="/ai-tools" element={<AITools />} />
            <Route path="/auto-apply" element={<AutoApply />} />
            <Route path="/history" element={<AppHistory />} />
            <Route path="/scraper" element={<Scraper />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  )
}
