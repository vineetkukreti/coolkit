import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-bg-primary">
          <div className="text-center space-y-4 max-w-md px-6">
            <div className="w-14 h-14 mx-auto rounded-xl bg-danger-bg flex items-center justify-center">
              <span className="text-danger text-2xl">!</span>
            </div>
            <h1 className="text-xl font-semibold text-fg-primary">Something went wrong</h1>
            <p className="text-sm text-fg-muted">
              An unexpected error occurred. Please reload the page to try again.
            </p>
            {this.state.error?.message && (
              <p className="text-xs text-fg-muted font-mono bg-bg-secondary border border-border rounded-lg px-3 py-2 break-all">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent hover:bg-accent-dim text-fg-inverse text-sm font-semibold transition-colors"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
