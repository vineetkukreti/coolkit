import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'
import {
  Bot, Search, Mail, AlertTriangle, CheckCircle, Check,
  Loader2, Monitor, LogIn, RefreshCw, ChevronRight, Sparkles,
} from 'lucide-react'

const STORAGE_KEY = 'jobautomate_setup_complete'

// ─── useSetupCheck hook ──────────────────────────────────────────────────────

export function useSetupCheck() {
  const [needsSetup, setNeedsSetup] = useState(false)
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const completed = localStorage.getItem(STORAGE_KEY) === 'true'
    if (completed) {
      setNeedsSetup(false)
      setIsChecking(false)
      return
    }

    api.getProfile()
      .then((profile) => {
        const hasProfile = profile && profile.name
        setNeedsSetup(!hasProfile)
      })
      .catch(() => {
        setNeedsSetup(true)
      })
      .finally(() => setIsChecking(false))
  }, [])

  const markComplete = () => {
    localStorage.setItem(STORAGE_KEY, 'true')
    setNeedsSetup(false)
  }

  const resetSetup = () => {
    localStorage.removeItem(STORAGE_KEY)
    setNeedsSetup(true)
  }

  return { needsSetup, isChecking, markComplete, resetSetup }
}

// ─── Step indicator ──────────────────────────────────────────────────────────

const STEPS = ['Welcome', 'Profile', 'LinkedIn', 'All Set']

