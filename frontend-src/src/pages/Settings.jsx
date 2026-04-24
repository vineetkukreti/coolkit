import { useEffect, useState } from 'react'
import {
  FileText,
  Mail,
  CheckCircle2,
  Loader2,
  Key,
  Send,
  Eye,
  EyeOff,
  AlertCircle,
  Sparkles,
  Server,
  User,
  Globe,
  Play,
  Square,
  LogIn,
  Wifi,
  WifiOff,
  Upload,
} from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'

/* ─── tiny helpers ─── */

function Label({ children }) {
  return <p className="text-fg-muted text-xs font-medium uppercase tracking-wider mb-1.5">{children}</p>
}

function HelperText({ children }) {
  return <p className="text-fg-muted text-xs mt-1.5 leading-relaxed">{children}</p>
}

function Input({ value, onChange, placeholder, type = 'text', mono = false, readOnly = false, small = false }) {
  return (
    <input
      type={type}
      value={value ?? ''}
      onChange={onChange}
      placeholder={placeholder}
      readOnly={readOnly}
      className={`w-full bg-bg-tertiary border border-border rounded-lg text-fg-primary placeholder:text-fg-muted focus:outline-none focus:border-accent transition-colors ${mono ? 'font-mono' : 'font-sans'} ${small ? 'px-3 py-1.5 text-sm' : 'px-3.5 py-2.5 text-sm'} ${readOnly ? 'opacity-60 cursor-not-allowed' : ''}`}
    />
  )
}

function Card({ title, icon: Icon, children, badge, action }) {
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          {Icon && <Icon size={16} className="text-accent" />}
          <h2 className="text-fg-primary text-sm font-semibold">{title}</h2>
        </div>
        <div className="flex items-center gap-2">
          {badge}
          {action}
        </div>
      </div>
      <div className="px-5 py-5">{children}</div>
    </div>
  )
}


