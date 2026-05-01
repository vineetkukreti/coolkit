import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const TOAST_CONFIG = {
  success: {
    icon: CheckCircle,
    borderColor: 'border-l-success',
    iconColor: 'text-success',
    bg: 'bg-success-bg',
  },
  error: {
    icon: XCircle,
    borderColor: 'border-l-danger',
    iconColor: 'text-danger',
    bg: 'bg-danger-bg',
  },
  warning: {
    icon: AlertTriangle,
    borderColor: 'border-l-warning',
    iconColor: 'text-warning',
    bg: 'bg-warning-bg',
  },
  info: {
    icon: Info,
    borderColor: 'border-l-info',
    iconColor: 'text-info',
    bg: 'bg-info-bg',
  },
}

function ToastItem({ id, title, description, type, onClose }) {
  const [visible, setVisible] = useState(false)
  const [leaving, setLeaving] = useState(false)
  const config = TOAST_CONFIG[type] || TOAST_CONFIG.info
  const Icon = config.icon

  useEffect(() => {
    // Trigger enter animation on mount
    const enterTimer = requestAnimationFrame(() => {
      requestAnimationFrame(() => setVisible(true))
    })
    return () => cancelAnimationFrame(enterTimer)
  }, [])

  const handleClose = useCallback(() => {
    setLeaving(true)
    setTimeout(() => onClose(id), 300)
  }, [id, onClose])

  useEffect(() => {
    const timer = setTimeout(handleClose, 4000)
    return () => clearTimeout(timer)
  }, [handleClose])

  return (
    <div
      className={`
        flex items-start gap-3 w-80 p-4 rounded-xl border border-border
        border-l-4 ${config.borderColor} ${config.bg}
        bg-bg-secondary shadow-2xl shadow-black/50
        transition-all duration-300 ease-out
        ${visible && !leaving
          ? 'translate-x-0 opacity-100'
          : 'translate-x-full opacity-0'
        }
      `}
      role="alert"
      aria-live="polite"
    >
      <Icon size={18} className={`${config.iconColor} shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        {title && (
          <p className="text-sm font-semibold text-fg-primary leading-tight">
            {title}
          </p>
        )}
        {description && (
          <p className={`text-xs text-fg-secondary leading-relaxed ${title ? 'mt-0.5' : ''}`}>
            {typeof description === 'string' ? description : JSON.stringify(description)}
          </p>
        )}
      </div>
      <button
        onClick={handleClose}
        className="shrink-0 p-0.5 rounded text-fg-muted hover:text-fg-primary hover:bg-bg-tertiary transition-colors"
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const counterRef = useRef(0)

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(({ title, description, type = 'info' }) => {
    const id = ++counterRef.current
    setToasts((prev) => {
      const next = [...prev, { id, title, description, type }]
      // Keep max 3 toasts — remove oldest if over limit
      return next.length > 3 ? next.slice(next.length - 3) : next
    })
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast container — bottom-right, above everything */}
      <div
        className="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2.5 items-end pointer-events-none"
        aria-label="Notifications"
      >
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem
              id={t.id}
              title={t.title}
              description={t.description}
              type={t.type}
              onClose={removeToast}
            />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}
