import { useContext } from "react"
import { CompanyContext, type CompanyContextValue } from "../auth/company-session.ts"

export function useCompanyContext(): CompanyContextValue {
  const value = useContext(CompanyContext)
  if (!value) {
    throw new Error("useCompanyContext must be used within CompanyProvider")
  }
  return value
}
