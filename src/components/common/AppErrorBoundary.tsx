import { Component, type ErrorInfo, type ReactNode } from "react"

type BoundaryState = {
  failed: boolean
}

export class AppErrorBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { failed: false }

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ui error", error.name, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <main className="mx-auto max-w-lg px-6 py-16">
          <h1 className="font-display text-3xl">Something went wrong</h1>
          <p className="mt-3 text-pine">Reload the page to continue.</p>
        </main>
      )
    }
    return this.props.children
  }
}