function StepIndicator({ current }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {STEPS.map((label, idx) => {
        const done = idx < current
        const active = idx === current
        return (
          <div key={label} className="flex items-center">
            {/* Circle */}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                  done
                    ? 'bg-accent text-fg-inverse'
                    : active
                    ? 'bg-accent text-fg-inverse ring-4 ring-accent/20'
                    : 'bg-bg-tertiary text-fg-muted border border-border'
                }`}
              >
                {done ? <Check size={14} /> : idx + 1}
              </div>
              <span
                className={`text-xs font-medium ${
                  active ? 'text-fg-primary' : done ? 'text-accent' : 'text-fg-muted'
                }`}
              >
                {label}
              </span>
            </div>
            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div
                className={`w-16 h-px mx-1 mb-5 transition-all duration-300 ${
                  idx < current ? 'bg-accent' : 'bg-border'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── Step 1: Welcome ─────────────────────────────────────────────────────────

function StepWelcome({ onNext }) {
  const [accepted, setAccepted] = useState(false)

  const features = [
    { icon: Bot, label: 'Auto-Apply to jobs', desc: 'Automatically apply to hundreds of matching positions' },
    { icon: Search, label: 'Scrape hiring posts', desc: 'Find hidden opportunities from LinkedIn posts' },
    { icon: Mail, label: 'AI email outreach', desc: 'Craft personalised cold emails to hiring managers' },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <div className="w-14 h-14 bg-accent-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Sparkles size={28} className="text-accent" />
        </div>
        <h2 className="text-2xl font-bold text-fg-primary mb-2">Welcome to coolkit</h2>
        <p className="text-fg-secondary text-sm">
          Automate your job search on LinkedIn with AI-powered tools
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {features.map(({ icon: Icon, label, desc }) => (
          <div key={label} className="flex items-start gap-3 p-3 rounded-xl bg-bg-tertiary border border-border">
            <div className="w-8 h-8 rounded-lg bg-accent-bg flex items-center justify-center shrink-0 mt-0.5">
              <Icon size={16} className="text-accent" />
            </div>
            <div>
              <p className="text-sm font-semibold text-fg-primary">{label}</p>
              <p className="text-xs text-fg-secondary mt-0.5">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="p-4 rounded-xl bg-warning-bg border border-warning/30 flex gap-3">
        <AlertTriangle size={18} className="text-warning shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-warning mb-1">Important Disclaimer</p>
          <p className="text-xs text-fg-secondary leading-relaxed">
            This tool automates LinkedIn actions which may violate LinkedIn's Terms of Service.
            Use at your own risk. We recommend conservative safety limits to protect your account.
          </p>
        </div>
      </div>

      {/* Checkbox */}
      <label className="flex items-center gap-3 cursor-pointer select-none group">
        <div
          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
            accepted ? 'bg-accent border-accent' : 'bg-bg-tertiary border-border group-hover:border-border-light'
          }`}
          onClick={() => setAccepted((v) => !v)}
        >
          {accepted && <Check size={12} className="text-fg-inverse" />}
        </div>
        <input
          type="checkbox"
          className="sr-only"
          checked={accepted}
          onChange={(e) => setAccepted(e.target.checked)}
        />
        <span className="text-sm text-fg-secondary">I understand and accept the risks</span>
      </label>

      <button
        onClick={onNext}
        disabled={!accepted}
        className="w-full py-3 rounded-xl bg-accent text-fg-inverse font-semibold text-sm
          hover:bg-accent-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed
          flex items-center justify-center gap-2"
      >
        I understand, let's go
        <ChevronRight size={16} />
      </button>
    </div>
  )
}

// ─── Step 2: Profile Setup ───────────────────────────────────────────────────

function StepProfile({ onNext, onBack }) {
  const [profile, setProfile] = useState({ name: '', email: '', phone: '', current_title: '' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getProfile()
      .then((data) => {
        if (data) {
          setProfile({
            name: data.name || '',
            email: data.email || '',
            phone: data.phone || '',
            current_title: data.current_title || '',
          })
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const fields = [
    { key: 'name', label: 'Full Name', placeholder: 'Your full name', type: 'text' },
    { key: 'email', label: 'Email Address', placeholder: 'you@example.com', type: 'email' },
    { key: 'phone', label: 'Phone Number', placeholder: '+91 XXXXX XXXXX', type: 'tel' },
    { key: 'current_title', label: 'Current Job Title', placeholder: 'e.g. Software Engineer', type: 'text' },
  ]

  const isValid = profile.name.trim() && profile.email.trim()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-bold text-fg-primary mb-1">Profile Setup</h2>
        <p className="text-sm text-fg-secondary">
          These details are used when applying to jobs. You can always update them later in Settings.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 size={24} className="text-accent animate-spin" />
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {fields.map(({ key, label, placeholder, type }) => (
            <div key={key}>
              <label className="block text-xs font-semibold text-fg-secondary uppercase tracking-wide mb-1.5">
                {label}
                {(key === 'name' || key === 'email') && (
                  <span className="text-danger ml-1">*</span>
                )}
              </label>
              <input
                type={type}
                value={profile[key]}
                onChange={(e) => setProfile((prev) => ({ ...prev, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full px-3.5 py-2.5 rounded-lg bg-bg-tertiary border border-border text-fg-primary
                  text-sm placeholder:text-fg-muted focus:outline-none focus:border-accent focus:ring-1
                  focus:ring-accent/20 transition-colors"
              />
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-fg-muted">
        Fields marked <span className="text-danger">*</span> are required.
      </p>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 py-3 rounded-xl bg-bg-tertiary border border-border text-fg-secondary
            text-sm font-medium hover:text-fg-primary hover:border-border-light transition-colors"
        >
          Back
        </button>
        <button
          onClick={onNext}
          disabled={!isValid || loading}
          className="flex-1 py-3 rounded-xl bg-accent text-fg-inverse font-semibold text-sm
            hover:bg-accent-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            flex items-center justify-center gap-2"
        >
          Continue
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}

// ─── Step 3: Connect LinkedIn ────────────────────────────────────────────────

const BROWSER_STATUS = {
  STOPPED: 'stopped',
  STARTING: 'starting',
  READY: 'ready',
  LOGGED_IN: 'logged_in',
}

function StepLinkedIn({ onNext, onBack }) {
  const [phase, setPhase] = useState(BROWSER_STATUS.STOPPED)
  const [error, setError] = useState('')

  // Poll for login verification
  useEffect(() => {
    if (phase !== BROWSER_STATUS.READY) return
    const interval = setInterval(async () => {
      try {
        const status = await api.getBrowserStatus()
        if (status?.logged_in) {
          setPhase(BROWSER_STATUS.LOGGED_IN)
        }
      } catch {}
    }, 3000)
    return () => clearInterval(interval)
  }, [phase])

  const handleStartBrowser = async () => {
    setError('')
    setPhase(BROWSER_STATUS.STARTING)
    try {
      await api.startBrowser()
      setPhase(BROWSER_STATUS.READY)
    } catch (err) {
      setError('Failed to start browser. Make sure the backend is running.')
      setPhase(BROWSER_STATUS.STOPPED)
    }
  }

  const handleOpenLogin = async () => {
    setError('')
    try {
      await api.openLogin()
    } catch {
      setError('Failed to open LinkedIn login page.')
    }
  }

  const handleVerifyLogin = async () => {
    setError('')
    try {
      const status = await api.checkLogin()
      if (status?.logged_in) {
        setPhase(BROWSER_STATUS.LOGGED_IN)
      } else {
        setError('Not logged in yet. Please complete the LinkedIn login in the browser window.')
      }
    } catch {
      setError('Could not verify login status.')
    }
  }

  const statusLabel = {
    [BROWSER_STATUS.STOPPED]: { text: 'Browser not started', color: 'text-danger', dot: 'bg-danger' },
    [BROWSER_STATUS.STARTING]: { text: 'Browser starting…', color: 'text-warning', dot: 'bg-warning animate-pulse' },
    [BROWSER_STATUS.READY]: { text: 'Browser ready — awaiting login', color: 'text-warning', dot: 'bg-warning' },
    [BROWSER_STATUS.LOGGED_IN]: { text: 'LinkedIn connected', color: 'text-success', dot: 'bg-success' },
  }[phase]

  const steps = [
    {
      num: 1,
      title: 'Start Browser',
      desc: 'Launches a Chrome window in the background',
      button: (
        <button
          onClick={handleStartBrowser}
          disabled={phase !== BROWSER_STATUS.STOPPED}
          className="px-4 py-2 rounded-lg bg-accent text-fg-inverse text-sm font-medium
            hover:bg-accent-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed
            flex items-center gap-2"
        >
          {phase === BROWSER_STATUS.STARTING ? (
            <><Loader2 size={14} className="animate-spin" /> Starting…</>
          ) : (
            <><Monitor size={14} /> Start Browser</>
          )}
        </button>
      ),
      done: phase !== BROWSER_STATUS.STOPPED && phase !== BROWSER_STATUS.STARTING,
    },
    {
      num: 2,
      title: 'Open LinkedIn Login',
      desc: 'Opens the LinkedIn login page in the browser',
      button: (
        <button
          onClick={handleOpenLogin}
          disabled={phase === BROWSER_STATUS.STOPPED || phase === BROWSER_STATUS.STARTING}
          className="px-4 py-2 rounded-lg bg-bg-tertiary border border-border text-fg-secondary text-sm
            font-medium hover:text-fg-primary hover:border-border-light transition-colors
            disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <LogIn size={14} /> Open Login Page
        </button>
      ),
      done: phase === BROWSER_STATUS.LOGGED_IN,
    },
    {
      num: 3,
      title: 'Verify Login',
      desc: 'Confirm that you\'re logged into LinkedIn',
      button: (
        <button
          onClick={handleVerifyLogin}
          disabled={phase === BROWSER_STATUS.STOPPED || phase === BROWSER_STATUS.STARTING}
          className="px-4 py-2 rounded-lg bg-bg-tertiary border border-border text-fg-secondary text-sm
            font-medium hover:text-fg-primary hover:border-border-light transition-colors
            disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {phase === BROWSER_STATUS.LOGGED_IN ? (
            <><CheckCircle size={14} className="text-success" /> Verified!</>
          ) : (
            <><RefreshCw size={14} /> Verify Login</>
          )}
        </button>
      ),
      done: phase === BROWSER_STATUS.LOGGED_IN,
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-bold text-fg-primary mb-1">Connect Your LinkedIn Account</h2>
        <p className="text-sm text-fg-secondary leading-relaxed">
          coolkit uses a real browser session to interact with LinkedIn — just like you would manually.
          You'll need to log in once and your session is saved for future runs.
        </p>
      </div>

      {/* Status pill */}
      <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-bg-tertiary border border-border w-fit">
        <div className={`w-2 h-2 rounded-full ${statusLabel.dot}`} />
        <span className={`text-xs font-medium ${statusLabel.color}`}>{statusLabel.text}</span>
      </div>

      {/* Three-step visual */}
      <div className="flex flex-col gap-3">
        {steps.map(({ num, title, desc, button, done }) => (
          <div
            key={num}
            className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
              done ? 'bg-success-bg border-success/30' : 'bg-bg-tertiary border-border'
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  done ? 'bg-success text-fg-inverse' : 'bg-bg-primary text-fg-muted border border-border'
                }`}
              >
                {done ? <Check size={13} /> : num}
              </div>
              <div>
                <p className="text-sm font-semibold text-fg-primary">{title}</p>
                <p className="text-xs text-fg-secondary mt-0.5">{desc}</p>
              </div>
            </div>
            {button}
          </div>
        ))}
      </div>

      {/* Note */}
      <p className="text-xs text-fg-muted bg-bg-tertiary border border-border rounded-lg px-3 py-2.5 leading-relaxed">
        A Chrome window will open on your desktop. Log into LinkedIn normally, then come back here and click "Verify Login".
      </p>

      {error && (
        <p className="text-xs text-danger bg-danger-bg border border-danger/30 rounded-lg px-3 py-2.5">
          {error}
        </p>
      )}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 py-3 rounded-xl bg-bg-tertiary border border-border text-fg-secondary
            text-sm font-medium hover:text-fg-primary hover:border-border-light transition-colors"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="flex-1 py-3 rounded-xl bg-accent text-fg-inverse font-semibold text-sm
            hover:bg-accent-dim transition-colors flex items-center justify-center gap-2"
        >
          {phase === BROWSER_STATUS.LOGGED_IN ? (
            <><CheckCircle size={16} /> Continue</>
          ) : (
            <>Skip for now <ChevronRight size={16} /></>
          )}
        </button>
      </div>
    </div>
  )
}

// ─── Step 4: All Set ─────────────────────────────────────────────────────────

function StepAllSet({ onComplete }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="flex flex-col items-center gap-6 text-center py-4">
      {/* Animated checkmark */}
      <div
        className={`w-20 h-20 rounded-full bg-success-bg border-2 border-success flex items-center justify-center
          transition-all duration-500 ease-out ${visible ? 'scale-100 opacity-100' : 'scale-50 opacity-0'}`}
      >
        <CheckCircle size={40} className="text-success" />
      </div>

      <div>
        <h2 className="text-2xl font-bold text-fg-primary mb-2">You're all set!</h2>
        <p className="text-sm text-fg-secondary leading-relaxed max-w-sm mx-auto">
          coolkit is configured and ready to help you land your next role.
        </p>
      </div>

      {/* Summary */}
      <div className="w-full flex flex-col gap-2 text-left">
        {[
          { label: 'Profile', value: 'Basic info configured' },
          { label: 'Browser', value: 'Automation engine set up' },
          { label: 'Auto-Apply', value: 'Ready to run from the Auto-Apply page' },
          { label: 'Job Search', value: 'Scrape LinkedIn jobs from the Search page' },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center gap-3 px-4 py-3 rounded-xl bg-bg-tertiary border border-border">
            <div className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
            <span className="text-xs font-semibold text-fg-secondary w-24 shrink-0">{label}</span>
            <span className="text-xs text-fg-primary">{value}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-fg-muted">
        Optional: Configure email outreach credentials in{' '}
        <span className="text-accent font-medium">Settings → Email</span>
      </p>

      <button
        onClick={onComplete}
        className="w-full py-3 rounded-xl bg-accent text-fg-inverse font-semibold text-sm
          hover:bg-accent-dim transition-colors flex items-center justify-center gap-2"
      >
        <Sparkles size={16} />
        Start Exploring
      </button>
    </div>
  )
}

// ─── Main Onboarding component ───────────────────────────────────────────────

export default function Onboarding({ onComplete }) {
  const [step, setStep] = useState(0)

  const next = useCallback(() => setStep((s) => Math.min(s + 1, 3)), [])
  const back = useCallback(() => setStep((s) => Math.max(s - 1, 0)), [])

  const handleComplete = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true')
    onComplete?.()
  }, [onComplete])

  return (
    // Full-screen overlay
    <div className="fixed inset-0 z-[9000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      {/* Modal card */}
      <div className="w-full max-w-2xl bg-bg-secondary rounded-2xl border border-border shadow-2xl shadow-black/60 p-8 max-h-[90vh] overflow-y-auto">
        <StepIndicator current={step} />

        {step === 0 && <StepWelcome onNext={next} />}
        {step === 1 && <StepProfile onNext={next} onBack={back} />}
        {step === 2 && <StepLinkedIn onNext={next} onBack={back} />}
        {step === 3 && <StepAllSet onComplete={handleComplete} />}
      </div>
    </div>
  )
}
