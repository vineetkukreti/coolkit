import { useState, useCallback, useMemo } from 'react'
import { ChevronDown, RotateCcw } from 'lucide-react'

/**
 * useFilters hook — manages filter state for a page.
 *
 * @param {Array} filterDefs - Array of filter definitions
 *   Each: { key: string, type: 'select'|'toggle'|'dateRange', defaultValue?: any }
 * @returns {{ values, setFilter, clearFilters, isFiltered }}
 */
export function useFilters(filterDefs) {
  const defaults = useMemo(() => {
    const d = {}
    for (const f of filterDefs) {
      if (f.type === 'toggle') d[f.key] = f.defaultValue ?? false
      else if (f.type === 'dateRange') d[f.key] = f.defaultValue ?? ''
      else d[f.key] = f.defaultValue ?? ''
    }
    return d
  }, [filterDefs])

  const [values, setValues] = useState(defaults)

  const setFilter = useCallback((key, value) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }, [])

  const clearFilters = useCallback(() => {
    setValues(defaults)
  }, [defaults])

  const isFiltered = useMemo(() => {
    return Object.keys(defaults).some(k => values[k] !== defaults[k])
  }, [values, defaults])

  return { values, setFilter, clearFilters, isFiltered }
}

/**
 * Helper: filter an array of items using filter values.
 * Each filter def needs a `match` function: (item, value) => boolean
 *
 * @param {Array} items
 * @param {Object} filterValues - { key: value }
 * @param {Array} filterDefs - with `match(item, value)` on each
 * @returns filtered items
 */
export function applyFilters(items, filterValues, filterDefs) {
  if (!items) return []
  return items.filter(item => {
    for (const f of filterDefs) {
      const val = filterValues[f.key]
      // Skip default/empty values
      if (f.type === 'toggle' && !val) continue
      if (f.type !== 'toggle' && (val === '' || val === undefined || val === null)) continue
      // Apply match function
      if (f.match && !f.match(item, val)) return false
    }
    return true
  })
}

/**
 * Helper: dateRange filter match function.
 * Use: match: dateRangeMatch('created_at')
 */
export function dateRangeMatch(dateField) {
  return (item, days) => {
    if (!days) return true
    const d = parseInt(days)
    if (isNaN(d)) return true
    const val = item[dateField]
    if (!val) return false
    const cutoff = Date.now() - d * 86400000
    return new Date(val).getTime() >= cutoff
  }
}

// ─── FilterBar Component ───────────────────────────────────────────────────

function FilterSelect({ label, value, options, onChange }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="appearance-none bg-bg-secondary border border-border rounded-lg pl-3 pr-8 py-1.5 text-xs text-fg-primary focus:outline-none focus:border-accent cursor-pointer"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-fg-muted pointer-events-none" />
    </div>
  )
}

function FilterToggle({ label, icon: Icon, active, onChange }) {
  return (
    <button
      onClick={() => onChange(!active)}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
        active
          ? 'bg-accent-bg border-accent text-accent'
          : 'bg-bg-secondary border-border text-fg-secondary hover:text-fg-primary'
      }`}
    >
      {Icon && <Icon size={12} />}
      {label}
    </button>
  )
}

function FilterDateRange({ value, onChange }) {
  const opts = [
    { value: '', label: 'All Time' },
    { value: '7', label: 'Last 7d' },
    { value: '30', label: 'Last 30d' },
    { value: '90', label: 'Last 90d' },
  ]
  return <FilterSelect label="Date" value={value} options={opts} onChange={onChange} />
}

/**
 * FilterBar — renders a row of filters.
 *
 * @param {Array} filters - filter definitions
 *   select: { key, type:'select', label, options: [{label, value}] }
 *   toggle: { key, type:'toggle', label, icon? }
 *   dateRange: { key, type:'dateRange' }
 * @param {Object} values - current filter state from useFilters
 * @param {Function} onChange - (key, value) => void
 * @param {Function} onClear - reset all
 * @param {boolean} isFiltered - whether any filter is active
 * @param {number} resultCount - filtered count (optional)
 * @param {number} totalCount - total count (optional)
 */
export default function FilterBar({ filters, values, onChange, onClear, isFiltered, resultCount, totalCount }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {filters.map(f => {
        if (f.type === 'select') {
          return (
            <FilterSelect
              key={f.key}
              label={f.label}
              value={values[f.key] || ''}
              options={f.options}
              onChange={v => onChange(f.key, v)}
            />
          )
        }
        if (f.type === 'toggle') {
          return (
            <FilterToggle
              key={f.key}
              label={f.label}
              icon={f.icon}
              active={!!values[f.key]}
              onChange={v => onChange(f.key, v)}
            />
          )
        }
        if (f.type === 'dateRange') {
          return (
            <FilterDateRange
              key={f.key}
              value={values[f.key] || ''}
              onChange={v => onChange(f.key, v)}
            />
          )
        }
        return null
      })}

      {isFiltered && (
        <button
          onClick={onClear}
          className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs text-fg-muted hover:text-fg-primary transition-colors"
          title="Clear all filters"
        >
          <RotateCcw size={11} />
          Clear
        </button>
      )}

      {resultCount !== undefined && totalCount !== undefined && isFiltered && (
        <span className="ml-auto text-xs text-fg-muted">
          {resultCount} of {totalCount}
        </span>
      )}
    </div>
  )
}
