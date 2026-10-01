export const UserRole = {
  SUPER_ADMIN: "super_admin",
  OWNER: "owner",
  COMPANY_MANAGER: "company_manager",
  MARKETING_MANAGER: "marketing_manager",
  EMPLOYEE: "employee",
} as const

export type UserRole = (typeof UserRole)[keyof typeof UserRole]

const ALL_ROLES = Object.values(UserRole)

export type NavItem = {
  id: string
  label: string
  path: string
  section: string
  roles: readonly UserRole[]
}

const companyOperators = [
  UserRole.SUPER_ADMIN,
  UserRole.OWNER,
  UserRole.COMPANY_MANAGER,
] as const

const marketingRoles = [...companyOperators, UserRole.MARKETING_MANAGER] as const

export const NAV_ITEMS: readonly NavItem[] = [
  {
    id: "companies",
    label: "Organisations",
    path: "/organisations",
    section: "Overview",
    roles: [UserRole.SUPER_ADMIN],
  },
  { id: "contacts", label: "Contacts", path: "/contacts", section: "Workspace", roles: ALL_ROLES },
  { id: "messages", label: "Messages", path: "/messages", section: "Workspace", roles: ALL_ROLES },
  { id: "leads", label: "Leads", path: "/leads", section: "Marketing", roles: marketingRoles },
  {
    id: "lead-metrics",
    label: "Lead Metrics",
    path: "/lead-metrics",
    section: "Marketing",
    roles: marketingRoles,
  },
  {
    id: "lead-metrics-types",
    label: "Lead Metrics Type",
    path: "/lead-metrics-types",
    section: "Marketing",
    roles: marketingRoles,
  },
  {
    id: "pipeline",
    label: "Pipeline",
    path: "/pipeline",
    section: "Sales Activity",
    roles: marketingRoles,
  },
  {
    id: "sales-metrics",
    label: "Sales Metrics",
    path: "/sales-metrics",
    section: "Sales Activity",
    roles: companyOperators,
  },
  {
    id: "users",
    label: "User Management",
    path: "/users",
    section: "Administration",
    roles: companyOperators,
  },
  {
    id: "account",
    label: "Account",
    path: "/account",
    section: "Account",
    roles: ALL_ROLES,
  },
]

const ROLE_VALUES = new Set<string>(ALL_ROLES)

export function isUserRole(value: string): value is UserRole {
  return ROLE_VALUES.has(value)
}

export function hasRole(role: UserRole | null, expected: UserRole): boolean {
  return role === expected
}

export function hasAnyRole(role: UserRole | null, roles: readonly UserRole[]): boolean {
  return role !== null && roles.includes(role)
}

export function hasCompanyAccess(companyIds: readonly string[], companyId: string): boolean {
  return companyIds.includes(companyId)
}

export function visibleNavItems(role: UserRole | null): NavItem[] {
  if (!role) {
    return []
  }
  return NAV_ITEMS.filter((item) => hasAnyRole(role, item.roles))
}

const COMPANY_ASSIGNABLE_ROLES = [
  UserRole.OWNER,
  UserRole.COMPANY_MANAGER,
  UserRole.MARKETING_MANAGER,
  UserRole.EMPLOYEE,
] as const

export function assignableRoles(role: UserRole | null): UserRole[] {
  if (role === UserRole.SUPER_ADMIN) {
    return [...COMPANY_ASSIGNABLE_ROLES]
  }
  if (role === UserRole.OWNER) {
    return [UserRole.COMPANY_MANAGER, UserRole.MARKETING_MANAGER, UserRole.EMPLOYEE]
  }
  if (role === UserRole.COMPANY_MANAGER) {
    return [UserRole.MARKETING_MANAGER, UserRole.EMPLOYEE]
  }
  return []
}

export function canManageMarketing(role: UserRole | null): boolean {
  return hasAnyRole(role, marketingRoles)
}

export function canManagePipeline(role: UserRole | null): boolean {
  return hasAnyRole(role, companyOperators)
}

export function canManageContacts(role: UserRole | null): boolean {
  return canManageMarketing(role)
}

export function canAccessNavItem(role: UserRole | null, itemId: string): boolean {
  const item = NAV_ITEMS.find((entry) => entry.id === itemId)
  if (!item || !role) {
    return false
  }
  return hasAnyRole(role, item.roles)
}
