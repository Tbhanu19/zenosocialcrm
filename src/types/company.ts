import type { UserRole } from "../auth/permissions.ts"

export type CompanyStatus = "active" | "inactive"

export type AvailableCompany = {
  id: string
  name: string
  role: UserRole
  status: CompanyStatus
}
