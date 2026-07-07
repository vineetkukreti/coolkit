import { useState, useEffect, useRef } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import BrowserBar from './components/BrowserBar'
import { useLinkedInStatus } from './components/ConnectGate'
import { AuthProvider } from './lib/auth'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import FindJobs from './pages/FindJobs'
import ApplyPage from './pages/ApplyPage'
import OutreachPage from './pages/OutreachPage'
import InsightsPage from './pages/InsightsPage'
import Pipeline from './pages/Pipeline'
import LeadDetail from './pages/LeadDetail'
import AITools from './pages/AITools'
import SkillsIntelligence from './pages/SkillsIntelligence'
import SettingsPage from './pages/Settings'
import Logs from './pages/Logs'
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
    prevConnected.current = isConnected
  }, [isConnected])

  useEffect(() => {
    if (prevConnected.current && !isConnected && !checking) {
      // Transition: was connected → now not connected
      if (running && !logged_in) {
        // Browser still alive but session expired — soft banner, not a hard gate
        if (!bannerDismissed) {
          setShowSessionBanner(true)
        }
      }
      // Browser fully stopped — BrowserBar handles reconnection
    }
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

  const isSoftExpiry = !isConnected && running && !logged_in

  // ── Full app (always accessible — connect via BrowserBar when ready) ──────
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
            {/* Primary routes */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/find" element={<FindJobs />} />
            <Route path="/apply" element={<ApplyPage />} />
            <Route path="/outreach" element={<OutreachPage />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/pipeline/:id" element={<LeadDetail />} />
            <Route path="/insights" element={<InsightsPage />} />
            <Route path="/ai-tools" element={<AITools />} />
            <Route path="/skills" element={<SkillsIntelligence />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/logs" element={<Logs />} />

            {/* Redirects from old routes */}
            <Route path="/search" element={<Navigate to="/find?tab=search" replace />} />
            <Route path="/scraper" element={<Navigate to="/find?tab=scraper" replace />} />
            <Route path="/posts" element={<Navigate to="/find?tab=posts" replace />} />
            <Route path="/auto-apply" element={<Navigate to="/apply?tab=engine" replace />} />
            <Route path="/history" element={<Navigate to="/apply?tab=history" replace />} />
            <Route path="/email" element={<Navigate to="/outreach?tab=email" replace />} />
            <Route path="/leads" element={<Navigate to="/outreach?tab=leads" replace />} />
            <Route path="/analytics" element={<Navigate to="/insights?tab=analytics" replace />} />
            <Route path="/quality" element={<Navigate to="/insights?tab=quality" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}
