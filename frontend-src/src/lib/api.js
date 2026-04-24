const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
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
  generateEmail: (data) => request('/email/generate', { method: 'POST', body: JSON.stringify(data) }),
  sendEmail: (data) => request('/email/send', { method: 'POST', body: JSON.stringify(data) }),
  bulkGenerate: (data) => request('/email/bulk-generate', { method: 'POST', body: JSON.stringify(data) }),
  bulkSend: (data = {}) => request('/email/bulk-send', { method: 'POST', body: JSON.stringify(data) }),
  getEmailWorkerStatus: () => request('/email/worker-status'),
  stopEmailWorker: () => request('/email/worker-stop', { method: 'POST' }),
  saveDraft: (data) => request('/email/save-draft', { method: 'POST', body: JSON.stringify(data) }),
  getEmailHistory: () => request('/email/history'),
  getEmailConfig: () => request('/email/config-status'),

  // Scraper
  startScraper: (data) => request('/scraper/start', { method: 'POST', body: JSON.stringify(data) }),
  stopScraper: () => request('/scraper/stop', { method: 'POST' }),
  getScraperStatus: () => request('/scraper/status'),
  getScraperSources: () => request('/scraper/sources'),

  // ATS Scanner
  atsCompanies: () => request('/ats/companies'),
  atsScan: () => request('/ats/scan', { method: 'POST' }),

  // Settings
  getAllSettings: () => request('/settings/all'),
  saveProfile: (data) => request('/settings/profile', { method: 'POST', body: JSON.stringify(data) }),
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

  // Analytics – Outreach Insights
  getPatterns: () => request('/analytics/patterns'),
  getConversion: () => request('/analytics/conversion'),

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
}
