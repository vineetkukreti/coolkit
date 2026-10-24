// coolkit Copilot popup — save jobs (Teal/Huntr-style) and autofill ATS forms (Simplify-style).

const $ = (id) => document.getElementById(id)
const msg = (text, color = '') => { $('msg').textContent = text; $('msg').style.color = color }

let cfg = { api: 'http://localhost:8000', token: '' }
let page = { url: '', text: '' }

async function call(path, options = {}) {
  const res = await fetch(cfg.api + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${cfg.token}`, ...(options.headers || {}) },
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 401) { await logout(); throw new Error('Session expired, sign in again') }
  if (!res.ok) throw new Error(data.message || data.detail || `HTTP ${res.status}`)
  return data
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab
}

async function runInPage(func, args = []) {
  const tab = await activeTab()
  const [{ result }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func, args })
  return result
}

// ── Runs inside the job page: pull structured data (JSON-LD JobPosting first, then heuristics)
function extractJob() {
  const out = { url: location.href, title: '', company: '', location: '', text: '' }
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const items = [].concat(JSON.parse(s.textContent))
      const flat = items.flatMap((i) => i['@graph'] || [i])
      const job = flat.find((i) => i['@type'] === 'JobPosting')
      if (job) {
        out.title = job.title || ''
        out.company = job.hiringOrganization?.name || ''
        const addr = [].concat(job.jobLocation || [])[0]?.address
        out.location = addr ? [addr.addressLocality, addr.addressRegion, addr.addressCountry].filter(Boolean).join(', ') : ''
        out.text = (job.description || '').replace(/<[^>]+>/g, ' ')
        break
      }
    } catch (e) { /* malformed JSON-LD */ }
  }
  const q = (sel) => document.querySelector(sel)?.textContent?.trim() || ''
  out.title ||= q('.job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1') || document.title
  out.company ||= q('.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, .comp-name, [data-company]')
    || document.querySelector('meta[property="og:site_name"]')?.content || ''
  out.text ||= (q('#job-details, .jobs-description, .job-description, [class*="description"]') || document.body.innerText).slice(0, 15000)
  return out
}

// ── Runs inside the application form: fill fields that match profile keys
function fillForm(profile) {
  const RULES = [
    [/first.?name|given.?name|fname/i, 'first_name'],
    [/last.?name|family.?name|surname|lname/i, 'last_name'],
    [/full.?name|^name$|your.?name|candidate.?name/i, 'name'],
    [/e-?mail/i, 'email'],
    [/phone|mobile|tel/i, 'phone'],
    [/linkedin/i, 'linkedin'],
    [/github/i, 'github'],
    [/website|portfolio|personal.?site|url/i, 'website'],
    [/city|location|address/i, 'location'],
    [/current.?(title|role|designation)|job.?title/i, 'current_title'],
    [/current.?(company|employer)|employer|organi[sz]ation/i, 'employer'],
    [/years.*experience|experience.*years|total.?experience/i, 'experience_years'],
    [/notice/i, 'notice_period_days'],
    [/current.?(ctc|salary|compensation)/i, 'current_salary'],
    [/expected|desired.?(ctc|salary|compensation)|salary.?expectation/i, 'desired_salary'],
    [/sponsor|visa/i, 'require_visa'],
    [/relocat/i, 'willing_to_relocate'],
    [/school|university|college|degree|education/i, 'education'],
    [/gender/i, 'gender'],
    [/ethnic|race/i, 'ethnicity'],
    [/disabilit/i, 'disability_status'],
    [/veteran/i, 'veteran_status'],
  ]
  const labelFor = (el) => {
    const parts = [el.name, el.id, el.placeholder, el.getAttribute('aria-label'), el.getAttribute('autocomplete')]
    if (el.id) parts.push(document.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.textContent)
    parts.push(el.closest('label')?.textContent, el.closest('[class*="field"], [class*="question"]')?.querySelector('label, legend')?.textContent)
    return parts.filter(Boolean).join(' ')
  }
  const setValue = (el, value) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value) // bypass React's value tracker
    el.dispatchEvent(new Event('input', { bubbles: true }))
    el.dispatchEvent(new Event('change', { bubbles: true }))
  }
  let filled = 0
  for (const el of document.querySelectorAll('input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]), textarea, select')) {
    if (el.disabled || el.readOnly || (el.value && el.tagName !== 'SELECT')) continue
    const label = labelFor(el)
    const rule = RULES.find(([re]) => re.test(label))
    const value = rule && profile[rule[1]]
    if (value === undefined || value === null || value === '') continue
    if (el.tagName === 'SELECT') {
      const want = String(value).toLowerCase()
      const opt = [...el.options].find((o) => o.value && (o.text.toLowerCase().includes(want) || want.includes(o.text.toLowerCase().trim())))
      if (!opt) continue
      setValue(el, opt.value)
    } else {
      setValue(el, String(value))
    }
    el.style.outline = '2px solid #A855F7'
    filled++
  }
  return filled
}

// ── Runs inside the application form: find unanswered custom questions, apply answers, or snapshot answers.
// Self-contained because chrome.scripting serializes only this function body.
function formAgent(mode, payload) {
  const clean = (t) => (t || '').replace(/\s+/g, ' ').replace(/\*/g, '').trim()
  const containerOf = (el) => el.closest('fieldset, [role="group"], [role="radiogroup"], [class*="field"], [class*="question"], li, .form-group') || el.parentElement
  const textLabel = (el) => {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`)
      if (l) return clean(l.textContent)
    }
    const byAria = el.getAttribute('aria-labelledby')
    if (byAria) return clean(byAria.split(' ').map((id) => document.getElementById(id)?.textContent).join(' '))
    return clean(el.getAttribute('aria-label') || el.closest('label')?.textContent
      || containerOf(el)?.querySelector('label, legend, [class*="label"]')?.textContent || el.placeholder || el.name)
  }
  const groupLabel = (el) => clean(containerOf(el)?.querySelector('legend, [class*="label"], label:not(:has(input))')?.textContent) || clean(el.name)
  const optionLabel = (el) => clean((el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.textContent) || el.closest('label')?.textContent || el.value)
  const setValue = (el, value) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value)
    el.dispatchEvent(new Event('input', { bubbles: true }))
    el.dispatchEvent(new Event('change', { bubbles: true }))
  }
  const visible = (el) => el.offsetParent !== null || el.getClientRects().length > 0
  const SKIP = 'input[type=hidden], input[type=file], input[type=password], input[type=submit], input[type=button], input[type=search]'

  // Build the question list: one entry per text field / select / radio group / checkbox group.
  const fields = []
  const groups = {}
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (el.matches(SKIP) || el.disabled || !visible(el)) continue
    if (el.type === 'radio' || el.type === 'checkbox') {
      const key = el.name || containerOf(el)?.textContent?.slice(0, 80)
      if (!groups[key]) fields.push(groups[key] = { type: el.type, els: [], question: groupLabel(el) })
      groups[key].els.push(el)
    } else {
      fields.push({ type: el.tagName === 'SELECT' ? 'select' : 'text', els: [el], question: textLabel(el) })
    }
  }
  // Pin ids to DOM nodes so they survive re-renders between 'collect' and 'apply'.
  fields.forEach((f, i) => {
    if (mode === 'collect') f.els[0].dataset.ckId = `ck${i}`
    f.id = f.els[0].dataset.ckId || ''
  })

  const answered = (f) => {
    if (f.type === 'radio' || f.type === 'checkbox') return f.els.some((e) => e.checked)
    const el = f.els[0]
    return el.tagName === 'SELECT' ? !!el.value && el.selectedIndex > 0 : !!el.value.trim()
  }
  const options = (f) => f.type === 'select'
    ? [...f.els[0].options].filter((o) => o.value).map((o) => clean(o.text))
    : f.type === 'text' ? [] : f.els.map(optionLabel)
  const valueOf = (f) => {
    if (f.type === 'select') return clean(f.els[0].selectedOptions[0]?.text)
    if (f.type === 'text') return f.els[0].value.trim()
    return f.els.filter((e) => e.checked).map(optionLabel).join(' | ')
  }

  if (mode === 'collect') {
    return fields.filter((f) => !answered(f) && f.question.length > 2)
      .map((f) => ({ id: f.id, question: f.question.slice(0, 300), type: f.type, options: options(f).slice(0, 50) }))
  }

  if (mode === 'snapshot') {
    return fields.filter((f) => answered(f) && f.question.length > 2)
      .map((f) => ({ question: f.question.slice(0, 300), answer: valueOf(f) }))
  }

  if (mode === 'apply') {
    let n = 0
    const byId = Object.fromEntries(fields.map((f) => [f.id, f]))
    for (const a of payload) {
      const f = byId[a.id]
      if (!f || answered(f)) continue
      const color = a.confidence === 'low' ? '#f59e0b' : a.source === 'llm' ? '#A855F7' : '#22c55e'
      if (f.type === 'select') {
        const opt = [...f.els[0].options].find((o) => clean(o.text) === a.answer)
        if (!opt) continue
        setValue(f.els[0], opt.value)
      } else if (f.type === 'text') {
        setValue(f.els[0], a.answer)
      } else {
        const picks = a.answer.split(' | ')
        f.els.filter((e) => picks.includes(optionLabel(e))).forEach((e) => { if (!e.checked) e.click() })
      }
      f.els.forEach((e) => { (f.type === 'text' || f.type === 'select' ? e : e.parentElement).style.outline = `2px solid ${color}` })
      n++
    }
    return n
  }
}

