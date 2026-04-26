import { Mail, HeartPulse } from 'lucide-react'
import PageTabs, { useTabState } from '../components/PageTabs'
import EmailOutreach from './EmailOutreach'
import StartupLeads from './StartupLeads'

const TABS = [
  { key: 'email', label: 'Email Campaigns', icon: Mail },
  { key: 'leads', label: 'Startup Leads', icon: HeartPulse },
]

export default function OutreachPage() {
  const [tab, setTab] = useTabState('email')

  return (
    <div className="flex flex-col h-full">
      <div className="px-10 pt-8 pb-0">
        <h1 className="text-2xl font-semibold text-fg-primary">Outreach</h1>
        <p className="text-sm text-fg-muted mt-1">Email campaigns & startup lead management</p>
        <div className="mt-4">
          <PageTabs tabs={TABS} activeTab={tab} onTabChange={setTab} />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === 'email' && <EmailOutreach />}
        {tab === 'leads' && <StartupLeads />}
      </div>
    </div>
  )
}
