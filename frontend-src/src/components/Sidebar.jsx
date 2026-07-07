import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Search, Zap, Mail, GitBranch, BarChart3, Sparkles, Settings, Brain, Terminal, LogOut,
} from 'lucide-react'
import { useAuth } from '../lib/auth'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/find', icon: Search, label: 'Find Jobs' },
  { to: '/apply', icon: Zap, label: 'Apply' },
  { to: '/outreach', icon: Mail, label: 'Outreach' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
  { to: '/insights', icon: BarChart3, label: 'Insights' },
  { to: '/skills', icon: Brain, label: 'Skills Intel' },
  { to: '/ai-tools', icon: Sparkles, label: 'AI Tools' },
  { to: '/logs', icon: Terminal, label: 'Logs' },
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
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-60 min-h-screen bg-bg-secondary border-r border-border flex flex-col px-4 py-6 shrink-0">
      <div className="flex items-center gap-2.5 mb-6 px-2">
        <div className="w-9 h-9 bg-accent rounded-lg flex items-center justify-center">
          <span className="text-fg-inverse font-bold text-sm">CK</span>
        </div>
        <span className="text-lg font-bold text-fg-primary">CareerKit</span>
      </div>
      <div className="h-px bg-border mb-4" />
      <nav className="flex flex-col gap-0.5 flex-1">
        {navItems.map(item => <NavItem key={item.to} {...item} />)}
      </nav>
      <div className="h-px bg-border my-3" />
      <NavItem to="/settings" icon={Settings} label="Settings" />
      {user && (
        <div className="mt-2 px-3 pt-2">
          <p className="text-xs text-fg-muted truncate mb-2" title={user.email}>{user.email}</p>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2.5 w-full px-0 py-1 rounded-lg text-sm text-fg-secondary
              hover:text-danger transition-colors"
          >
            <LogOut size={18} className="text-fg-muted" />
            Log out
          </button>
        </div>
      )}
    </aside>
  )
}
