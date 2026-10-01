import { useAuth } from "./useAuth.ts"
import { useCompanyContext } from "./useCompanyContext.ts"
import { useCurrentUser } from "./useCurrentUser.ts"
import type { AvailableCompany } from "../types/company.ts"
import type { CurrentUser } from "../types/user.ts"
import type { UserRole } from "../auth/permissions.ts"

export type AppSession = {
  currentUser: CurrentUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  activeCompany: AvailableCompany | null
  availableCompanies: AvailableCompany[]
  setActiveCompany: (companyId: string) => void
  navRole: UserRole | null
}

export function useSession(): AppSession {
  const auth = useAuth()
  const company = useCompanyContext()
  const userQuery = useCurrentUser()

  return {
    currentUser: userQuery.data ?? null,
    isAuthenticated: auth.isAuthenticated && Boolean(userQuery.data),
    isLoading: auth.isAuthenticated && (userQuery.isPending || company.isLoading),
    login: auth.login,
    logout: auth.logout,
    activeCompany: company.currentCompany,
    availableCompanies: company.companies,
    setActiveCompany: company.setCurrentCompanyId,
    navRole: company.navRole,
  }
}
