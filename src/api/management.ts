import type { CompanyListFilters, ListFilters } from "./query-keys.ts"
import { apiFetch } from "./client.ts"
import type {
  AdminCompanyDetail,
  AdminCompanyListItem,
  CompanyRecord,
  AdminUserRow,
  CompanyMember,
  CompanyWrite,
  CreateCompanyBody,
  CreatedCompany,
  MemberUpdate,
  MemberWrite,
  OrganisationCompany,
  OrganisationCompanyWrite,
  Page,
} from "../types/management.ts"

function queryString(entries: Record<string, string | number>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(entries)) {
    if (value !== "") {
      params.set(key, String(value))
    }
  }
  const text = params.toString()
  return text ? `?${text}` : ""
}

export function fetchAdminCompanies(
  filters: CompanyListFilters,
): Promise<Page<AdminCompanyListItem>> {
  return apiFetch(
    `/api/admin/companies${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      status: filters.status,
      business_type: filters.businessType,
    })}`,
  )
}

export function fetchAdminCompany(companyId: string): Promise<AdminCompanyDetail> {
  return apiFetch(`/api/admin/companies/${companyId}`)
}

export function createAdminCompany(body: CreateCompanyBody): Promise<CreatedCompany> {
  return apiFetch("/api/admin/companies", { method: "POST", body: JSON.stringify(body) })
}

export function updateAdminCompany(
  companyId: string,
  body: CompanyWrite,
): Promise<CompanyRecord> {
  return apiFetch(`/api/admin/companies/${companyId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function deleteAdminCompany(companyId: string): Promise<void> {
  return apiFetch(`/api/admin/companies/${companyId}`, {
    method: "DELETE",
  })
}

export function fetchOrganisationCompanies(
  organisationId: string,
): Promise<OrganisationCompany[]> {
  return apiFetch(`/api/admin/companies/${organisationId}/companies`)
}

export function fetchTenantOrganisationCompanies(
  organisationId: string,
): Promise<OrganisationCompany[]> {
  return apiFetch(`/api/companies/${organisationId}/organisation-companies`)
}

export function createOrganisationCompany(
  organisationId: string,
  body: OrganisationCompanyWrite,
): Promise<OrganisationCompany> {
  return apiFetch(`/api/admin/companies/${organisationId}/companies`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function fetchCompanyUsers(
  companyId: string,
  filters: ListFilters,
): Promise<Page<CompanyMember>> {
  return apiFetch(
    `/api/companies/${companyId}/users${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      role: filters.role,
      status: filters.status,
    })}`,
  )
}

export function fetchAdminUsers(filters: ListFilters): Promise<Page<AdminUserRow>> {
  return apiFetch(
    `/api/admin/users${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      role: filters.role,
      status: filters.status,
    })}`,
  )
}

export function createCompanyUser(companyId: string, body: MemberWrite): Promise<CompanyMember> {
  return apiFetch(`/api/companies/${companyId}/users`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateCompanyUser(
  companyId: string,
  userId: string,
  body: MemberUpdate,
): Promise<CompanyMember> {
  return apiFetch(`/api/companies/${companyId}/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}
