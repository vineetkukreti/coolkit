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
  Plug,
  SlidersHorizontal,
  Wrench,
  Download,
  Info,
} from 'lucide-react'
import { api } from '../lib/api'
import { useToast } from '../components/Toast'
import PageTabs from '../components/PageTabs'

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

/* ─── Resume Variants Card ─── */

function ResumeVariantsCard({ toast }) {
  const [variants, setVariants] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(null) // variant name being uploaded

  // Test selection state
  const [testText, setTestText] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    loadVariants()
  }, [])

  async function loadVariants() {
    try {
      const data = await api.getResumeVariants()
      setVariants(data.variants || [])
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(variantName, file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      toast({ title: 'Invalid file', description: 'Only PDF files are allowed.', type: 'error' })
      return
    }
    setUploading(variantName)
    try {
      const res = await api.uploadVariantResume(variantName, file)
      toast({ title: 'Resume uploaded', description: `${res.filename} set for "${variantName}" (${res.size_kb} KB)`, type: 'success' })
      loadVariants()
    } catch (e) {
      toast({ title: 'Upload failed', description: e.message, type: 'error' })
    } finally {
      setUploading(null)
    }
  }

  async function testSelection() {
    if (!testText.trim()) return
    setTesting(true)
    try {
      const res = await api.testResumeSelection({ role: testText, content: testText })
      setTestResult(res)
    } catch (e) {
      toast({ title: 'Test failed', description: e.message, type: 'error' })
    } finally {
      setTesting(false)
    }
  }

  const variantColors = {
    'healthcare-ai': 'text-emerald-400',
    'genai-platform': 'text-violet-400',
    'data-engineering': 'text-blue-400',
    'default': 'text-fg-muted',
  }

  return (
    <Card title="Resume Variants" icon={FileText} badge={
      <span className="text-fg-muted text-xs">{variants.filter(v => v.exists).length}/{variants.length} uploaded</span>
    }>
      {loading ? (
        <div className="flex items-center gap-2 py-4 text-fg-muted">
          <Loader2 size={15} className="animate-spin text-accent" />
          <span className="text-sm">Loading variants...</span>
        </div>
      ) : (
        <div className="space-y-3">
          {variants.map((v) => (
            <div key={v.name} className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary border border-border">
              <div className="w-9 h-9 rounded-lg bg-bg-primary border border-border flex items-center justify-center flex-shrink-0">
                <FileText size={16} className={variantColors[v.name] || 'text-fg-muted'} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-fg-primary text-sm font-medium">{v.name}</p>
                <p className="text-fg-muted text-xs mt-0.5 truncate">{v.description}</p>
                {v.keywords.length > 0 && (
                  <p className="text-fg-muted text-xs mt-1 opacity-60 truncate">
                    {v.keywords.slice(0, 5).join(', ')}{v.keywords.length > 5 ? ` +${v.keywords.length - 5} more` : ''}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {v.exists ? (
                  <span className="flex items-center gap-1 px-2 py-1 rounded-lg bg-success-bg border border-success/30 text-success text-xs font-medium">
                    <CheckCircle2 size={11} />
                    {v.size_kb} KB
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-2 py-1 rounded-lg bg-danger-bg border border-danger/30 text-danger text-xs font-medium">
                    <AlertCircle size={11} />
                    Missing
                  </span>
                )}
                <label className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-border text-fg-secondary text-xs cursor-pointer hover:text-fg-primary hover:border-fg-muted transition-colors">
                  {uploading === v.name ? <Loader2 size={11} className="animate-spin" /> : <Upload size={11} />}
                  {v.exists ? 'Replace' : 'Upload'}
                  <input type="file" accept=".pdf" onChange={(e) => { handleUpload(v.name, e.target.files?.[0]); e.target.value = '' }} className="hidden" />
                </label>
              </div>
            </div>
          ))}

          {/* Test Selection */}
          <div className="border-t border-border pt-3 mt-3">
            <p className="text-fg-muted text-xs font-medium uppercase tracking-wider mb-2">Test Selection</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                placeholder="Paste job title or description..."
                className="flex-1 bg-bg-tertiary border border-border rounded-lg text-fg-primary text-xs px-3 py-2 focus:outline-none focus:border-accent placeholder:text-fg-muted"
                onKeyDown={(e) => e.key === 'Enter' && testSelection()}
              />
              <button
                onClick={testSelection}
                disabled={testing || !testText.trim()}
                className="flex items-center gap-1 px-3 py-2 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60 flex-shrink-0"
              >
                {testing ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
                Test
              </button>
            </div>
            {testResult && (
              <div className="mt-2 p-2.5 rounded-lg bg-bg-primary border border-border">
                <p className="text-fg-primary text-xs font-medium mb-1.5">
                  Selected: <span className={variantColors[testResult.selected] || ''}>{testResult.selected}</span>
                </p>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {Object.entries(testResult.scores || {}).map(([name, info]) => (
                    <span key={name} className="text-fg-muted text-xs">
                      {name}: <span className={`font-mono ${info.score >= 2 ? 'text-success' : 'text-fg-muted'}`}>{info.score.toFixed(1)}</span>
                      <span className="opacity-50"> ({info.hits} hits)</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}

/* ─── Email Config Status ─── */

function EmailConfigStatus() {
  const [config, setConfig] = useState(null)

  useEffect(() => {
    api.getEmailConfig().then(setConfig).catch(() => {})
  }, [])

  if (!config) return null

  return (
    <Card title="Email Config Status" icon={Info}>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Status</Label>
          <div className="flex items-center gap-2">
            {config.configured ? (
              <><CheckCircle2 size={14} className="text-success" /><span className="text-sm text-success">Configured</span></>
            ) : (
              <><AlertCircle size={14} className="text-danger" /><span className="text-sm text-danger">Not Configured</span></>
            )}
          </div>
        </div>
        {config.smtp_host && (
          <div>
            <Label>SMTP Host</Label>
            <p className="text-sm text-fg-primary font-mono">{config.smtp_host}</p>
          </div>
        )}
        {config.from_email && (
          <div>
            <Label>From Email</Label>
            <p className="text-sm text-fg-primary font-mono">{config.from_email}</p>
          </div>
        )}
        {config.from_name && (
          <div>
            <Label>From Name</Label>
            <p className="text-sm text-fg-primary">{config.from_name}</p>
          </div>
        )}
      </div>
    </Card>
  )
}

/* ─── Resume Status ─── */

function ResumeStatusCard() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    api.getResumeStatus().then(setStatus).catch(() => {})
  }, [])

  if (!status) return null

  return (
    <Card title="Resume Status" icon={FileText}>
      <div className="flex items-center gap-4">
        {status.exists ? (
          <>
            <CheckCircle2 size={16} className="text-success" />
            <div>
              <p className="text-sm text-fg-primary font-medium">Resume uploaded</p>
              <p className="text-xs text-fg-muted">
                {status.filename || 'resume.pdf'} · {status.size_kb ? `${status.size_kb.toFixed(0)} KB` : ''}
              </p>
            </div>
          </>
        ) : (
          <>
            <AlertCircle size={16} className="text-warning" />
            <div>
              <p className="text-sm text-fg-primary font-medium">No resume uploaded</p>
              <p className="text-xs text-fg-muted">Upload a resume in the Resume Variants section below</p>
            </div>
          </>
        )}
      </div>
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
    location: '', current_title: '', experience_years: 0, notice_period_days: 30,
    resume_path: '', employer: '', employer_domain: '',
    current_salary: 0, desired_salary: 0,
    education: '', education_level: "Bachelor's Degree", certifications: '',
    skills_summary: '', projects: [], achievements: [],
    require_visa: 'No', us_citizenship: 'Not Applicable', willing_to_relocate: 'Yes',
    gender: 'Decline to self-identify', ethnicity: 'Decline to self-identify',
    disability_status: "I don't wish to answer", veteran_status: 'I am not a protected veteran',
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

  // Search config
  const [searchConfig, setSearchConfig] = useState({
    target_roles: [], domain_keywords: [], resume_skills: {},
    active_regions: [], available_regions: [],
    default_location: '', max_jobs: 25, mode: 'semi',
  })
  const [searchSaving, setSearchSaving] = useState(false)
  const [newRole, setNewRole] = useState('')
  const [newKeyword, setNewKeyword] = useState('')
  const [newSkill, setNewSkill] = useState('')
  const [newSkillWeight, setNewSkillWeight] = useState(3)

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

      // Load search config
      try {
        const sc = await api.getSearchConfig()
        if (sc) setSearchConfig(prev => ({ ...prev, ...sc }))
      } catch {}

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
      const payload = {
        ...profile,
        experience_years: parseInt(profile.experience_years, 10) || 0,
        notice_period_days: parseInt(profile.notice_period_days, 10) || 0,
        current_salary: parseInt(profile.current_salary, 10) || 0,
        desired_salary: parseInt(profile.desired_salary, 10) || 0,
      }
      await api.saveProfile(payload)
      toast({ title: 'Profile saved', description: 'Your profile information has been updated.', type: 'success' })
    } catch (e) {
      toast({ title: 'Save failed', description: e.message, type: 'error' })
    } finally {
      setProfileSaving(false)
    }
  }

  async function saveSMTP() {
    // Validate
    if (!smtp.smtp_host?.trim()) {
      toast({ title: 'Missing SMTP host', type: 'error' })
      return
    }
    if (!smtp.smtp_port || smtp.smtp_port < 1 || smtp.smtp_port > 65535) {
      toast({ title: 'Invalid port number', type: 'error' })
      return
    }
    if (smtp.from_email && !smtp.from_email.includes('@')) {
      toast({ title: 'Invalid from email', type: 'error' })
      return
    }
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


  async function saveSearchConfig() {
    setSearchSaving(true)
    try {
      await api.saveSearchConfig({
        target_roles: searchConfig.target_roles,
        domain_keywords: searchConfig.domain_keywords,
        resume_skills: searchConfig.resume_skills,
        active_regions: searchConfig.active_regions,
        default_location: searchConfig.default_location,
        max_jobs: parseInt(searchConfig.max_jobs, 10) || 25,
        mode: searchConfig.mode,
      })
      toast({ title: 'Search config saved', description: 'Your search preferences have been updated.', type: 'success' })
    } catch (e) {
      toast({ title: 'Save failed', description: e.message, type: 'error' })
    } finally {
      setSearchSaving(false)
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


  const initials = profile.name?.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase() || '?'

  const SETTINGS_TABS = [
    { key: 'profile', label: 'Profile', icon: User },
    { key: 'integrations', label: 'Integrations', icon: Plug },
    { key: 'search', label: 'Search Config', icon: SlidersHorizontal },
    { key: 'advanced', label: 'Advanced', icon: Wrench },
  ]

  const [activeTab, setActiveTab] = useState('profile')

  return (
    <div className="min-h-screen bg-bg-primary text-fg-primary px-6 py-8 font-sans">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-fg-primary">Settings</h1>
        <p className="text-fg-muted text-sm mt-1">Configure your profile, integrations, search preferences & more</p>
      </div>

      <div className="mb-6">
        <PageTabs tabs={SETTINGS_TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-3 py-32 text-fg-muted">
          <Loader2 size={22} className="animate-spin text-accent" />
          <span className="text-sm">Loading settings...</span>
        </div>
      ) : (
        <div className="max-w-5xl">

          {/* ── Tab 1: Profile ── */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
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
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-14 h-14 rounded-full bg-accent-bg border border-accent/30 flex items-center justify-center flex-shrink-0">
                    <span className="text-accent font-semibold text-lg font-mono">{initials}</span>
                  </div>
                  <div className="flex-1 grid grid-cols-2 gap-3">
                    <div>
                      <Label>Full Name</Label>
                      <Input {...pf('name')} placeholder="Your Name" />
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
                    <Input {...pf('phone')} placeholder="+1 000 000 0000" />
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
                  <div>
                    <Label>Experience (yrs)</Label>
                    <Input {...pf('experience_years')} placeholder="2" type="number" mono />
                  </div>
                  <div>
                    <Label>Notice (days)</Label>
                    <Input {...pf('notice_period_days')} placeholder="30" type="number" mono />
                  </div>
                  <div>
                    <Label>Current Employer</Label>
                    <Input {...pf('employer')} placeholder="Company Name" />
                  </div>
                  <div>
                    <Label>Employer Domain</Label>
                    <Input {...pf('employer_domain')} placeholder="company.com (blocked from outreach)" />
                  </div>
                  <div>
                    <Label>Website</Label>
                    <Input {...pf('website')} placeholder="https://yourwebsite.com" />
                  </div>
                  <div>
                    <Label>Current Salary</Label>
                    <Input {...pf('current_salary')} placeholder="0" type="number" mono />
                  </div>
                  <div>
                    <Label>Desired Salary</Label>
                    <Input {...pf('desired_salary')} placeholder="0" type="number" mono />
                  </div>
                </div>

                {/* ── Education & Credentials ── */}
                <div className="border-t border-border mt-5 mb-5" />
                <div className="grid grid-cols-2 gap-x-5 gap-y-4">
                  <div>
                    <Label>Education</Label>
                    <Input {...pf('education')} placeholder="B.S. Computer Science, University Name" />
                  </div>
                  <div>
                    <Label>Education Level</Label>
                    <select
                      value={profile.education_level || "Bachelor's Degree"}
                      onChange={e => setProfile(p => ({ ...p, education_level: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      <option>High School</option>
                      <option>Associate's Degree</option>
                      <option>Bachelor's Degree</option>
                      <option>Master's Degree</option>
                      <option>Doctorate (PhD)</option>
                      <option>Professional Degree (MD, JD)</option>
                    </select>
                  </div>
                  <div>
                    <Label>Certifications</Label>
                    <Input {...pf('certifications')} placeholder="AWS Solutions Architect, etc." />
                  </div>
                </div>

                {/* ── Visa & Relocation ── */}
                <div className="border-t border-border mt-5 mb-5" />
                <p className="text-[10px] text-fg-muted uppercase tracking-wider font-semibold mb-3">Visa & Relocation (used by auto-apply forms)</p>
                <div className="grid grid-cols-3 gap-x-5 gap-y-4">
                  <div>
                    <Label>Require Visa Sponsorship</Label>
                    <select value={profile.require_visa || 'No'} onChange={e => setProfile(p => ({ ...p, require_visa: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>No</option><option>Yes</option>
                    </select>
                  </div>
                  <div>
                    <Label>US Work Authorization</Label>
                    <select value={profile.us_citizenship || 'Not Applicable'} onChange={e => setProfile(p => ({ ...p, us_citizenship: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>US Citizen</option><option>Green Card</option><option>H-1B</option><option>OPT/CPT</option><option>Not Applicable</option>
                    </select>
                  </div>
                  <div>
                    <Label>Willing to Relocate</Label>
                    <select value={profile.willing_to_relocate || 'Yes'} onChange={e => setProfile(p => ({ ...p, willing_to_relocate: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>Yes</option><option>No</option><option>Depends on location</option>
                    </select>
                  </div>
                </div>

                {/* ── EEO / Diversity (auto-apply forms) ── */}
                <div className="border-t border-border mt-5 mb-5" />
                <p className="text-[10px] text-fg-muted uppercase tracking-wider font-semibold mb-3">EEO / Diversity (optional — used by auto-apply forms)</p>
                <div className="grid grid-cols-2 gap-x-5 gap-y-4">
                  <div>
                    <Label>Gender</Label>
                    <select value={profile.gender || 'Decline to self-identify'} onChange={e => setProfile(p => ({ ...p, gender: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>Male</option><option>Female</option><option>Non-binary</option><option>Decline to self-identify</option>
                    </select>
                  </div>
                  <div>
                    <Label>Ethnicity</Label>
                    <select value={profile.ethnicity || 'Decline to self-identify'} onChange={e => setProfile(p => ({ ...p, ethnicity: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>Asian</option><option>Black or African American</option><option>Hispanic or Latino</option><option>White</option><option>Two or More Races</option><option>Native American</option><option>Pacific Islander</option><option>Decline to self-identify</option>
                    </select>
                  </div>
                  <div>
                    <Label>Disability Status</Label>
                    <select value={profile.disability_status || "I don't wish to answer"} onChange={e => setProfile(p => ({ ...p, disability_status: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>Yes, I have a disability</option><option>No, I do not have a disability</option><option>I don't wish to answer</option>
                    </select>
                  </div>
                  <div>
                    <Label>Veteran Status</Label>
                    <select value={profile.veteran_status || 'I am not a protected veteran'} onChange={e => setProfile(p => ({ ...p, veteran_status: e.target.value }))}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                      <option>I am a protected veteran</option><option>I am not a protected veteran</option><option>Decline to self-identify</option>
                    </select>
                  </div>
                </div>

                {/* ── Skills, Projects, Achievements ── */}
                <div className="border-t border-border mt-5 mb-5" />
                <div className="space-y-4">
                  <div>
                    <Label>Skills Summary</Label>
                    <textarea
                      value={profile.skills_summary || ''}
                      onChange={e => setProfile(p => ({ ...p, skills_summary: e.target.value }))}
                      placeholder="Python, FastAPI, React, Docker, AWS — your core tech stack for email personalization"
                      rows={2}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                    />
                  </div>
                  <div>
                    <Label>Projects (used in cold email personalization)</Label>
                    {(profile.projects || []).map((proj, i) => (
                      <div key={i} className="flex gap-2 mb-2">
                        <input
                          value={proj.name || ''}
                          onChange={e => {
                            const updated = [...(profile.projects || [])];
                            updated[i] = { ...updated[i], name: e.target.value };
                            setProfile(p => ({ ...p, projects: updated }));
                          }}
                          placeholder="Project name"
                          className="w-1/3 px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
                        />
                        <input
                          value={proj.description || ''}
                          onChange={e => {
                            const updated = [...(profile.projects || [])];
                            updated[i] = { ...updated[i], description: e.target.value };
                            setProfile(p => ({ ...p, projects: updated }));
                          }}
                          placeholder="Brief description with metrics"
                          className="flex-1 px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
                        />
                        <button
                          onClick={() => {
                            const updated = (profile.projects || []).filter((_, j) => j !== i);
                            setProfile(p => ({ ...p, projects: updated }));
                          }}
                          className="px-2 py-1.5 text-fg-muted hover:text-danger transition-colors text-xs"
                        >×</button>
                      </div>
                    ))}
                    <button
                      onClick={() => setProfile(p => ({ ...p, projects: [...(p.projects || []), { name: '', description: '' }] }))}
                      className="text-xs text-accent hover:text-accent/80 transition-colors"
                    >+ Add project</button>
                  </div>
                  <div>
                    <Label>Achievements (one per line)</Label>
                    <textarea
                      value={(profile.achievements || []).join('\n')}
                      onChange={e => setProfile(p => ({ ...p, achievements: e.target.value.split('\n').filter(l => l.trim()) }))}
                      placeholder={"Published 2 papers at top conferences\nOpen source project with 500+ stars"}
                      rows={3}
                      className="w-full px-3 py-2 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent resize-none font-mono"
                    />
                  </div>
                </div>
              </Card>

              <ResumeStatusCard />
              <ResumeVariantsCard toast={toast} />
            </div>
          )}

          {/* ── Tab 2: Integrations ── */}
          {activeTab === 'integrations' && (
            <div className="space-y-6">
              {/* SMTP */}
              <Card
                title="Email Server (SMTP)"
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
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-bg-tertiary border border-border text-fg-secondary text-xs font-medium rounded-lg hover:text-fg-primary hover:border-accent/50 transition-colors disabled:opacity-40"
                    >
                      {testingConnection ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                      Test
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
                    <Input {...sf('from_name')} placeholder="Your Name" />
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

              <EmailConfigStatus />

              {/* Gemini API */}
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

              {/* LinkedIn Browser */}
              <BrowserStatusCard toast={toast} />
            </div>
          )}

          {/* ── Tab 3: Search Config ── */}
          {activeTab === 'search' && (
            <div className="space-y-6">
              <Card title="Search Configuration" icon={SlidersHorizontal}
                action={
                  <button onClick={saveSearchConfig} disabled={searchSaving}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-60">
                    {searchSaving ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                    {searchSaving ? 'Saving...' : 'Save'}
                  </button>
                }
              >
                <div className="space-y-5">
                  {/* Target Roles */}
                  <div>
                    <Label>Target Roles</Label>
                    <p className="text-fg-muted text-xs mb-2">Roles you're targeting — used for smart filtering & scoring</p>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {searchConfig.target_roles.map(r => (
                        <span key={r} className="inline-flex items-center gap-1 px-3 py-1.5 bg-accent-bg text-accent text-xs font-medium rounded-lg border border-accent/20">
                          {r}
                          <button onClick={() => setSearchConfig(s => ({ ...s, target_roles: s.target_roles.filter(x => x !== r) }))}
                            className="text-accent/50 hover:text-danger ml-0.5">×</button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input value={newRole} onChange={e => setNewRole(e.target.value)} placeholder="Add role..."
                        onKeyDown={e => { if (e.key === 'Enter' && newRole.trim()) { setSearchConfig(s => ({ ...s, target_roles: [...s.target_roles, newRole.trim()] })); setNewRole(''); } }}
                        className="flex-1 px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent" />
                      <button onClick={() => { if (newRole.trim()) { setSearchConfig(s => ({ ...s, target_roles: [...s.target_roles, newRole.trim()] })); setNewRole(''); } }}
                        className="px-3 py-1.5 text-xs text-accent hover:text-accent/80 border border-accent/20 rounded-lg">+ Add</button>
                    </div>
                  </div>

                  <div className="border-t border-border" />

                  {/* Domain Keywords */}
                  <div>
                    <Label>Domain Keywords</Label>
                    <p className="text-fg-muted text-xs mb-2">Keywords for domain relevance scoring (e.g. healthcare, fintech)</p>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {searchConfig.domain_keywords.map(k => (
                        <span key={k} className="inline-flex items-center gap-1 px-2 py-1 bg-bg-tertiary text-fg-secondary text-xs rounded-md border border-border">
                          {k}
                          <button onClick={() => setSearchConfig(s => ({ ...s, domain_keywords: s.domain_keywords.filter(x => x !== k) }))}
                            className="text-fg-muted hover:text-danger">×</button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input value={newKeyword} onChange={e => setNewKeyword(e.target.value)} placeholder="Add keyword..."
                        onKeyDown={e => { if (e.key === 'Enter' && newKeyword.trim()) { setSearchConfig(s => ({ ...s, domain_keywords: [...s.domain_keywords, newKeyword.trim().toLowerCase()] })); setNewKeyword(''); } }}
                        className="flex-1 px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent" />
                      <button onClick={() => { if (newKeyword.trim()) { setSearchConfig(s => ({ ...s, domain_keywords: [...s.domain_keywords, newKeyword.trim().toLowerCase()] })); setNewKeyword(''); } }}
                        className="px-3 py-1.5 text-xs text-accent hover:text-accent/80 border border-accent/20 rounded-lg">+ Add</button>
                    </div>
                  </div>

                  <div className="border-t border-border" />

                  {/* Resume Skills (skill weights for scoring) */}
                  <div>
                    <Label>Resume Skills & Weights</Label>
                    <p className="text-fg-muted text-xs mb-2">Your skills with priority weights (1–5) — used for job scoring & matching</p>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {Object.entries(searchConfig.resume_skills).map(([skill, weight]) => (
                        <span key={skill} className="inline-flex items-center gap-1 px-2 py-1 bg-bg-tertiary text-fg-secondary text-xs rounded-md border border-border">
                          {skill} <span className="text-accent font-mono">({weight})</span>
                          <button onClick={() => setSearchConfig(s => { const rs = { ...s.resume_skills }; delete rs[skill]; return { ...s, resume_skills: rs }; })}
                            className="text-fg-muted hover:text-danger">×</button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input value={newSkill} onChange={e => setNewSkill(e.target.value)} placeholder="Skill name..."
                        onKeyDown={e => { if (e.key === 'Enter' && newSkill.trim()) { setSearchConfig(s => ({ ...s, resume_skills: { ...s.resume_skills, [newSkill.trim().toLowerCase()]: parseInt(newSkillWeight) || 3 } })); setNewSkill(''); } }}
                        className="flex-1 px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary placeholder:text-fg-muted/50 focus:outline-none focus:ring-1 focus:ring-accent" />
                      <input value={newSkillWeight} onChange={e => setNewSkillWeight(e.target.value)} type="number" min="1" max="5" placeholder="Wt"
                        className="w-16 px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary text-center font-mono focus:outline-none focus:ring-1 focus:ring-accent" />
                      <button onClick={() => { if (newSkill.trim()) { setSearchConfig(s => ({ ...s, resume_skills: { ...s.resume_skills, [newSkill.trim().toLowerCase()]: parseInt(newSkillWeight) || 3 } })); setNewSkill(''); } }}
                        className="px-3 py-1.5 text-xs text-accent hover:text-accent/80 border border-accent/20 rounded-lg">+ Add</button>
                    </div>
                  </div>

                  <div className="border-t border-border" />

                  {/* Active Regions */}
                  <div>
                    <Label>Active Regions</Label>
                    <p className="text-fg-muted text-xs mb-2">Regions to include in job search queries</p>
                    <div className="flex flex-wrap gap-2">
                      {searchConfig.available_regions.map(r => {
                        const active = searchConfig.active_regions.includes(r);
                        return (
                          <button key={r} onClick={() => setSearchConfig(s => ({
                            ...s, active_regions: active ? s.active_regions.filter(x => x !== r) : [...s.active_regions, r]
                          }))}
                            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${active ? 'bg-accent-bg text-accent border-accent/30' : 'bg-bg-tertiary text-fg-muted border-border hover:text-fg-secondary'}`}>
                            {r.charAt(0).toUpperCase() + r.slice(1)}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="border-t border-border" />

                  {/* Search Defaults */}
                  <div className="grid grid-cols-3 gap-5">
                    <div>
                      <Label>Default Location</Label>
                      <input value={searchConfig.default_location} onChange={e => setSearchConfig(s => ({ ...s, default_location: e.target.value }))}
                        placeholder="India" className="w-full px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent" />
                    </div>
                    <div>
                      <Label>Max Jobs per Run</Label>
                      <input value={searchConfig.max_jobs} onChange={e => setSearchConfig(s => ({ ...s, max_jobs: e.target.value }))}
                        type="number" className="w-full px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary font-mono focus:outline-none focus:ring-1 focus:ring-accent" />
                    </div>
                    <div>
                      <Label>Apply Mode</Label>
                      <select value={searchConfig.mode} onChange={e => setSearchConfig(s => ({ ...s, mode: e.target.value }))}
                        className="w-full px-2.5 py-1.5 bg-bg-primary border border-border rounded-lg text-sm text-fg-primary focus:outline-none focus:ring-1 focus:ring-accent">
                        <option value="semi">Semi-auto (approve each)</option>
                        <option value="auto">Full auto (apply all)</option>
                      </select>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* ── Tab 4: Advanced ── */}
          {activeTab === 'advanced' && (
            <div className="space-y-6">
              <Card title="Data Export" icon={Download}>
                <div className="flex items-center gap-3">
                  <button
                    onClick={async () => {
                      try {
                        const data = await api.getApplications()
                        const apps = data?.applications || []
                        const csv = ['Status,Title,Company,Location,Platform,Date,URL']
                        apps.forEach(a => csv.push(`${a.status},"${a.job_title || ''}","${a.company || ''}","${a.location || ''}",${a.platform || ''},${a.applied_at || ''},"${a.job_url || ''}"`))
                        const blob = new Blob([csv.join('\n')], { type: 'text/csv' })
                        const url = URL.createObjectURL(blob)
                        const el = document.createElement('a')
                        el.href = url; el.download = 'applications.csv'; el.click()
                        URL.revokeObjectURL(url)
                        toast({ title: 'Exported', description: `${apps.length} applications exported to CSV`, type: 'success' })
                      } catch (e) {
                        toast({ title: 'Export failed', description: e.message, type: 'error' })
                      }
                    }}
                    className="flex items-center gap-1.5 px-4 py-2.5 bg-bg-tertiary border border-border text-fg-secondary text-sm font-medium rounded-lg hover:text-fg-primary hover:border-accent/50 transition-colors"
                  >
                    <Download size={14} />
                    Export Applications (CSV)
                  </button>
                </div>
              </Card>

              <Card title="About CareerKit" icon={Info}>
                <div className="space-y-2 text-sm">
                  <p className="text-fg-secondary">Full-stack job hunting automation platform</p>
                  <p className="text-fg-muted text-xs">100+ job sources &bull; AI-powered email generation &bull; Smart scoring &bull; Auto-apply</p>
                  <div className="flex gap-4 mt-3 text-xs text-fg-muted">
                    <span>Stack: React + FastAPI + SQLite</span>
                    <span>LLM: Gemini + Ollama</span>
                  </div>
                </div>
              </Card>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
