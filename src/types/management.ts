import type { CompanyStatus } from "./company.ts"
import type { UserStatus } from "./user.ts"
import type { UserRole } from "../auth/permissions.ts"

export type Page<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type AdminCompanyListItem = {
  id: string
  name: string
  business_type: string | null
  status: CompanyStatus
  created_at: string
  owner_name: string | null
  owner_email: string | null
}

export type RoleCounts = {
  owners: number
  company_managers: number
  marketing_managers: number
  employees: number
}

export type AdminCompanyDetail = {
  id: string
  name: string
  business_type: string | null
  phone: string | null
  email: string | null
  website: string | null
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  status: CompanyStatus
  created_at: string
  updated_at: string
  counts: RoleCounts
}

export type CompanyWrite = {
  name: string
  business_type: string | null
  phone: string | null
  email: string | null
  website: string | null
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  status: CompanyStatus
}

export type CreateCompanyBody = CompanyWrite & {
  business_type: string
  owner: {
    first_name: string
    last_name: string
    email: string
    phone: string | null
  }
}

export type CompanyRecord = Omit<AdminCompanyDetail, "counts">

export type CreatedCompany = {
  company: CompanyRecord
  owner: {
    id: string
    email: string
    first_name: string
    last_name: string
    phone: string | null
    status: UserStatus
    linked_existing_user: boolean
  }
}

export type OrganisationCompany = {
  id: string
  organisation_id: string
  name: string
  business_type: string | null
  phone: string | null
  email: string | null
  status: CompanyStatus
  created_at: string
  updated_at: string
}

export type OrganisationCompanyWrite = {
  name: string
  business_type: string
  phone: string | null
  email: string | null
  status: CompanyStatus
}

export type MembershipStatus = "active" | "inactive"

export type CompanyMember = {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string | null
  role: UserRole
  membership_status: MembershipStatus
  user_status: UserStatus
  created_at: string
}

export type AdminUserRow = CompanyMember & {
  company_id: string
  company_name: string
}

export type MemberWrite = {
  first_name: string
  last_name: string
  email: string
  phone: string | null
  role: UserRole
  membership_status: MembershipStatus
}

export type MemberUpdate = {
  first_name?: string
  last_name?: string
  phone?: string | null
  role?: UserRole
  membership_status?: MembershipStatus
}
