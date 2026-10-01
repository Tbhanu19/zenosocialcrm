import { useState } from "react"
import { Outlet } from "react-router-dom"
import { useCompanyContext } from "../../hooks/useCompanyContext.ts"
import { ErrorState } from "../common/ErrorState.tsx"
import { Header } from "./Header.tsx"
import { Sidebar } from "./Sidebar.tsx"

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { errorMessage } = useCompanyContext()

  return (
    <div className="min-h-screen md:grid md:h-screen md:grid-cols-[16rem_minmax(0,1fr)]">
      {sidebarOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-ink/40 md:hidden"
          aria-label="Close menu"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      <div className="flex min-h-0 min-w-0 flex-col md:h-full">
        <Header onOpenSidebar={() => setSidebarOpen(true)} />
        <main className="flex min-h-0 flex-1 flex-col overflow-auto px-4 py-6 md:px-8">
          {errorMessage ? (
            <div className="mb-6 shrink-0">
              <ErrorState title="Company access unavailable" message={errorMessage} />
            </div>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  )
}
