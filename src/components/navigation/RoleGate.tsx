import type { ReactNode } from "react"
import { canAccessNavItem } from "../../auth/permissions.ts"
import { useCompanyContext } from "../../hooks/useCompanyContext.ts"
import { EmptyState } from "../common/EmptyState.tsx"
import { LoadingState } from "../common/LoadingState.tsx"

export function RoleGate({ itemId, children }: { itemId: string; children: ReactNode }) {
  const { navRole, isLoading } = useCompanyContext()
  if (isLoading && !navRole) {
    return <LoadingState label="Loading your workspace" />
  }
  if (!canAccessNavItem(navRole, itemId)) {
    return (
      <EmptyState
        title="This section is unavailable"
        message="Your role does not include this part of the workspace."
      />
    )
  }
  return children
}