/* ─── Browser Status Section ─── */
function BrowserStatusCard({ toast }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)

  useEffect(() => {
    fetchStatus()
  }, [])

  async function fetchStatus() {
    try {
      const data = await api.getBrowserStatus()
      setStatus(data)
    } catch {
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(action, label) {
    setActionLoading(label)
    try {
      await action()
      await fetchStatus()
    } catch (e) {
      toast({ title: 'Action failed', description: e.message, type: 'error' })
    } finally {
      setActionLoading(null)
    }
  }

  const isRunning = status?.running ?? false
  const isLoggedIn = status?.logged_in ?? false

  return (
    <Card
      title="LinkedIn Connection"
      icon={Globe}
      badge={
        loading ? null : isRunning ? (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-success-bg text-success text-xs font-medium border border-success/30">
            <Wifi size={11} />
            Browser Active
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-bg-tertiary text-fg-muted text-xs font-medium border border-border">
            <WifiOff size={11} />
            Offline
          </span>
        )
      }
    >
      {loading ? (
        <div className="flex items-center gap-2 py-4 text-fg-muted">
          <Loader2 size={15} className="animate-spin text-accent" />
          <span className="text-sm">Checking browser status…</span>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Status row */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary border border-border">
            <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isRunning ? 'bg-success animate-pulse' : 'bg-fg-muted'}`} />
            <div className="flex-1 min-w-0">
              <p className="text-fg-primary text-sm font-medium">
                {isRunning ? 'Browser is running' : 'Browser is stopped'}
              </p>
              <p className="text-fg-muted text-xs mt-0.5">
                {isRunning
                  ? isLoggedIn
                    ? 'LinkedIn session active — ready to apply'
                    : 'Running but not logged in to LinkedIn'
                  : 'Start the browser to begin automating applications'
                }
              </p>
            </div>
            {isRunning && (
              <div className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${isLoggedIn ? 'bg-success-bg text-success border border-success/30' : 'bg-warning-bg text-warning border border-warning/30'}`}>
                {isLoggedIn ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
                {isLoggedIn ? 'Logged in' : 'Not logged in'}
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {!isRunning ? (
              <button
                onClick={() => handleAction(api.startBrowser, 'start')}
                disabled={actionLoading !== null}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-success hover:bg-success/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60"
              >
                {actionLoading === 'start' ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                Start Browser
              </button>
            ) : (
              <>
                {!isLoggedIn && (
                  <button
                    onClick={() => handleAction(api.openLogin, 'login')}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60"
                  >
                    {actionLoading === 'login' ? <Loader2 size={13} className="animate-spin" /> : <LogIn size={13} />}
                    Login to LinkedIn
                  </button>
                )}
                <button
                  onClick={() => handleAction(api.stopBrowser, 'stop')}
                  disabled={actionLoading !== null}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-bg-tertiary border border-border text-fg-secondary text-xs font-medium rounded-lg hover:text-danger hover:border-danger/40 transition-colors disabled:opacity-60"
                >
                  {actionLoading === 'stop' ? <Loader2 size={13} className="animate-spin" /> : <Square size={13} />}
                  Stop Browser
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}

/* ─── Resume Upload Card ─── */

function ResumeCard({ toast, resumeFileName: initialName, onUploaded }) {
  const [resumeInfo, setResumeInfo] = useState({ exists: !!initialName, filename: initialName, size_kb: 0 })
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    api.getResumeStatus().then(setResumeInfo).catch(() => {})
  }, [])

  async function handleFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast({ title: 'Invalid file', description: 'Only PDF files are allowed.', type: 'error' })
      return
    }
    setUploading(true)
    try {
      const res = await api.uploadResume(file)
      setResumeInfo({ exists: true, filename: res.filename, path: res.path, size_kb: Math.round(file.size / 1024) })
      onUploaded?.(res.filename, res.path)
      toast({ title: 'Resume uploaded', description: res.message, type: 'success' })
    } catch (e) {
      toast({ title: 'Upload failed', description: e.message, type: 'error' })
    } finally {
      setUploading(false)
    }
  }

  function handleInputChange(e) {
    handleFile(e.target.files?.[0])
    e.target.value = ''
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  return (
    <Card title="Resume" icon={FileText}>
      {resumeInfo.exists ? (
        <>
          <div className="flex items-center gap-4 mb-3">
            <div className="w-11 h-11 rounded-xl bg-bg-tertiary border border-border flex items-center justify-center flex-shrink-0">
              <FileText size={20} className="text-accent" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-fg-primary text-sm font-medium truncate">{resumeInfo.filename}</p>
              <p className="text-fg-muted text-xs mt-0.5">
                PDF Document{resumeInfo.size_kb ? ` — ${resumeInfo.size_kb} KB` : ''}
              </p>
            </div>
            <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-success-bg border border-success/30 text-success text-xs font-medium flex-shrink-0">
              <CheckCircle2 size={11} />
              Set
            </div>
          </div>
          <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-fg-secondary text-xs cursor-pointer hover:text-fg-primary hover:border-fg-muted transition-colors">
            <Upload size={12} />
            Replace Resume
            <input type="file" accept=".pdf" onChange={handleInputChange} className="hidden" />
          </label>
        </>
      ) : (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${dragOver ? 'border-accent bg-accent-bg/30' : 'border-border'}`}
        >
          <div className="w-12 h-12 rounded-full bg-bg-tertiary border border-border flex items-center justify-center mx-auto mb-3">
            {uploading ? <Loader2 size={20} className="animate-spin text-accent" /> : <Upload size={20} className="text-fg-muted" />}
          </div>
          <p className="text-fg-primary text-sm font-medium mb-1">
            {uploading ? 'Uploading...' : 'Upload your resume'}
          </p>
          <p className="text-fg-muted text-xs mb-3">
            Drag &amp; drop a PDF here, or click to browse
          </p>
          <label className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-white text-xs font-medium cursor-pointer hover:bg-accent/90 transition-colors">
            <Upload size={12} />
            Choose PDF
            <input type="file" accept=".pdf" onChange={handleInputChange} className="hidden" disabled={uploading} />
          </label>
        </div>
      )}
    </Card>
  )
}

/* ─── Main Settings component ─── */

export default function Settings() {
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)

  // Profile form
  const [profile, setProfile] = useState({
    name: '', email: '', phone: '', linkedin: '', github: '', website: '',
    location: '', current_title: '', experience_years: 2, notice_period_days: 30,
    resume_path: '',
  })
  const [profileSaving, setProfileSaving] = useState(false)

  // SMTP form
  const [smtp, setSmtp] = useState({
    smtp_host: 'smtp.gmail.com', smtp_port: 587, smtp_user: '',
    smtp_password: '', from_email: '', from_name: '',
  })
  const [smtpSaving, setSmtpSaving] = useState(false)
  const [smtpConfigured, setSmtpConfigured] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)

  // Gemini
  const [geminiKey, setGeminiKey] = useState('')
  const [geminiSet, setGeminiSet] = useState(false)
  const [geminiPreview, setGeminiPreview] = useState('')
  const [geminiSaving, setGeminiSaving] = useState(false)
  const [showGeminiKey, setShowGeminiKey] = useState(false)


  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    try {
      const data = await api.getAllSettings()

      if (data.profile) {
        setProfile(prev => ({ ...prev, ...data.profile }))
      }

      if (data.smtp) {
        setSmtp(prev => ({
          ...prev,
          smtp_host: data.smtp.smtp_host || 'smtp.gmail.com',
          smtp_port: data.smtp.smtp_port || 587,
          smtp_user: data.smtp.smtp_user || '',
          from_email: data.smtp.from_email || '',
          from_name: data.smtp.from_name || '',
          smtp_password: '',
        }))
        setSmtpConfigured(data.smtp.smtp_password_set)
      }

      if (data.gemini) {
        setGeminiSet(data.gemini.api_key_set)
        setGeminiPreview(data.gemini.api_key_preview || '')
      }

    } catch {
      // silently fall back to defaults
    } finally {
      setLoading(false)
    }
  }

  // ── Save handlers ──

  async function saveProfile() {
    setProfileSaving(true)
    try {
      await api.saveProfile(profile)
      toast({ title: 'Profile saved', description: 'Your profile information has been updated.', type: 'success' })
    } catch (e) {
      toast({ title: 'Save failed', description: e.message, type: 'error' })
    } finally {
      setProfileSaving(false)
    }
  }

  async function saveSMTP() {
    setSmtpSaving(true)
    try {
      await api.saveSMTP(smtp)
      setSmtpConfigured(true)
      toast({ title: 'Email settings saved', description: 'Your email server configuration has been updated.', type: 'success' })
    } catch (e) {
      toast({ title: 'Save failed', description: e.message, type: 'error' })
    } finally {
      setSmtpSaving(false)
    }
  }

  async function testConnection() {
    setTestingConnection(true)
    try {
      if (smtpConfigured) {
        // If already configured, call test endpoint
        const res = await api.testEmail()
        toast({ title: 'Connection successful', description: res.message || 'Email configuration looks good', type: 'success' })
      } else {
        toast({ title: 'Not configured', description: 'Save your email settings first before testing.', type: 'warning' })
      }
    } catch (e) {
      toast({ title: 'Connection failed', description: e.message, type: 'error' })
    } finally {
      setTestingConnection(false)
    }
  }

  async function saveGemini() {
    if (!geminiKey.trim()) return
    setGeminiSaving(true)
    try {
      await api.saveGemini({ api_key: geminiKey.trim() })
      setGeminiSet(true)
      setGeminiPreview(geminiKey.trim().slice(0, 8) + '...')
      setGeminiKey('')
      toast({ title: 'Gemini API key saved', description: 'AI email generation is now active.', type: 'success' })
    } catch (e) {
      toast({ title: 'Save failed', description: e.message, type: 'error' })
    } finally {
      setGeminiSaving(false)
    }
  }


  // ── Field helpers ──

  function pf(key) {
    return {
      value: profile[key],
      onChange: (e) => setProfile(prev => ({ ...prev, [key]: e.target.value })),
    }
  }

  function sf(key) {
    return {
      value: smtp[key],
      onChange: (e) => setSmtp(prev => ({ ...prev, [key]: e.target.value })),
    }
  }


  const initials = profile.name?.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase() || 'VK'
  const resumeFileName = profile.resume_path ? profile.resume_path.split('/').pop() : null

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary px-6 py-8 font-sans">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-fg-primary">Settings</h1>
        <p className="text-fg-muted text-sm mt-1">Configure everything from here — profile, email, API keys, and protection limits</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-3 py-32 text-fg-muted">
          <Loader2 size={22} className="animate-spin text-accent" />
          <span className="text-sm">Loading settings...</span>
        </div>
      ) : (
        <div className="space-y-6 max-w-5xl">

          {/* ── Row 1: Profile + (Resume + Gemini + LinkedIn Connection) ── */}
          <div className="flex gap-6 items-start">
            {/* Left: Profile */}
            <div className="flex-1 min-w-0">
              <Card
                title="Profile Information"
                icon={User}
                action={
                  <button
                    onClick={saveProfile}
                    disabled={profileSaving}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60"
                  >
                    {profileSaving ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                    {profileSaving ? 'Saving...' : 'Save'}
                  </button>
                }
              >
                {/* Avatar + name */}
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-14 h-14 rounded-full bg-accent-bg border border-accent/30 flex items-center justify-center flex-shrink-0">
                    <span className="text-accent font-semibold text-lg font-mono">{initials}</span>
                  </div>
                  <div className="flex-1 grid grid-cols-2 gap-3">
                    <div>
                      <Label>Full Name</Label>
                      <Input {...pf('name')} placeholder="Vineet Kukreti" />
                    </div>
                    <div>
                      <Label>Current Title</Label>
                      <Input {...pf('current_title')} placeholder="AI Engineer" />
                    </div>
                  </div>
                </div>

                <div className="border-t border-border mb-5" />

                <div className="grid grid-cols-2 gap-x-5 gap-y-4">
                  <div>
                    <Label>Email</Label>
                    <Input {...pf('email')} placeholder="you@example.com" />
                  </div>
                  <div>
                    <Label>Phone</Label>
                    <Input {...pf('phone')} placeholder="+91 XXXXX XXXXX" />
                  </div>
                  <div>
                    <Label>LinkedIn</Label>
                    <Input {...pf('linkedin')} placeholder="linkedin.com/in/handle" />
                  </div>
                  <div>
                    <Label>GitHub</Label>
                    <Input {...pf('github')} placeholder="github.com/handle" />
                  </div>
                  <div>
                    <Label>Location</Label>
                    <Input {...pf('location')} placeholder="City, Country" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Experience (yrs)</Label>
                      <Input {...pf('experience_years')} placeholder="2" type="number" mono />
                    </div>
                    <div>
                      <Label>Notice (days)</Label>
                      <Input {...pf('notice_period_days')} placeholder="30" type="number" mono />
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Right column: LinkedIn Connection + Resume + Gemini */}
            <div className="w-[380px] flex-shrink-0 flex flex-col gap-5">

              {/* LinkedIn Connection */}
              <BrowserStatusCard toast={toast} />

              {/* Resume */}
              <ResumeCard toast={toast} resumeFileName={resumeFileName} onUploaded={(name, path) => setProfile(prev => ({ ...prev, resume_path: path }))} />

              {/* Gemini API Key */}
              <Card
                title="Gemini API Key"
                icon={Sparkles}
                badge={
                  geminiSet ? (
                    <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-success-bg text-success text-xs font-medium border border-success/30">
                      <CheckCircle2 size={11} />
                      Active
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-danger-bg text-danger text-xs font-medium border border-danger/30">
                      <AlertCircle size={11} />
                      Not Set
                    </span>
                  )
                }
              >
                {geminiSet && (
                  <p className="text-fg-muted text-xs mb-3 font-mono">{geminiPreview}</p>
                )}
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <input
                      type={showGeminiKey ? 'text' : 'password'}
                      value={geminiKey}
                      onChange={(e) => setGeminiKey(e.target.value)}
                      placeholder={geminiSet ? 'Enter new key to replace...' : 'AIzaSy...'}
                      className="w-full bg-bg-tertiary border border-border rounded-lg text-fg-primary text-sm font-mono px-3.5 py-2.5 pr-10 focus:outline-none focus:border-accent placeholder:text-fg-muted"
                    />
                    <button
                      onClick={() => setShowGeminiKey(!showGeminiKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg-primary"
                    >
                      {showGeminiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                  <button
                    onClick={saveGemini}
                    disabled={geminiSaving || !geminiKey.trim()}
                    className="flex items-center gap-1.5 px-4 py-2.5 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60 flex-shrink-0"
                  >
                    {geminiSaving ? <Loader2 size={13} className="animate-spin" /> : <Key size={13} />}
                    Save
                  </button>
                </div>
                <p className="text-fg-muted text-xs mt-2">
                  Used for AI email generation. Get a key at{' '}
                  <span className="text-accent">aistudio.google.com</span>
                </p>
              </Card>
            </div>
          </div>

          {/* ── Row 2: Email Server + Account Protection ── */}
          <div className="flex gap-6 items-start">

            {/* Email Server Settings */}
            <div className="flex-1 min-w-0">
              <Card
                title="Email Server Settings"
                icon={Server}
                badge={
                  smtpConfigured ? (
                    <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-success-bg text-success text-xs font-medium border border-success/30">
                      <CheckCircle2 size={11} />
                      Connected
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-danger-bg text-danger text-xs font-medium border border-danger/30">
                      <AlertCircle size={11} />
                      Not Configured
                    </span>
                  )
                }
                action={
                  <div className="flex items-center gap-2">
                    <button
                      onClick={testConnection}
                      disabled={testingConnection}
                      title={smtpConfigured ? 'Test email server connection' : 'Save settings first'}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-bg-tertiary border border-border text-fg-secondary text-xs font-medium rounded-lg hover:text-fg-primary hover:border-accent/50 transition-colors disabled:opacity-40"
                    >
                      {testingConnection ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                      Test Connection
                    </button>
                    <button
                      onClick={saveSMTP}
                      disabled={smtpSaving}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60"
                    >
                      {smtpSaving ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                      Save
                    </button>
                  </div>
                }
              >
                <div className="grid grid-cols-2 gap-x-5 gap-y-4">
                  <div>
                    <Label>SMTP Host</Label>
                    <Input {...sf('smtp_host')} placeholder="smtp.gmail.com" mono />
                  </div>
                  <div>
                    <Label>Port</Label>
                    <Input
                      value={smtp.smtp_port}
                      onChange={(e) => setSmtp(prev => ({ ...prev, smtp_port: parseInt(e.target.value) || 587 }))}
                      placeholder="587"
                      type="number"
                      mono
                    />
                  </div>
                  <div>
                    <Label>SMTP Username</Label>
                    <Input {...sf('smtp_user')} placeholder="you@gmail.com" />
                  </div>
                  <div>
                    <Label>App Password</Label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={smtp.smtp_password}
                        onChange={(e) => setSmtp(prev => ({ ...prev, smtp_password: e.target.value }))}
                        placeholder={smtpConfigured ? '(saved — enter new to change)' : 'xxxx xxxx xxxx xxxx'}
                        className="w-full bg-bg-tertiary border border-border rounded-lg text-fg-primary text-sm font-mono px-3.5 py-2.5 pr-10 focus:outline-none focus:border-accent placeholder:text-fg-muted"
                      />
                      <button
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg-primary"
                      >
                        {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <Label>From Email</Label>
                    <Input {...sf('from_email')} placeholder="you@gmail.com" />
                  </div>
                  <div>
                    <Label>From Name</Label>
                    <Input {...sf('from_name')} placeholder="Vineet Kukreti" />
                  </div>
                </div>

                <div className="mt-4 p-3 rounded-lg bg-bg-tertiary border border-border">
                  <p className="text-fg-muted text-xs leading-relaxed">
                    <strong className="text-fg-secondary">Gmail setup:</strong> Enable 2-Step Verification, then create an App Password at{' '}
                    <span className="text-accent font-mono">myaccount.google.com/apppasswords</span>.
                    Use the 16-character password above (not your Gmail password).
                  </p>
                </div>
              </Card>
            </div>


          </div>
        </div>
      )}
    </div>
  )
}
