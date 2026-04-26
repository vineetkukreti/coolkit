import { Search, Scan, Database } from 'lucide-react'
import PageTabs, { useTabState } from '../components/PageTabs'
import JobSearch from './JobSearch'
import Scraper from './Scraper'
import Posts from './Posts'

const TABS = [
  { key: 'search', label: 'Search', icon: Search },
  { key: 'scraper', label: 'Scraper', icon: Scan },
  { key: 'posts', label: 'Browse Posts', icon: Database },
]

export default function FindJobs() {
  const [tab, setTab] = useTabState('search')

  return (
    <div className="flex flex-col h-full">
      <div className="px-10 pt-8 pb-0">
        <h1 className="text-2xl font-semibold text-fg-primary">Find Jobs</h1>
        <p className="text-sm text-fg-muted mt-1">Search, scrape & browse job posts from 100+ sources</p>
        <div className="mt-4">
          <PageTabs tabs={TABS} activeTab={tab} onTabChange={setTab} />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === 'search' && <JobSearch />}
        {tab === 'scraper' && <Scraper />}
        {tab === 'posts' && <Posts />}
      </div>
    </div>
  )
}
