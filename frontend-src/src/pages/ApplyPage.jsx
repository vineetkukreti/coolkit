import { Zap, History } from 'lucide-react'
import PageTabs, { useTabState } from '../components/PageTabs'
import AutoApply from './AutoApply'
import AppHistory from './AppHistory'

const TABS = [
  { key: 'engine', label: 'Auto-Apply Engine', icon: Zap },
  { key: 'history', label: 'Application History', icon: History },
]

export default function ApplyPage() {
  const [tab, setTab] = useTabState('engine')

  return (
    <div className="flex flex-col h-full">
      <div className="px-10 pt-8 pb-0">
        <h1 className="text-2xl font-semibold text-fg-primary">Apply</h1>
        <p className="text-sm text-fg-muted mt-1">Automated applications & tracking</p>
        <div className="mt-4">
          <PageTabs tabs={TABS} activeTab={tab} onTabChange={setTab} />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === 'engine' && <AutoApply />}
        {tab === 'history' && <AppHistory />}
      </div>
    </div>
  )
}
