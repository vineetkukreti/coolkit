import { BarChart3, Target } from 'lucide-react'
import PageTabs, { useTabState } from '../components/PageTabs'
import EmailAnalytics from './EmailAnalytics'
import QualityDashboard from './QualityDashboard'

const TABS = [
  { key: 'analytics', label: 'Email Analytics', icon: BarChart3 },
  { key: 'quality', label: 'Quality Scoring', icon: Target },
]

export default function InsightsPage() {
  const [tab, setTab] = useTabState('analytics')

  return (
    <div className="flex flex-col h-full">
      <div className="px-10 pt-8 pb-0">
        <h1 className="text-2xl font-semibold text-fg-primary">Insights</h1>
        <p className="text-sm text-fg-muted mt-1">Email performance analytics & job quality scoring</p>
        <div className="mt-4">
          <PageTabs tabs={TABS} activeTab={tab} onTabChange={setTab} />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === 'analytics' && <EmailAnalytics />}
        {tab === 'quality' && <QualityDashboard />}
      </div>
    </div>
  )
}
