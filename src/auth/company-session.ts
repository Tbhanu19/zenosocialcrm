import { createContext } from "react"
import type { UserRole } from "./permissions.ts"
import type { AvailableCompany } from "../types/company.ts"

const COMPANY_KEY = "zeno.current_company_id"

export function readCompanyId(): string | null {
  return sessionStorage.getItem(COMPANY_KEY)
}

export function writeCompanyId(companyId: string | null): void {
  if (companyId) {
    sessionStorage.setItem(COMPANY_KEY, companyId)
  } else {
    sessionStorage.removeItem(COMPANY_KEY)
  }
}

export type CompanyContextValue = {
  companies: AvailableCompany[]
  currentCompany: AvailableCompany | null
  setCurrentCompanyId: (companyId: string) => void
  isLoading: boolean
  errorMessage: string | null
  navRole: UserRole | null
}

export const CompanyContext = createContext<CompanyContextValue | null>(null)
