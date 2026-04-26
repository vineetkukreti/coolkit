import { useSearchParams } from 'react-router-dom'

export function useTabState(defaultTab) {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || defaultTab
  const setTab = (key) => setParams({ tab: key }, { replace: true })
  return [tab, setTab]
}

export default function PageTabs({ tabs, activeTab, onTabChange }) {
  return (
    <div className="flex items-center gap-1 border-b border-border">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === tab.key
              ? 'border-accent text-accent'
              : 'border-transparent text-fg-muted hover:text-fg-primary'
          }`}
        >
          {tab.icon && <tab.icon size={14} />}
          {tab.label}
        </button>
      ))}
    </div>
  )
}
