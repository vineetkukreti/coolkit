const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

const TOKEN_KEY = 'careerkit_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

async function request(path, options = {}) {
  const headers = { ...options.headers }
  if (options.body) {
    headers['Content-Type'] = 'application/json'
  }
  const token = tokenStore.get()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  })
  if (res.status === 401 && !path.startsWith('/auth/')) {
    // Token missing/expired — drop it and bounce to login.
    tokenStore.clear()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    throw new Error('Session expired — please log in again.')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || 'Request failed')
  }
  return res.json()
}

export const api = {
  // Auth
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/auth/me'),

  // Profile & stats
  getProfile: () => request('/profile'),
  getStats: () => request('/stats'),
  // Job search
  searchJobs: (data) => request('/search', { method: 'POST', body: JSON.stringify(data) }),

  // Browser control
  startBrowser: () => request('/browser/start', { method: 'POST' }),
  stopBrowser: () => request('/browser/stop', { method: 'POST' }),
  openLogin: () => request('/browser/login', { method: 'POST' }),
  checkLogin: () => request('/browser/check-login', { method: 'POST' }),
  getBrowserStatus: () => request('/browser/status'),

  // Manual apply/skip
  markApplied: (data) => request('/apply', { method: 'POST', body: JSON.stringify(data) }),
  markSkipped: (data) => request('/skip', { method: 'POST', body: JSON.stringify(data) }),

  // Applications history
  getApplications: () => request('/applications'),

  // DB posts
  getPosts: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/db/posts?${qs}`)
  },
  getDbStats: () => request('/db/stats'),
  getOutreachReady: () => request('/db/outreach-ready'),
  findEmailForPost: (postId) => request(`/db/posts/${postId}/find-email`, { method: 'POST' }),

  // Email
  verifyEmail: (email, company = '') => request('/email/verify', { method: 'POST', body: JSON.stringify({ email, company }) }),
  generateEmail: (data) => request('/email/generate', { method: 'POST', body: JSON.stringify(data) }),
  sendEmail: (data) => request('/email/send', { method: 'POST', body: JSON.stringify(data) }),
  bulkGenerate: (data) => request('/email/bulk-generate', { method: 'POST', body: JSON.stringify(data) }),
  bulkSend: (data = {}) => request('/email/bulk-send', { method: 'POST', body: JSON.stringify(data) }),
  getEmailWorkerStatus: () => request('/email/worker-status'),
  stopEmailWorker: (task) => request(`/email/worker-stop${task ? `?task=${task}` : ''}`, { method: 'POST' }),
  saveDraft: (data) => request('/email/save-draft', { method: 'POST', body: JSON.stringify(data) }),
  pasteExtract: (rawText) => request('/email/paste-extract', { method: 'POST', body: JSON.stringify({ raw_text: rawText }) }),
  getPasteHistory: () => request('/email/paste-history'),
  getSkillDemand: () => request('/email/skill-demand'),
  backfillSkills: () => request('/email/backfill-skills', { method: 'POST' }),
  getEmailHistory: () => request('/email/history'),
  getEmailConfig: () => request('/email/config-status'),

  // Address quality report
  getAddressQuality: () => request('/email/address-quality'),

  // Manual email status update
  updateEmailStatus: (outreachId, status) => request('/email/update-status', { method: 'POST', body: JSON.stringify({ outreach_id: outreachId, status }) }),

  // Scraper
  startScraper: (data) => request('/scraper/start', { method: 'POST', body: JSON.stringify(data) }),
  stopScraper: (source) => request(`/scraper/stop${source ? `?source=${source}` : ''}`, { method: 'POST' }),
  getScraperStatus: () => request('/scraper/status'),
  getScraperSources: () => request('/scraper/sources'),

  // ATS Scanner
  atsCompanies: () => request('/ats/companies'),
  atsScan: () => request('/ats/scan', { method: 'POST' }),

  // Settings
  getAllSettings: () => request('/settings/all'),
  saveProfile: (data) => request('/settings/profile', { method: 'POST', body: JSON.stringify(data) }),
  getSearchConfig: () => request('/settings/search-config'),
  saveSearchConfig: (data) => request('/settings/search-config', { method: 'POST', body: JSON.stringify(data) }),
  saveSMTP: (data) => request('/settings/smtp', { method: 'POST', body: JSON.stringify(data) }),
  saveGemini: (data) => request('/settings/gemini', { method: 'POST', body: JSON.stringify(data) }),
  testEmail: () => request('/settings/test-email', { method: 'POST' }),
  uploadResume: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch('/api/settings/upload-resume', { method: 'POST', body: form })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || 'Upload failed')
        }
        return res.json()
      })
  },
  getResumeStatus: () => request('/settings/resume-status'),

  // Pipeline
  getPipeline: () => request('/pipeline'),
  getPipelineStats: () => request('/pipeline/stats'),
  getPipelineLead: (id) => request(`/pipeline/lead/${id}`),
  updatePipelineStage: (data) => request('/pipeline/update-stage', { method: 'POST', body: JSON.stringify(data) }),
  addPipelineNote: (data) => request('/pipeline/add-note', { method: 'POST', body: JSON.stringify(data) }),
  syncPipeline: () => request('/pipeline/sync', { method: 'POST' }),

  // Follow-up
  getFollowupStatus: () => request('/followup/status'),
  recordFollowup: (outreachId) => request('/followup/record', { method: 'POST', body: JSON.stringify({ outreach_id: outreachId }) }),
  autoFollowup: () => request('/followup/auto-send', { method: 'POST' }),
  previewFollowup: (outreachId) => request(`/followup/preview/${outreachId}`, { method: 'POST' }),
  getFollowupWorkerStatus: () => request('/followup/worker-status'),
  stopFollowupWorker: () => request('/followup/worker-stop', { method: 'POST' }),

  // Email connections
  getEmailConnections: (postId) => request(`/email/connections/${postId}`),

  // Email Stats & Tracking
  getEmailStats: () => request('/email/stats'),
  classifyFailures: () => request('/email/classify-failures', { method: 'POST' }),

  // IMAP Reply Detection
  checkReplies: () => request('/email/check-replies', { method: 'POST' }),
  startImapPolling: () => request('/email/imap-start', { method: 'POST' }),
  stopImapPolling: () => request('/email/imap-stop', { method: 'POST' }),
  getImapStatus: () => request('/email/imap-status'),
  deepScanReplies: (since = '01-Mar-2026') => request(`/email/deep-scan?since=${encodeURIComponent(since)}`, { method: 'POST' }),
  reclassifyReplies: () => request('/email/reclassify', { method: 'POST' }),
  getReplyBreakdown: () => request('/email/reply-breakdown'),

  // Analytics – Outreach Insights
  getPatterns: () => request('/analytics/patterns'),
  getConversion: () => request('/analytics/conversion'),

  // Server Logs
  getLogs: (level = '', limit = 100, search = '') => request(`/logs?level=${level}&limit=${limit}&search=${encodeURIComponent(search)}`),
  getErrors: (limit = 50) => request(`/logs/errors?limit=${limit}`),
  getLogFile: (lines = 200) => request(`/logs/file?lines=${lines}`),

  // Startup Leads
  getLeads: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/leads?${qs}`)
  },
  getLeadsStats: () => request('/leads/stats'),
  getLeadsSources: () => request('/leads/sources'),
  getLead: (id) => request(`/leads/${id}`),
  updateLead: (id, data) => request(`/leads/${id}/update`, { method: 'POST', body: JSON.stringify(data) }),
  importLeads: () => request('/leads/import', { method: 'POST' }),

  // AI Tools
  getClipboard: () => request('/clipboard'),
  evaluateJob: (jdText) => request('/tools/evaluate', { method: 'POST', body: JSON.stringify({ jd_text: jdText }) }),
  generateOutreach: (data) => request('/tools/outreach', { method: 'POST', body: JSON.stringify(data) }),
  deepDive: (data) => request('/tools/deep-dive', { method: 'POST', body: JSON.stringify(data) }),
  tailorCv: (jdText) => request('/tools/tailor-cv', { method: 'POST', body: JSON.stringify({ jd_text: jdText }) }),
  interviewPrep: (data) => request('/tools/interview-prep', { method: 'POST', body: JSON.stringify(data) }),

  // Auto-Apply
  startAutoApply: (data) => request('/auto-apply/start', { method: 'POST', body: JSON.stringify(data) }),
  stopAutoApply: () => request('/auto-apply/stop', { method: 'POST' }),
  getAutoApplyStatus: () => request('/auto-apply/status'),
  getAutoApplyQuota: () => request('/auto-apply/quota'),

  // Quality Dashboard & Smart Filter
  getQualityDashboard: () => request('/dashboard/quality'),
  getSmartFilterStats: () => request('/smart-filter/stats'),
  getSmartFilterTop: () => request('/smart-filter/top'),
  scoreAllJobs: () => request('/smart-filter/score-all', { method: 'POST' }),
  getSendTimeStats: () => request('/email/send-time-stats'),
  getAbStats: () => request('/email/ab-stats'),
  scanCompany: (company) => request('/company/scan', { method: 'POST', body: JSON.stringify({ company }) }),
  getConnections: (company) => request('/company/connections', { method: 'POST', body: JSON.stringify({ company }) }),
  getResumeVariants: () => request('/resumes/variants'),
  uploadVariantResume: (variantName, file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`/api/resumes/variants/${variantName}/upload`, { method: 'POST', body: form })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || 'Upload failed')
        }
        return res.json()
      })
  },
  testResumeSelection: (data) => request('/resumes/test-selection', { method: 'POST', body: JSON.stringify(data) }),

  // Lead Enrichment
  startEnrichment: (data = {}) => request('/leads/enrich/start', { method: 'POST', body: JSON.stringify(data) }),
  getEnrichmentStatus: () => request('/leads/enrich/status'),
  stopEnrichment: (target) => request(`/leads/enrich/stop${target ? `?target=${target}` : ''}`, { method: 'POST' }),
  enrichSingleLead: (id) => request(`/leads/enrich/single/${id}`, { method: 'POST' }),

  // Bounce Detection
  checkBounces: () => request('/email/check-bounces', { method: 'POST' }),

  // Smart Filter – Individual Scoring
  smartFilterScore: (data) => request('/smart-filter/score', { method: 'POST', body: JSON.stringify(data) }),

  // Liveness Check
  livenessCheck: (data) => request('/liveness/check', { method: 'POST', body: JSON.stringify(data) }),
  livenessScan: () => request('/liveness/scan', { method: 'POST' }),

  // Resume Selection
  selectResume: (data) => request('/resumes/select', { method: 'POST', body: JSON.stringify(data) }),

  // Orchestrator – Daily Cycle
  startDailyCycle: (data = {}) => request('/orchestrator/start', { method: 'POST', body: JSON.stringify(data) }),
  stopDailyCycle: () => request('/orchestrator/stop', { method: 'POST' }),
  getOrchestratorStatus: () => request('/orchestrator/status'),

  // Application Export
  exportApplications: () => fetch('/api/applications/export').then(res => {
    if (!res.ok) throw new Error('Export failed')
    return res.blob()
  }),

  // Ghost Job Detection
  getGhostStats: () => request('/ghost/stats'),
  scanGhostJobs: (limit = 100) => request(`/ghost/scan?limit=${limit}`, { method: 'POST' }),
  checkGhostScore: (postId) => request(`/ghost/check/${postId}`),

  // ATS Resume Scoring
  getAtsScore: (jdText) => request('/ats/score', { method: 'POST', body: JSON.stringify({ jd_text: jdText }) }),
  getAtsScoreForPost: (postId) => request(`/ats/score/${postId}`),
  extractJdKeywords: (jdText) => request('/ats/extract-keywords', { method: 'POST', body: JSON.stringify({ jd_text: jdText }) }),

  // Quality Gate
  qualityGateCheck: (data) => request('/quality-gate/check', { method: 'POST', body: JSON.stringify(data) }),
  qualityGateBatch: (limit = 50) => request(`/quality-gate/batch?limit=${limit}`),
  qualityGateTiers: () => request('/quality-gate/tiers'),

  // Skills Intelligence
  getSkillsDashboard: () => request('/skills/dashboard'),
  analyzeSkills: (data = {}) => request('/skills/analyze', { method: 'POST', body: JSON.stringify(data) }),
  getAnalysisStatus: () => request('/skills/analysis-status'),
  getSkillsGaps: () => request('/skills/gaps'),
  getSkillsTrends: () => request('/skills/trends'),
  refreshSkillsTrends: () => request('/skills/trends/refresh', { method: 'POST' }),
  getSkillsNews: () => request('/skills/news'),
  refreshSkillsNews: () => request('/skills/news/refresh', { method: 'POST' }),

  // Inbox Tracker
  scanInbox: (since) => request(`/inbox/scan${since ? '?since=' + encodeURIComponent(since) : ''}`, { method: 'POST' }),
  classifyEmail: (subject, body, from) => request('/inbox/classify', { method: 'POST', body: JSON.stringify({ subject, body, from }) }),

  // Funnel Analytics
  getPipelineFunnel: () => request('/pipeline/funnel'),
}
