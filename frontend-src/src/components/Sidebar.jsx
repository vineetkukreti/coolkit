import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Search, Database, Scan, Mail, History, Settings,
  GitBranch, BarChart3, Sparkles, Building2, HeartPulse, Zap,
} from 'lucide-react'

const topNav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/search', icon: Search, label: 'Job Search' },
  { to: '/posts', icon: Database, label: 'LinkedIn Posts' },
  { to: '/scraper', icon: Scan, label: 'Scraper' },
  { to: '/auto-apply', icon: Zap, label: 'Auto-Apply' },
  { to: '/email', icon: Mail, label: 'Email Outreach' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
]

const companiesNav = [
  { to: '/leads', icon: HeartPulse, label: 'Healthcare' },
]

const bottomNav = [
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/history', icon: History, label: 'History' },
  { to: '/ai-tools', icon: Sparkles, label: 'AI Tools' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors ${
          isActive
            ? 'bg-accent-bg text-fg-primary font-medium'
            : 'text-fg-secondary hover:text-fg-primary hover:bg-bg-tertiary'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={20} className={isActive ? 'text-accent' : 'text-fg-muted'} />
          {label}
        </>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  return (
    <aside className="w-60 min-h-screen bg-bg-secondary border-r border-border flex flex-col px-4 py-6 shrink-0">
      <div className="flex items-center gap-2.5 mb-6 px-2">
        <div className="w-9 h-9 bg-accent rounded-lg flex items-center justify-center">
          <span className="text-fg-inverse font-bold text-sm">JA</span>
        </div>
        <span className="text-lg font-bold text-fg-primary">JobAutomate</span>
      </div>
      <div className="h-px bg-border mb-4" />
      <nav className="flex flex-col gap-0.5">
        {topNav.map(item => <NavItem key={item.to} {...item} />)}
      </nav>

      {/* Companies section */}
      <div className="mt-5 mb-1">
        <div className="flex items-center gap-2 px-3 mb-2">
          <Building2 size={13} className="text-fg-muted" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-fg-muted">Companies</span>
        </div>
        <nav className="flex flex-col gap-0.5">
          {companiesNav.map(item => <NavItem key={item.to} {...item} />)}
        </nav>
      </div>

      <div className="h-px bg-border my-3" />
      <nav className="flex flex-col gap-0.5">
        {bottomNav.map(item => <NavItem key={item.to} {...item} />)}
      </nav>
    </aside>
  )
}