async function loadPage() {
  try {
    page = await runInPage(extractJob)
    $('title').value = page.title.slice(0, 200)
    $('company').value = page.company.slice(0, 120)
    $('location').value = page.location.slice(0, 120)
  } catch (e) {
    msg('Cannot read this page (browser-internal pages are blocked)', 'var(--warn)')
  }
}

function renderAts(ats) {
  if (!ats) return ''
  const s = ats.ats_score ?? 0
  const color = s >= 75 ? 'var(--ok)' : s >= 50 ? 'var(--warn)' : 'var(--bad)'
  const chips = (arr) => (arr || []).slice(0, 12).map((k) => `<span>${String(k).replace(/</g, '&lt;')}</span>`).join('')
  return `<div class="score" style="color:${color}">${s}<span class="muted">/100 ATS match</span></div>
    ${ats.matched?.length ? `<div class="muted">Matched</div><div class="chips">${chips(ats.matched)}</div>` : ''}
    ${ats.missing?.length ? `<div class="muted">Missing</div><div class="chips">${chips(ats.missing)}</div>` : ''}`
}

async function save() {
  msg('Saving…')
  try {
    const data = await call('/api/extension/save-job', {
      method: 'POST',
      body: JSON.stringify({ url: page.url, title: $('title').value, company: $('company').value,
        location: $('location').value, page_text: page.text, status: $('status').value }),
    })
    msg(data.message, 'var(--ok)')
    $('result').innerHTML = renderAts(data.ats)
    $('result').classList.toggle('hidden', !data.ats)
  } catch (e) { msg(e.message, 'var(--bad)') }
}

