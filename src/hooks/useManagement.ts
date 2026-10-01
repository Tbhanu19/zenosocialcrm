import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createAdminCompany,
  createCompanyUser,
  createOrganisationCompany,
  deleteAdminCompany,
  fetchAdminCompanies,
  fetchAdminCompany,
  fetchAdminUsers,
  fetchCompanyUsers,
  fetchOrganisationCompanies,
  fetchTenantOrganisationCompanies,
  updateAdminCompany,
  updateCompanyUser,
} from "../api/management.ts"
import { queryKeys, type CompanyListFilters, type ListFilters } from "../api/query-keys.ts"
import type { OrganisationCompanyWrite } from "../types/management.ts"

export function useAdminCompanies(filters: CompanyListFilters) {
  return useQuery({
    queryKey: queryKeys.adminCompanies(filters),
    queryFn: () => fetchAdminCompanies(filters),
  })
}

export function useAdminCompany(companyId: string) {
  return useQuery({
    queryKey: queryKeys.adminCompany(companyId),
    queryFn: () => fetchAdminCompany(companyId),
    enabled: Boolean(companyId),
  })
}

export function useCreateCompany() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAdminCompany,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-companies"] })
      void queryClient.invalidateQueries({ queryKey: ["admin-company", result.company.id] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.availableCompanies })
    },
  })
}

export function useUpdateCompany(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Parameters<typeof updateAdminCompany>[1]) =>
      updateAdminCompany(companyId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-companies"] })
      void queryClient.invalidateQueries({ queryKey: ["admin-company", companyId] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.availableCompanies })
    },
  })
}

export function useDeleteCompany() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAdminCompany,
    onSuccess: (_result, companyId) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-companies"] })
      void queryClient.invalidateQueries({ queryKey: ["admin-company", companyId] })
      void queryClient.invalidateQueries({ queryKey: queryKeys.availableCompanies })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.organisationCompanies(companyId),
      })
    },
  })
}

export function useOrganisationCompanies(organisationId: string) {
  return useQuery({
    queryKey: queryKeys.organisationCompanies(organisationId),
    queryFn: () => fetchOrganisationCompanies(organisationId),
    enabled: Boolean(organisationId),
  })
}

export function useTenantOrganisationCompanies(organisationId: string | null) {
  return useQuery({
    queryKey: queryKeys.tenantOrganisationCompanies(organisationId ?? ""),
    queryFn: () => fetchTenantOrganisationCompanies(organisationId ?? ""),
    enabled: Boolean(organisationId),
  })
}

export function useCreateOrganisationCompany(organisationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: OrganisationCompanyWrite) =>
      createOrganisationCompany(organisationId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.organisationCompanies(organisationId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.tenantOrganisationCompanies(organisationId),
      })
    },
  })
}

export function useCompanyUsers(companyId: string | null, filters: ListFilters, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.companyUsers(companyId ?? "", filters),
    queryFn: () => fetchCompanyUsers(companyId ?? "", filters),
    enabled: enabled && Boolean(companyId),
  })
}

export function useAdminUsers(filters: ListFilters, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.adminUsers(filters),
    queryFn: () => fetchAdminUsers(filters),
    enabled,
  })
}

export function useCreateCompanyUser(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Parameters<typeof createCompanyUser>[1]) =>
      createCompanyUser(companyId, body),
    onSuccess: () => {
      invalidateUsers(queryClient, companyId)
    },
  })
}

export function useUpdateCompanyUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      companyId,
      userId,
      body,
    }: {
      companyId: string
      userId: string
      body: Parameters<typeof updateCompanyUser>[2]
    }) => updateCompanyUser(companyId, userId, body),
    onSuccess: (_result, variables) => {
      invalidateUsers(queryClient, variables.companyId)
    },
  })
}

function invalidateUsers(
  queryClient: ReturnType<typeof useQueryClient>,
  companyId: string,
): void {
  void queryClient.invalidateQueries({ queryKey: ["company-users", companyId] })
  void queryClient.invalidateQueries({ queryKey: ["admin-users"] })
  void queryClient.invalidateQueries({ queryKey: ["admin-company", companyId] })
}
