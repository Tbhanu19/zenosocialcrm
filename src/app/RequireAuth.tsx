import { Navigate } from "react-router-dom"
import { useAuth } from "../hooks/useAuth.ts"
import { CompanyProvider } from "../auth/company-context.tsx"
import { ApiError } from "../api/client.ts"
import { AppShell } from "../components/layout/AppShell.tsx"
import { ErrorState } from "../components/common/ErrorState.tsx"
import { LoadingState } from "../components/common/LoadingState.tsx"
import { useCurrentUser } from "../hooks/useCurrentUser.ts"

export function RequireAuth() {
  const { token } = useAuth()
  const userQuery = useCurrentUser()

  if (!token) {
    return <Navigate to="/login" replace />
  }
  if (userQuery.isPending) {
    return (
      <div className="p-8">
        <LoadingState label="Checking your session" />
      </div>
    )
  }
  if (userQuery.isError) {
    if (userQuery.error instanceof ApiError && userQuery.error.status === 401) {
      return <Navigate to="/login" replace />
    }
    const message =
      userQuery.error instanceof ApiError ? userQuery.error.message : "Your session could not be loaded."
    return (
      <div className="p-8">
        <ErrorState message={message} />
      </div>
    )
  }

  return (
    <CompanyProvider>
      <AppShell />
    </CompanyProvider>
  )
}
