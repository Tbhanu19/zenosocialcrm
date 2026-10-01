import { isUserRole, type UserRole } from "../auth/permissions.ts"
import type { AvailableCompany } from "../types/company.ts"
import { ApiError, apiFetch } from "./client.ts"

type AvailableCompanyResponse = {
  id: string
  name: string
  role: string
  status: AvailableCompany["status"]
}

export async function fetchAvailableCompanies(): Promise<AvailableCompany[]> {
  const rows = await apiFetch<AvailableCompanyResponse[]>("/api/companies/available")
  return rows.map((row) => ({
    ...row,
    role: parseRole(row.role),
  }))
}

function parseRole(value: string): UserRole {
  if (!isUserRole(value)) {
    throw new ApiError(500, "The server returned an unknown role.")
  }
  return value
}
