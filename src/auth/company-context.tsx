import { useEffect, useMemo, useState, type ReactNode } from "react"
import { CompanyContext, readCompanyId, writeCompanyId, type CompanyContextValue } from "./company-session.ts"
import { hasCompanyAccess, UserRole } from "./permissions.ts"
import { ApiError, setCompanyIdGetter } from "../api/client.ts"
import { useAvailableCompanies } from "../hooks/useCompanies.ts"
import { useCurrentUser } from "../hooks/useCurrentUser.ts"
import type { AvailableCompany } from "../types/company.ts"

const EMPTY_COMPANIES: AvailableCompany[] = []

export function CompanyProvider({ children }: { children: ReactNode }) {
  const userQuery = useCurrentUser()
  const companiesQuery = useAvailableCompanies()
  const [selectedId, setSelectedId] = useState<string | null>(() => readCompanyId())

  const companies = companiesQuery.data ?? EMPTY_COMPANIES
  const currentCompany = useMemo(() => {
    if (companies.length === 0) {
      return null
    }
    return companies.find((company) => company.id === selectedId) ?? companies[0] ?? null
  }, [companies, selectedId])

  useEffect(() => {
    if (!companiesQuery.isSuccess) {
      return
    }
    writeCompanyId(currentCompany?.id ?? null)
  }, [companiesQuery.isSuccess, currentCompany])

  useEffect(() => {
    setCompanyIdGetter(() => currentCompany?.id ?? null)
    return () => setCompanyIdGetter(() => null)
  }, [currentCompany])

  const value = useMemo<CompanyContextValue>(() => {
    const navRole = userQuery.data?.is_super_admin
      ? UserRole.SUPER_ADMIN
      : companiesQuery.isPending
        ? null
        : (currentCompany?.role ?? null)

    return {
      companies,
      currentCompany,
      setCurrentCompanyId: (companyId: string) => {
        if (!hasCompanyAccess(companies.map((company) => company.id), companyId)) {
          return
        }
        setSelectedId(companyId)
        writeCompanyId(companyId)
      },
      isLoading: companiesQuery.isPending,
      errorMessage:
        companiesQuery.error instanceof ApiError
          ? companiesQuery.error.message
          : companiesQuery.error
            ? "Organisations could not be loaded."
            : null,
      navRole,
    }
  }, [companies, companiesQuery.error, companiesQuery.isPending, currentCompany, userQuery.data])

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>
}