async function autofill() {
  msg('Filling profile fields…')
  try {
    const { profile } = await call('/api/extension/autofill-profile')
    const basic = await runInPage(fillForm, [profile])
    const questions = await runInPage(formAgent, ['collect', null])
    let custom = 0, fromBank = 0
    if (questions.length) {
      msg(`Answering ${questions.length} custom question(s)…`)
      const res = await call('/api/extension/answer-questions', {
        method: 'POST',
        body: JSON.stringify({ questions, company: $('company').value, role: $('title').value, jd_text: page.text }),
      })
      custom = await runInPage(formAgent, ['apply', res.answers])
      fromBank = res.from_bank
    }
    const total = basic + custom
    msg(total
      ? `Filled ${basic} profile + ${custom} custom (${fromBank} from your bank). Green = your answer, purple = AI, amber = check it. Review, then Remember.`
      : 'No fillable fields found on this page', total ? 'var(--ok)' : 'var(--warn)')
  } catch (e) { msg(e.message, 'var(--bad)') }
}

async function rememberAnswers() {
  try {
    const answers = await runInPage(formAgent, ['snapshot', null])
    const res = await call('/api/extension/remember-answers', {
      method: 'POST', body: JSON.stringify({ answers, company: $('company').value }),
    })
    msg(res.message + ' — they will be reused on future forms', 'var(--ok)')
  } catch (e) { msg(e.message, 'var(--bad)') }
}

async function login() {
  cfg.api = ($('api').value || 'http://localhost:8000').replace(/\/$/, '')
  msg('Signing in…')
  try {
    const res = await fetch(cfg.api + '/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: $('email').value, password: $('password').value }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.message || 'Login failed')
    cfg.token = data.token
    await chrome.storage.local.set(cfg)
    msg('')
    show()
  } catch (e) { msg(e.message, 'var(--bad)') }
}

async function logout() {
  cfg.token = ''
  await chrome.storage.local.set(cfg)
  show()
}

function show() {
  $('login').classList.toggle('hidden', !!cfg.token)
  $('main').classList.toggle('hidden', !cfg.token)
  $('api').value = cfg.api
  if (cfg.token) loadPage()
}

$('loginBtn').onclick = login
$('saveBtn').onclick = save
$('fillBtn').onclick = autofill
$('rememberBtn').onclick = rememberAnswers
$('logout').onclick = (e) => { e.preventDefault(); logout() }

chrome.storage.local.get(['api', 'token']).then((stored) => { cfg = { ...cfg, ...stored }; show() })
